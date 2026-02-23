"""Tests for the ToolExecutor and search_context tool."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.server.fastmcp.exceptions import ToolError
from mcp.shared.message import SessionMessage

import atlas_mcp.tools.search_context as _sc_mod
from atlas_mcp.server import create_server
from atlas_mcp.tools.executor import ToolExecutor
from atlas_mcp.tools.search_context import (
    _SEARCH_CONTEXT_DESCRIPTION,
    _SEARCH_CONTEXT_NAME,
    _build_filters,
    _validate_search_params,
    configure,
    register_search_context,
)
from atlas_mcp.vectorization.store import SearchResult

# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

_SAMPLE_RESULTS = [
    SearchResult(
        chunk_id=1,
        document_id=10,
        content="Architecture overview of the system.",
        section_path="Architecture > Overview",
        chunk_index=0,
        similarity=0.95,
        metadata={"doc_type": "documentation"},
    ),
    SearchResult(
        chunk_id=2,
        document_id=11,
        content="ADR-001 decision record.",
        section_path="Decisions > ADR-001",
        chunk_index=0,
        similarity=0.87,
        metadata={"doc_type": "decision"},
    ),
    SearchResult(
        chunk_id=3,
        document_id=12,
        content="Code convention guidelines.",
        section_path="Conventions > Code Style",
        chunk_index=0,
        similarity=0.82,
        metadata={"doc_type": "convention"},
    ),
]


async def _run_tool_test(callback: Any) -> None:
    """Set up an in-memory MCP session with tools and call *callback*.

    The server has ``ToolExecutor.register()`` already applied so
    that ``tools/list`` and ``tools/call`` return real data.
    """
    server = create_server()
    ToolExecutor.register(server)

    send_c2s, recv_c2s = anyio.create_memory_object_stream[SessionMessage](1)
    send_s2c, recv_s2c = anyio.create_memory_object_stream[SessionMessage](1)

    init_options = server._mcp_server.create_initialization_options()

    async with anyio.create_task_group() as tg:
        tg.start_soon(
            server._mcp_server.run,
            recv_c2s,
            send_s2c,
            init_options,
            True,
        )
        async with ClientSession(recv_s2c, send_c2s) as session:
            await session.initialize()
            await callback(session)
            tg.cancel_scope.cancel()


async def _run_configured_tool_test(
    callback: Any,
    search_results: list[SearchResult] | None = None,
) -> None:
    """Set up MCP session with a mocked RAG pipeline.

    Configures module-level ``_embedder`` and ``_store`` so that
    ``search_context`` executes the full pipeline against mocks.
    """
    mock_embedder = AsyncMock()
    mock_embedder.embed = AsyncMock(return_value=[0.1] * 1536)

    mock_store = AsyncMock()
    mock_store.search = AsyncMock(return_value=search_results or [])

    _sc_mod._embedder = mock_embedder
    _sc_mod._store = mock_store

    try:
        await _run_tool_test(callback)
    finally:
        _sc_mod._embedder = None
        _sc_mod._store = None


# ---------------------------------------------------------------------------
# TestToolExecutor
# ---------------------------------------------------------------------------


class TestToolExecutor:
    """Tests for the ToolExecutor class."""

    def test_should_register_tools_on_server(self) -> None:
        """Validate that register() adds tools to the server."""
        server = create_server()
        ToolExecutor.register(server)

        tools = server._tool_manager.list_tools()
        assert len(tools) >= 1

    def test_should_register_search_context_tool(self) -> None:
        """Validate that search_context appears after registration."""
        server = create_server()
        ToolExecutor.register(server)

        tools = server._tool_manager.list_tools()
        names = [t.name for t in tools]
        assert _SEARCH_CONTEXT_NAME in names

    def test_should_allow_direct_search_context_registration(self) -> None:
        """Validate that register_search_context can be called directly."""
        server = create_server()
        register_search_context(server)

        tools = server._tool_manager.list_tools()
        names = [t.name for t in tools]
        assert _SEARCH_CONTEXT_NAME in names


# ---------------------------------------------------------------------------
# TestSearchContextTool — listing
# ---------------------------------------------------------------------------


class TestSearchContextToolListing:
    """Tests for the search_context tool listing via MCP protocol."""

    async def test_should_appear_in_tools_list(self) -> None:
        """Validate that search_context appears in tools/list."""

        async def _assert(session: ClientSession) -> None:
            result = await session.list_tools()
            names = [t.name for t in result.tools]
            assert _SEARCH_CONTEXT_NAME in names

        await _run_tool_test(_assert)

    async def test_should_have_correct_description(self) -> None:
        """Validate that the tool description matches."""

        async def _assert(session: ClientSession) -> None:
            result = await session.list_tools()
            tool = next(t for t in result.tools if t.name == _SEARCH_CONTEXT_NAME)
            assert tool.description == _SEARCH_CONTEXT_DESCRIPTION

        await _run_tool_test(_assert)

    async def test_should_have_query_parameter(self) -> None:
        """Validate that the tool schema includes 'query' as required."""

        async def _assert(session: ClientSession) -> None:
            result = await session.list_tools()
            tool = next(t for t in result.tools if t.name == _SEARCH_CONTEXT_NAME)
            schema = tool.inputSchema
            assert "query" in schema["properties"]
            assert "query" in schema.get("required", [])

        await _run_tool_test(_assert)

    async def test_should_have_optional_parameters(self) -> None:
        """Validate that filters, limit, and similarity_threshold are optional."""

        async def _assert(session: ClientSession) -> None:
            result = await session.list_tools()
            tool = next(t for t in result.tools if t.name == _SEARCH_CONTEXT_NAME)
            schema = tool.inputSchema
            required = schema.get("required", [])
            assert "filters" not in required
            assert "limit" not in required
            assert "similarity_threshold" not in required
            assert "filters" in schema["properties"]
            assert "limit" in schema["properties"]
            assert "similarity_threshold" in schema["properties"]

        await _run_tool_test(_assert)


# ---------------------------------------------------------------------------
# TestSearchContextTool — calling
# ---------------------------------------------------------------------------


class TestSearchContextConfigure:
    """Tests for configure() and _build_filters() helpers."""

    def test_should_set_module_refs_via_configure(self) -> None:
        """Validate that configure() sets _embedder and _store."""
        mock_embedder = AsyncMock()
        mock_store = AsyncMock()

        old_e, old_s = _sc_mod._embedder, _sc_mod._store
        try:
            configure(mock_embedder, mock_store)
            assert _sc_mod._embedder is mock_embedder
            assert _sc_mod._store is mock_store
        finally:
            _sc_mod._embedder = old_e
            _sc_mod._store = old_s

    def test_build_filters_should_return_none_for_none(self) -> None:
        """Validate that _build_filters returns None for None input."""
        assert _build_filters(None) is None

    def test_build_filters_should_return_none_for_empty_dict(self) -> None:
        """Validate that _build_filters returns None for empty dict."""
        assert _build_filters({}) is None

    def test_build_filters_should_map_type_to_doc_type(self) -> None:
        """Validate that 'type' key is mapped to 'doc_type'."""
        result = _build_filters({"type": "decision"})
        assert result == {"doc_type": "decision"}

    def test_build_filters_should_pass_doc_type_directly(self) -> None:
        """Validate that 'doc_type' key passes through unchanged."""
        result = _build_filters({"doc_type": "documentation"})
        assert result == {"doc_type": "documentation"}

    def test_build_filters_should_pass_status(self) -> None:
        """Validate that 'status' key passes through."""
        result = _build_filters({"status": "APPROVED"})
        assert result == {"status": "APPROVED"}

    def test_build_filters_should_convert_document_id_to_int(self) -> None:
        """Validate that 'document_id' is converted to int."""
        result = _build_filters({"document_id": "42"})
        assert result == {"document_id": 42}

    def test_build_filters_should_ignore_unknown_keys(self) -> None:
        """Validate that unknown filter keys are silently ignored."""
        result = _build_filters({"nonexistent_key": "value"})
        assert result is None

    def test_build_filters_should_combine_multiple_keys(self) -> None:
        """Validate that multiple known keys are combined."""
        result = _build_filters({"type": "decision", "status": "APPROVED"})
        assert result == {"doc_type": "decision", "status": "APPROVED"}


# ---------------------------------------------------------------------------
# TestSearchContextValidation
# ---------------------------------------------------------------------------


class TestSearchContextValidation:
    """Tests for _validate_search_params()."""

    def test_should_reject_empty_query(self) -> None:
        """Validate that empty query raises ToolError."""
        with pytest.raises(ToolError):
            _validate_search_params("", 5, 0.7)

    def test_should_reject_whitespace_only_query(self) -> None:
        """Validate that whitespace-only query raises ToolError."""
        with pytest.raises(ToolError):
            _validate_search_params("   ", 5, 0.7)

    def test_should_reject_negative_limit(self) -> None:
        """Validate that limit < 1 raises ToolError."""
        with pytest.raises(ToolError):
            _validate_search_params("test", -1, 0.7)

    def test_should_reject_zero_limit(self) -> None:
        """Validate that limit=0 raises ToolError."""
        with pytest.raises(ToolError):
            _validate_search_params("test", 0, 0.7)

    def test_should_reject_threshold_above_one(self) -> None:
        """Validate that similarity_threshold > 1.0 raises ToolError."""
        with pytest.raises(ToolError):
            _validate_search_params("test", 5, 1.5)

    def test_should_reject_negative_threshold(self) -> None:
        """Validate that similarity_threshold < 0.0 raises ToolError."""
        with pytest.raises(ToolError):
            _validate_search_params("test", 5, -0.1)

    def test_should_accept_valid_params(self) -> None:
        """Validate that valid parameters do not raise."""
        _validate_search_params("architecture", 5, 0.7)

    def test_should_accept_boundary_thresholds(self) -> None:
        """Validate that threshold 0.0 and 1.0 are accepted."""
        _validate_search_params("test", 1, 0.0)
        _validate_search_params("test", 1, 1.0)


# ---------------------------------------------------------------------------
# TestSearchContextUnconfigured
# ---------------------------------------------------------------------------


class TestSearchContextUnconfigured:
    """Tests for calling search_context without RAG pipeline."""

    async def test_should_return_service_unavailable(self) -> None:
        """Validate that calling without configure() returns error."""
        old_e, old_s = _sc_mod._embedder, _sc_mod._store
        _sc_mod._embedder = None
        _sc_mod._store = None

        try:

            async def _assert(session: ClientSession) -> None:
                result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "test"})
                assert result.isError is True
                text = result.content[0].text  # type: ignore[union-attr]
                assert "SERVICE_UNAVAILABLE" in text

            await _run_tool_test(_assert)
        finally:
            _sc_mod._embedder = old_e
            _sc_mod._store = old_s

    async def test_should_validate_before_service_check(self) -> None:
        """Validate that param validation runs before availability check."""
        old_e, old_s = _sc_mod._embedder, _sc_mod._store
        _sc_mod._embedder = None
        _sc_mod._store = None

        try:

            async def _assert(session: ClientSession) -> None:
                result = await session.call_tool(
                    _SEARCH_CONTEXT_NAME,
                    {"query": "test", "limit": -1},
                )
                assert result.isError is True
                text = result.content[0].text  # type: ignore[union-attr]
                assert "INVALID_PARAMETER" in text

            await _run_tool_test(_assert)
        finally:
            _sc_mod._embedder = old_e
            _sc_mod._store = old_s


# ---------------------------------------------------------------------------
# TestSearchContextToolCalling
# ---------------------------------------------------------------------------


class TestSearchContextToolCalling:
    """Tests for calling search_context with mocked RAG pipeline."""

    async def test_should_return_valid_json(self) -> None:
        """Validate that calling search_context returns valid JSON."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "architecture"})
            assert len(result.content) >= 1
            text = result.content[0].text  # type: ignore[union-attr]
            data = json.loads(text)
            assert isinstance(data, dict)

        await _run_configured_tool_test(_assert, _SAMPLE_RESULTS)

    async def test_should_contain_query_in_response(self) -> None:
        """Validate that the response echoes back the query string."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "architecture"})
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["query"] == "architecture"

        await _run_configured_tool_test(_assert, _SAMPLE_RESULTS)

    async def test_should_return_results_from_store(self) -> None:
        """Validate that the response contains results from vector store."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "test"})
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["total_results"] == 3
            assert len(data["results"]) == 3

        await _run_configured_tool_test(_assert, _SAMPLE_RESULTS)

    async def test_should_return_empty_when_store_returns_nothing(self) -> None:
        """Validate that empty store results yield empty response."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "nonexistent"})
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["total_results"] == 0
            assert data["results"] == []

        await _run_configured_tool_test(_assert, [])

    async def test_should_include_filters_applied(self) -> None:
        """Validate that filters_applied reflects the user filters."""

        async def _assert(session: ClientSession) -> None:
            filters = {"type": "convention"}
            result = await session.call_tool(
                _SEARCH_CONTEXT_NAME,
                {"query": "test", "filters": filters},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["filters_applied"] == filters

        await _run_configured_tool_test(_assert, _SAMPLE_RESULTS)

    async def test_should_return_empty_filters_when_none(self) -> None:
        """Validate that filters_applied is {} when no filters given."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "test"})
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["filters_applied"] == {}

        await _run_configured_tool_test(_assert, _SAMPLE_RESULTS)

    async def test_should_format_similarity_to_4_decimals(self) -> None:
        """Validate that similarity scores are rounded to 4 decimals."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "test"})
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            for item in data["results"]:
                sim_str = str(item["similarity"])
                parts = sim_str.split(".")
                if len(parts) == 2:
                    assert len(parts[1]) <= 4

        await _run_configured_tool_test(_assert, _SAMPLE_RESULTS)

    async def test_should_include_result_fields(self) -> None:
        """Validate that each result includes the expected fields."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "test"})
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            for item in data["results"]:
                assert "chunk_id" in item
                assert "document_id" in item
                assert "content" in item
                assert "section_path" in item
                assert "similarity" in item
                assert "metadata" in item

        await _run_configured_tool_test(_assert, _SAMPLE_RESULTS)

    async def test_should_handle_special_character_query(self) -> None:
        """Validate that unicode/special chars are accepted in query."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _SEARCH_CONTEXT_NAME,
                {"query": "búsca semântica 🔍 café"},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["query"] == "búsca semântica 🔍 café"

        await _run_configured_tool_test(_assert, [])

    async def test_should_forward_params_to_store(self) -> None:
        """Validate that limit, threshold, and filters reach the store."""
        mock_embedder = AsyncMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1] * 10)

        mock_store = AsyncMock()
        mock_store.search = AsyncMock(return_value=[])

        _sc_mod._embedder = mock_embedder
        _sc_mod._store = mock_store

        try:

            async def _assert(session: ClientSession) -> None:
                await session.call_tool(
                    _SEARCH_CONTEXT_NAME,
                    {
                        "query": "arch",
                        "limit": 3,
                        "similarity_threshold": 0.8,
                        "filters": {"type": "decision"},
                    },
                )
                mock_embedder.embed.assert_awaited_once_with("arch")
                mock_store.search.assert_awaited_once()
                kw = mock_store.search.call_args.kwargs
                assert kw["limit"] == 3
                assert kw["similarity_threshold"] == 0.8
                assert kw["filters"] == {"doc_type": "decision"}

            await _run_tool_test(_assert)
        finally:
            _sc_mod._embedder = None
            _sc_mod._store = None


# ---------------------------------------------------------------------------
# TestSearchContextEdgeCases
# ---------------------------------------------------------------------------


class TestSearchContextEdgeCases:
    """Tests for edge cases in the search_context tool."""

    async def test_should_return_error_for_negative_limit(self) -> None:
        """Validate that limit=-1 returns isError=True."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _SEARCH_CONTEXT_NAME,
                {"query": "test", "limit": -1},
            )
            assert result.isError is True

        await _run_tool_test(_assert)

    async def test_should_handle_embedding_error(self) -> None:
        """Validate that embedding errors are wrapped as SEARCH_FAILED."""
        mock_embedder = AsyncMock()
        mock_embedder.embed = AsyncMock(
            side_effect=RuntimeError("Embedding API down"),
        )
        mock_store = AsyncMock()

        _sc_mod._embedder = mock_embedder
        _sc_mod._store = mock_store

        try:

            async def _assert(session: ClientSession) -> None:
                result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "test"})
                assert result.isError is True
                text = result.content[0].text  # type: ignore[union-attr]
                assert "SEARCH_FAILED" in text

            await _run_tool_test(_assert)
        finally:
            _sc_mod._embedder = None
            _sc_mod._store = None

    async def test_should_handle_store_search_error(self) -> None:
        """Validate that store search errors are wrapped as SEARCH_FAILED."""
        mock_embedder = AsyncMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1] * 1536)
        mock_store = AsyncMock()
        mock_store.search = AsyncMock(
            side_effect=RuntimeError("DB connection lost"),
        )

        _sc_mod._embedder = mock_embedder
        _sc_mod._store = mock_store

        try:

            async def _assert(session: ClientSession) -> None:
                result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "test"})
                assert result.isError is True
                text = result.content[0].text  # type: ignore[union-attr]
                assert "SEARCH_FAILED" in text

            await _run_tool_test(_assert)
        finally:
            _sc_mod._embedder = None
            _sc_mod._store = None

    async def test_should_pass_single_result_correctly(self) -> None:
        """Validate that a single store result formats correctly."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "test", "limit": 1})
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["total_results"] == 1
            assert data["results"][0]["chunk_id"] == 1

        await _run_configured_tool_test(_assert, [_SAMPLE_RESULTS[0]])

    async def test_should_pass_none_filters_to_store(self) -> None:
        """Validate that no filters passes None to the store."""
        mock_embedder = AsyncMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1] * 10)
        mock_store = AsyncMock()
        mock_store.search = AsyncMock(return_value=[])

        _sc_mod._embedder = mock_embedder
        _sc_mod._store = mock_store

        try:

            async def _assert(session: ClientSession) -> None:
                await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "test"})
                kw = mock_store.search.call_args.kwargs
                assert kw["filters"] is None

            await _run_tool_test(_assert)
        finally:
            _sc_mod._embedder = None
            _sc_mod._store = None
