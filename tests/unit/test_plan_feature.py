"""Tests for the plan_feature tool."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import anyio
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage

import atlas_mcp.tools.plan_feature as _pf_mod
from atlas_mcp.server import create_server
from atlas_mcp.tools.executor import ToolExecutor
from atlas_mcp.tools.plan_feature import (
    _PLAN_FEATURE_DESCRIPTION,
    _PLAN_FEATURE_NAME,
    _search_related_context,
    configure,
    register_plan_feature,
)
from atlas_mcp.vectorization.store import SearchResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_RESULTS = [
    SearchResult(
        chunk_id=10,
        document_id=1,
        content="Architecture overview.",
        section_path="Architecture > Overview",
        chunk_index=0,
        similarity=0.91,
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
    """Set up MCP session with mocked RAG pipeline for plan_feature."""
    mock_embedder = AsyncMock()
    mock_embedder.embed = AsyncMock(return_value=[0.1] * 1536)

    mock_store = AsyncMock()
    mock_store.search = AsyncMock(return_value=search_results or [])

    _pf_mod._embedder = mock_embedder
    _pf_mod._store = mock_store

    try:
        await _run_tool_test(callback)
    finally:
        _pf_mod._embedder = None
        _pf_mod._store = None


# ---------------------------------------------------------------------------
# TestPlanFeatureRegistration
# ---------------------------------------------------------------------------


class TestPlanFeatureRegistration:
    """Tests for plan_feature tool registration."""

    def test_should_register_on_server(self) -> None:
        server = create_server()
        register_plan_feature(server)
        tools = server._tool_manager.list_tools()
        names = [t.name for t in tools]
        assert _PLAN_FEATURE_NAME in names

    def test_should_appear_via_executor(self) -> None:
        server = create_server()
        ToolExecutor.register(server)
        tools = server._tool_manager.list_tools()
        names = [t.name for t in tools]
        assert _PLAN_FEATURE_NAME in names

    async def test_should_appear_in_tools_list(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.list_tools()
            names = [t.name for t in result.tools]
            assert _PLAN_FEATURE_NAME in names

        await _run_tool_test(_assert)

    async def test_should_have_correct_description(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.list_tools()
            tool = next(t for t in result.tools if t.name == _PLAN_FEATURE_NAME)
            assert tool.description == _PLAN_FEATURE_DESCRIPTION

        await _run_tool_test(_assert)

    async def test_should_have_required_parameters(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.list_tools()
            tool = next(t for t in result.tools if t.name == _PLAN_FEATURE_NAME)
            schema = tool.inputSchema
            assert "title" in schema.get("required", [])
            assert "description" in schema.get("required", [])

        await _run_tool_test(_assert)

    async def test_should_have_optional_parameters(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.list_tools()
            tool = next(t for t in result.tools if t.name == _PLAN_FEATURE_NAME)
            schema = tool.inputSchema
            required = schema.get("required", [])
            assert "requirements" not in required
            assert "constraints" not in required

        await _run_tool_test(_assert)


# ---------------------------------------------------------------------------
# TestPlanFeatureConfigure
# ---------------------------------------------------------------------------


class TestPlanFeatureConfigure:
    """Tests for configure() and _search_related_context()."""

    def test_should_set_module_refs(self) -> None:
        mock_embedder = AsyncMock()
        mock_store = AsyncMock()
        old_e, old_s = _pf_mod._embedder, _pf_mod._store
        try:
            configure(mock_embedder, mock_store)
            assert _pf_mod._embedder is mock_embedder
            assert _pf_mod._store is mock_store
        finally:
            _pf_mod._embedder = old_e
            _pf_mod._store = old_s

    async def test_search_should_return_empty_when_unconfigured(self) -> None:
        old_e, old_s = _pf_mod._embedder, _pf_mod._store
        _pf_mod._embedder = None
        _pf_mod._store = None
        try:
            result = await _search_related_context("test query")
            assert result == []
        finally:
            _pf_mod._embedder = old_e
            _pf_mod._store = old_s

    async def test_search_should_return_results_when_configured(self) -> None:
        mock_embedder = AsyncMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1] * 10)
        mock_store = AsyncMock()
        mock_store.search = AsyncMock(return_value=_SAMPLE_RESULTS)

        _pf_mod._embedder = mock_embedder
        _pf_mod._store = mock_store
        try:
            result = await _search_related_context("test")
            assert len(result) == 1
            assert result[0]["chunk_id"] == 10
        finally:
            _pf_mod._embedder = None
            _pf_mod._store = None

    async def test_search_should_handle_errors_gracefully(self) -> None:
        mock_embedder = AsyncMock()
        mock_embedder.embed = AsyncMock(side_effect=RuntimeError("API down"))
        mock_store = AsyncMock()

        _pf_mod._embedder = mock_embedder
        _pf_mod._store = mock_store
        try:
            result = await _search_related_context("test")
            assert result == []
        finally:
            _pf_mod._embedder = None
            _pf_mod._store = None


# ---------------------------------------------------------------------------
# TestPlanFeatureValidation
# ---------------------------------------------------------------------------


class TestPlanFeatureValidation:
    """Tests for parameter validation."""

    async def test_should_reject_empty_title(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _PLAN_FEATURE_NAME,
                {"title": "", "description": "Some desc"},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "INVALID_PARAMETER" in text

        await _run_tool_test(_assert)

    async def test_should_reject_empty_description(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _PLAN_FEATURE_NAME,
                {"title": "Feature X", "description": ""},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "INVALID_PARAMETER" in text

        await _run_tool_test(_assert)

    async def test_should_reject_whitespace_title(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _PLAN_FEATURE_NAME,
                {"title": "   ", "description": "desc"},
            )
            assert result.isError is True

        await _run_tool_test(_assert)


# ---------------------------------------------------------------------------
# TestPlanFeatureCalling
# ---------------------------------------------------------------------------


class TestPlanFeatureCalling:
    """Tests for calling plan_feature via MCP protocol."""

    async def test_should_return_valid_json(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _PLAN_FEATURE_NAME,
                {"title": "New Feature", "description": "Add something"},
            )
            text = result.content[0].text  # type: ignore[union-attr]
            data = json.loads(text)
            assert isinstance(data, dict)

        await _run_configured_tool_test(_assert)

    async def test_should_include_feature_info(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _PLAN_FEATURE_NAME,
                {"title": "Auth Flow", "description": "Add OAuth2"},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["feature"]["title"] == "Auth Flow"
            assert data["feature"]["description"] == "Add OAuth2"

        await _run_configured_tool_test(_assert)

    async def test_should_parse_requirements(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _PLAN_FEATURE_NAME,
                {
                    "title": "F1",
                    "description": "Desc",
                    "requirements": "Req 1\nReq 2\nReq 3",
                },
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["feature"]["requirements"] == ["Req 1", "Req 2", "Req 3"]

        await _run_configured_tool_test(_assert)

    async def test_should_parse_constraints(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _PLAN_FEATURE_NAME,
                {
                    "title": "F1",
                    "description": "Desc",
                    "constraints": "Max 5ms latency\nNo external deps",
                },
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert len(data["feature"]["constraints"]) == 2

        await _run_configured_tool_test(_assert)

    async def test_should_include_related_context(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _PLAN_FEATURE_NAME,
                {"title": "Arch", "description": "Architecture change"},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert len(data["related_context"]) == 1
            assert data["related_context"][0]["chunk_id"] == 10

        await _run_configured_tool_test(_assert, _SAMPLE_RESULTS)

    async def test_should_report_context_availability(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _PLAN_FEATURE_NAME,
                {"title": "F1", "description": "Desc"},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["context_available"] is True

        await _run_configured_tool_test(_assert)

    async def test_should_work_without_rag_configured(self) -> None:
        old_e, old_s = _pf_mod._embedder, _pf_mod._store
        _pf_mod._embedder = None
        _pf_mod._store = None
        try:

            async def _assert(session: ClientSession) -> None:
                result = await session.call_tool(
                    _PLAN_FEATURE_NAME,
                    {"title": "F1", "description": "Desc"},
                )
                assert result.isError is not True
                data = json.loads(result.content[0].text)  # type: ignore[union-attr]
                assert data["related_context"] == []
                assert data["context_available"] is False

            await _run_tool_test(_assert)
        finally:
            _pf_mod._embedder = old_e
            _pf_mod._store = old_s

    async def test_should_handle_empty_requirements(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _PLAN_FEATURE_NAME,
                {"title": "F1", "description": "Desc", "requirements": ""},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["feature"]["requirements"] == []

        await _run_configured_tool_test(_assert)

    async def test_should_strip_whitespace_from_title(self) -> None:
        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _PLAN_FEATURE_NAME,
                {"title": "  Feature X  ", "description": "Desc"},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["feature"]["title"] == "Feature X"

        await _run_configured_tool_test(_assert)
