"""Tests for the ToolExecutor and search_context tool."""

from __future__ import annotations

import json
from typing import Any

import anyio
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage

from atlas_mcp.server import create_server
from atlas_mcp.tools.executor import ToolExecutor
from atlas_mcp.tools.search_context import (
    _SEARCH_CONTEXT_DESCRIPTION,
    _SEARCH_CONTEXT_NAME,
    register_search_context,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


class TestSearchContextToolCalling:
    """Tests for calling the search_context tool via MCP protocol."""

    async def test_should_return_valid_json(self) -> None:
        """Validate that calling search_context returns valid JSON."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "architecture"})
            assert len(result.content) >= 1
            text = result.content[0].text  # type: ignore[union-attr]
            data = json.loads(text)
            assert isinstance(data, dict)

        await _run_tool_test(_assert)

    async def test_should_contain_query_in_response(self) -> None:
        """Validate that the response echoes back the query string."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "architecture"})
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["query"] == "architecture"

        await _run_tool_test(_assert)

    async def test_should_return_mock_results(self) -> None:
        """Validate that the response contains mock results."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "test"})
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["total_results"] > 0
            assert len(data["results"]) > 0

        await _run_tool_test(_assert)

    async def test_should_filter_by_type(self) -> None:
        """Validate that filters narrow down results by type."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _SEARCH_CONTEXT_NAME,
                {"query": "test", "filters": {"type": "decision"}},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            for item in data["results"]:
                assert item["type"] == "decision"

        await _run_tool_test(_assert)

    async def test_should_respect_limit(self) -> None:
        """Validate that limit parameter caps the number of results."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "test", "limit": 1})
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert len(data["results"]) <= 1

        await _run_tool_test(_assert)

    async def test_should_respect_similarity_threshold(self) -> None:
        """Validate that similarity_threshold filters low-score results."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _SEARCH_CONTEXT_NAME,
                {"query": "test", "similarity_threshold": 0.90},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            for item in data["results"]:
                assert item["similarity"] >= 0.90

        await _run_tool_test(_assert)

    async def test_should_return_empty_when_no_match(self) -> None:
        """Validate that high threshold returns empty results."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _SEARCH_CONTEXT_NAME,
                {"query": "nonexistent", "similarity_threshold": 0.99},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["total_results"] == 0
            assert len(data["results"]) == 0

        await _run_tool_test(_assert)

    async def test_should_include_filters_applied_in_response(self) -> None:
        """Validate that filters_applied reflects the used filters."""

        async def _assert(session: ClientSession) -> None:
            filters = {"type": "convention"}
            result = await session.call_tool(
                _SEARCH_CONTEXT_NAME,
                {"query": "test", "filters": filters},
            )
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["filters_applied"] == filters

        await _run_tool_test(_assert)

    async def test_should_return_empty_filters_when_none_provided(self) -> None:
        """Validate that filters_applied is empty dict when no filters."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "test"})
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["filters_applied"] == {}

        await _run_tool_test(_assert)
