"""Tests for the analyze_bug tool."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import anyio
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage

import atlas_mcp.tools.analyze_bug as _ab_mod
from atlas_mcp.server import create_server
from atlas_mcp.tools.analyze_bug import (
    _ANALYZE_BUG_DESCRIPTION,
    _ANALYZE_BUG_NAME,
    _search_related_context,
    configure,
    register_analyze_bug,
)
from atlas_mcp.tools.executor import ToolExecutor
from atlas_mcp.vectorization.store import SearchResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_RESULTS = [
    SearchResult(
        chunk_id=20,
        document_id=5,
        content="Error handling guidelines.",
        section_path="Conventions > Error Handling",
        chunk_index=0,
        similarity=0.88,
        metadata={},
    ),
]


async def _run_tool_test(callback: Any) -> None:
    """Set up an in-memory MCP session with tools and call *callback*."""
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
    """Set up MCP session with mocked RAG pipeline for analyze_bug."""
    mock_embedder = AsyncMock()
    mock_embedder.embed = AsyncMock(return_value=[0.1] * 1536)

    mock_store = AsyncMock()
    mock_store.search = AsyncMock(return_value=search_results or [])

    _ab_mod._embedder = mock_embedder
    _ab_mod._store = mock_store

    try:
        await _run_tool_test(callback)
    finally:
        _ab_mod._embedder = None
        _ab_mod._store = None


# ---------------------------------------------------------------------------
# TestAnalyzeBugRegistration
# ---------------------------------------------------------------------------


class TestAnalyzeBugRegistration:
    """Tests for analyze_bug tool registration."""

    def test_should_register_on_server(self) -> None:
        server = create_server()
        register_analyze_bug(server)
        tools = server._tool_manager.list_tools()
        names = [t.name for t in tools]
        assert _ANALYZE_BUG_NAME in names

    def test_should_appear_via_executor(self) -> None:
        server = create_server()
        ToolExecutor.register(server)
        tools = server._tool_manager.list_tools()
        names = [t.name for t in tools]
        assert _ANALYZE_BUG_NAME in names

    async def test_should_appear_in_tools_list(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.list_tools()
            names = [t.name for t in result.tools]
            assert _ANALYZE_BUG_NAME in names

        await _run_tool_test(_assert)

    async def test_should_have_correct_description(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.list_tools()
            tool = next(t for t in result.tools if t.name == _ANALYZE_BUG_NAME)
            assert tool.description == _ANALYZE_BUG_DESCRIPTION

        await _run_tool_test(_assert)

    async def test_should_have_required_parameters(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.list_tools()
            tool = next(t for t in result.tools if t.name == _ANALYZE_BUG_NAME)
            schema = tool.inputSchema
            assert "title" in schema.get("required", [])
            assert "description" in schema.get("required", [])

        await _run_tool_test(_assert)

    async def test_should_have_optional_parameters(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.list_tools()
            tool = next(t for t in result.tools if t.name == _ANALYZE_BUG_NAME)
            schema = tool.inputSchema
            required = schema.get("required", [])
            assert "expected_behavior" not in required
            assert "steps_to_reproduce" not in required

        await _run_tool_test(_assert)


# ---------------------------------------------------------------------------
# TestAnalyzeBugConfigure
# ---------------------------------------------------------------------------


class TestAnalyzeBugConfigure:
    """Tests for configure() and _search_related_context()."""

    def test_should_set_module_refs(self) -> None:
        mock_embedder = AsyncMock()
        mock_store = AsyncMock()
        old_e, old_s = _ab_mod._embedder, _ab_mod._store
        try:
            configure(mock_embedder, mock_store)
            assert _ab_mod._embedder is mock_embedder
            assert _ab_mod._store is mock_store
        finally:
            _ab_mod._embedder = old_e
            _ab_mod._store = old_s

    async def test_search_should_return_empty_when_unconfigured(self) -> None:
        old_e, old_s = _ab_mod._embedder, _ab_mod._store
        _ab_mod._embedder = None
        _ab_mod._store = None
        try:
            result = await _search_related_context("test query")
            assert result == []
        finally:
            _ab_mod._embedder = old_e
            _ab_mod._store = old_s

    async def test_search_should_return_results_when_configured(self) -> None:
        mock_embedder = AsyncMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1] * 10)
        mock_store = AsyncMock()
        mock_store.search = AsyncMock(return_value=_SAMPLE_RESULTS)

        _ab_mod._embedder = mock_embedder
        _ab_mod._store = mock_store
        try:
            result = await _search_related_context("test")
            assert len(result) == 1
            assert result[0]["chunk_id"] == 20
        finally:
            _ab_mod._embedder = None
            _ab_mod._store = None

    async def test_search_should_handle_errors_gracefully(self) -> None:
        mock_embedder = AsyncMock()
        mock_embedder.embed = AsyncMock(side_effect=RuntimeError("API down"))
        mock_store = AsyncMock()

        _ab_mod._embedder = mock_embedder
        _ab_mod._store = mock_store
        try:
            result = await _search_related_context("test")
            assert result == []
        finally:
            _ab_mod._embedder = None
            _ab_mod._store = None


# ---------------------------------------------------------------------------
# TestAnalyzeBugValidation
# ---------------------------------------------------------------------------


class TestAnalyzeBugValidation:
    """Tests for parameter validation."""

    async def test_should_reject_empty_title(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _ANALYZE_BUG_NAME,
                {"title": "", "description": "Something broke"},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "INVALID_PARAMETER" in text

        await _run_tool_test(_assert)

    async def test_should_reject_empty_description(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _ANALYZE_BUG_NAME,
                {"title": "Bug X", "description": ""},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "INVALID_PARAMETER" in text

        await _run_tool_test(_assert)

    async def test_should_reject_whitespace_title(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _ANALYZE_BUG_NAME,
                {"title": "   ", "description": "desc"},
            )
            assert result.isError is True

        await _run_tool_test(_assert)


# ---------------------------------------------------------------------------
# TestAnalyzeBugCalling
# ---------------------------------------------------------------------------


class TestAnalyzeBugCalling:
    """Tests for calling analyze_bug via MCP protocol."""

    async def test_should_return_valid_json(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _ANALYZE_BUG_NAME,
                {"title": "Crash on start", "description": "App crashes"},
            )
            text = result.content[0].text  # type: ignore[union-attr]
            data = json.loads(text)
            assert isinstance(data, dict)

        await _run_configured_tool_test(_assert)

    async def test_should_include_bug_info(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _ANALYZE_BUG_NAME,
                {"title": "Login fails", "description": "401 returned"},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["bug"]["title"] == "Login fails"
            assert data["bug"]["description"] == "401 returned"

        await _run_configured_tool_test(_assert)

    async def test_should_include_expected_behavior(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _ANALYZE_BUG_NAME,
                {
                    "title": "Bug",
                    "description": "Desc",
                    "expected_behavior": "Should return 200",
                },
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["bug"]["expected_behavior"] == "Should return 200"

        await _run_configured_tool_test(_assert)

    async def test_should_parse_steps_to_reproduce(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _ANALYZE_BUG_NAME,
                {
                    "title": "Bug",
                    "description": "Desc",
                    "steps_to_reproduce": "Open app\nClick login\nEnter creds",
                },
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["bug"]["steps_to_reproduce"] == [
                "Open app",
                "Click login",
                "Enter creds",
            ]

        await _run_configured_tool_test(_assert)

    async def test_should_include_related_context(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _ANALYZE_BUG_NAME,
                {"title": "Error", "description": "Error handling issue"},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert len(data["related_context"]) == 1
            assert data["related_context"][0]["chunk_id"] == 20

        await _run_configured_tool_test(_assert, _SAMPLE_RESULTS)

    async def test_should_report_context_availability(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _ANALYZE_BUG_NAME,
                {"title": "Bug", "description": "Desc"},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["context_available"] is True

        await _run_configured_tool_test(_assert)

    async def test_should_work_without_rag_configured(self) -> None:
        old_e, old_s = _ab_mod._embedder, _ab_mod._store
        _ab_mod._embedder = None
        _ab_mod._store = None
        try:

            async def _assert(session: ClientSession) -> None:
                result = await session.call_tool(
                    _ANALYZE_BUG_NAME,
                    {"title": "Bug", "description": "Desc"},
                )
                assert result.isError is not True
                data = json.loads(result.content[0].text)  # type: ignore[union-attr]
                assert data["related_context"] == []
                assert data["context_available"] is False

            await _run_tool_test(_assert)
        finally:
            _ab_mod._embedder = old_e
            _ab_mod._store = old_s

    async def test_should_handle_empty_steps(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _ANALYZE_BUG_NAME,
                {
                    "title": "Bug",
                    "description": "Desc",
                    "steps_to_reproduce": "",
                },
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["bug"]["steps_to_reproduce"] == []

        await _run_configured_tool_test(_assert)

    async def test_should_strip_whitespace_from_title(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _ANALYZE_BUG_NAME,
                {"title": "  Bug Title  ", "description": "Desc"},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["bug"]["title"] == "Bug Title"

        await _run_configured_tool_test(_assert)
