"""Tests for error handling across the Atlas MCP server."""

from __future__ import annotations

import json
from typing import Any

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.shared.exceptions import McpError
from mcp.shared.message import SessionMessage

from atlas_mcp.protocol.errors import (
    AtlasMCPError,
    ContextNotFoundError,
    InvalidParameterError,
    create_error_data,
    format_tool_error,
)
from atlas_mcp.resources import ResourceRegistry
from atlas_mcp.server import create_server
from atlas_mcp.tools import ToolExecutor
from atlas_mcp.tools.search_context import _SEARCH_CONTEXT_NAME

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _run_error_test(callback: Any) -> None:
    """Set up an in-memory MCP session with all capabilities and call *callback*.

    Both resources and tools are registered so that error scenarios
    can be tested for both categories.  Uses ``raise_exceptions=False``
    so that server-side errors are returned as JSON-RPC error responses
    instead of crashing the task group.
    """
    server = create_server()
    ResourceRegistry.register(server)
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
            False,
        )
        async with ClientSession(recv_s2c, send_c2s) as session:
            await session.initialize()
            await callback(session)
            tg.cancel_scope.cancel()


# ---------------------------------------------------------------------------
# TestAtlasMCPExceptions
# ---------------------------------------------------------------------------


class TestAtlasMCPExceptions:
    """Tests for the custom exception hierarchy."""

    def test_should_create_base_error(self) -> None:
        """Validate that AtlasMCPError stores message correctly."""
        err = AtlasMCPError("something went wrong")
        assert err.message == "something went wrong"
        assert str(err) == "something went wrong"

    def test_should_create_invalid_parameter_error(self) -> None:
        """Validate that InvalidParameterError stores parameter and reason."""
        err = InvalidParameterError("limit", "must be >= 1")
        assert err.parameter == "limit"
        assert err.reason == "must be >= 1"
        assert "limit" in str(err)
        assert "must be >= 1" in str(err)

    def test_should_create_context_not_found_error(self) -> None:
        """Validate that ContextNotFoundError stores context_id."""
        err = ContextNotFoundError("ctx-999")
        assert err.context_id == "ctx-999"
        assert "ctx-999" in str(err)

    def test_should_inherit_from_base_error(self) -> None:
        """Validate that custom errors inherit from AtlasMCPError."""
        assert issubclass(InvalidParameterError, AtlasMCPError)
        assert issubclass(ContextNotFoundError, AtlasMCPError)

    def test_should_inherit_from_exception(self) -> None:
        """Validate that AtlasMCPError inherits from Exception."""
        assert issubclass(AtlasMCPError, Exception)


# ---------------------------------------------------------------------------
# TestErrorHelpers
# ---------------------------------------------------------------------------


class TestErrorHelpers:
    """Tests for error helper functions."""

    def test_should_create_error_data(self) -> None:
        """Validate that create_error_data produces correct ErrorData."""
        err = create_error_data(-32602, "Invalid params", {"field": "query"})
        assert err.code == -32602
        assert err.message == "Invalid params"
        assert err.data == {"field": "query"}

    def test_should_create_error_data_without_data(self) -> None:
        """Validate that create_error_data works without optional data."""
        err = create_error_data(-32603, "Internal error")
        assert err.code == -32603
        assert err.message == "Internal error"
        assert err.data is None

    def test_should_format_tool_error_as_json(self) -> None:
        """Validate that format_tool_error returns valid JSON."""
        result = format_tool_error("INVALID_PARAMETER", "Query is empty")
        data = json.loads(result)
        assert data["error"] is True
        assert data["error_code"] == "INVALID_PARAMETER"
        assert data["message"] == "Query is empty"

    def test_should_include_details_in_tool_error(self) -> None:
        """Validate that format_tool_error includes details when provided."""
        result = format_tool_error(
            "INVALID_PARAMETER",
            "Limit too low",
            {"parameter": "limit", "value": 0},
        )
        data = json.loads(result)
        assert data["details"]["parameter"] == "limit"
        assert data["details"]["value"] == 0

    def test_should_omit_details_when_none(self) -> None:
        """Validate that details key is absent when not provided."""
        result = format_tool_error("INTERNAL_ERROR", "Unexpected error")
        data = json.loads(result)
        assert "details" not in data

    def test_should_include_empty_dict_details(self) -> None:
        """Validate that details={} is included as an empty dict."""
        result = format_tool_error("INTERNAL_ERROR", "Error", {})
        data = json.loads(result)
        assert "details" in data
        assert data["details"] == {}

    def test_should_create_error_data_with_falsy_data_zero(self) -> None:
        """Validate that create_error_data works with data=0."""
        err = create_error_data(-32603, "Error", 0)
        assert err.data == 0

    def test_should_create_error_data_with_falsy_data_empty_string(self) -> None:
        """Validate that create_error_data works with data=''."""
        err = create_error_data(-32603, "Error", "")
        assert err.data == ""


class TestErrorReExports:
    """Tests for re-exported SDK error codes."""

    def test_should_import_internal_error(self) -> None:
        """Validate that INTERNAL_ERROR is importable from errors module."""
        from atlas_mcp.protocol.errors import INTERNAL_ERROR

        assert isinstance(INTERNAL_ERROR, int)

    def test_should_import_invalid_params(self) -> None:
        """Validate that INVALID_PARAMS is importable from errors module."""
        from atlas_mcp.protocol.errors import INVALID_PARAMS

        assert isinstance(INVALID_PARAMS, int)

    def test_should_import_invalid_request(self) -> None:
        """Validate that INVALID_REQUEST is importable from errors module."""
        from atlas_mcp.protocol.errors import INVALID_REQUEST

        assert isinstance(INVALID_REQUEST, int)

    def test_should_import_method_not_found(self) -> None:
        """Validate that METHOD_NOT_FOUND is importable from errors module."""
        from atlas_mcp.protocol.errors import METHOD_NOT_FOUND

        assert isinstance(METHOD_NOT_FOUND, int)

    def test_should_have_correct_error_codes(self) -> None:
        """Validate that re-exported codes match JSON-RPC 2.0 spec."""
        from atlas_mcp.protocol.errors import (
            INTERNAL_ERROR,
            INVALID_PARAMS,
            INVALID_REQUEST,
            METHOD_NOT_FOUND,
        )

        assert INTERNAL_ERROR == -32603
        assert INVALID_PARAMS == -32602
        assert INVALID_REQUEST == -32600
        assert METHOD_NOT_FOUND == -32601


# ---------------------------------------------------------------------------
# TestToolErrorHandling — via MCP protocol
# ---------------------------------------------------------------------------


class TestToolErrorHandling:
    """Tests for tool error handling via the MCP protocol."""

    async def test_should_return_error_for_empty_query(self) -> None:
        """Validate that empty query returns isError=True."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": ""})
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "INVALID_PARAMETER" in text
            assert "query" in text

        await _run_error_test(_assert)

    async def test_should_return_error_for_whitespace_query(self) -> None:
        """Validate that whitespace-only query returns isError=True."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "   "})
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "INVALID_PARAMETER" in text

        await _run_error_test(_assert)

    async def test_should_return_error_for_negative_limit(self) -> None:
        """Validate that limit < 1 returns isError=True."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": "test", "limit": 0})
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "INVALID_PARAMETER" in text
            assert "limit" in text

        await _run_error_test(_assert)

    async def test_should_return_error_for_threshold_above_one(self) -> None:
        """Validate that similarity_threshold > 1.0 returns isError=True."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _SEARCH_CONTEXT_NAME,
                {"query": "test", "similarity_threshold": 1.5},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "INVALID_PARAMETER" in text
            assert "similarity_threshold" in text

        await _run_error_test(_assert)

    async def test_should_return_error_for_negative_threshold(self) -> None:
        """Validate that similarity_threshold < 0.0 returns isError=True."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _SEARCH_CONTEXT_NAME,
                {"query": "test", "similarity_threshold": -0.1},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "INVALID_PARAMETER" in text

        await _run_error_test(_assert)

    async def test_should_return_parseable_error_json(self) -> None:
        """Validate that tool errors contain valid JSON with standard fields."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(_SEARCH_CONTEXT_NAME, {"query": ""})
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            # The error text wraps the ToolError message which contains our JSON
            # Extract the JSON portion from the error message
            # ToolError wraps as: "Error executing tool search_context: <json>"
            error_prefix = f"Error executing tool {_SEARCH_CONTEXT_NAME}: "
            assert text.startswith(error_prefix)
            json_part = text[len(error_prefix) :]
            data = json.loads(json_part)
            assert data["error"] is True
            assert "error_code" in data
            assert "message" in data

        await _run_error_test(_assert)

    async def test_should_succeed_with_valid_params(self) -> None:
        """Validate that valid parameters do not trigger errors."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                _SEARCH_CONTEXT_NAME,
                {
                    "query": "architecture",
                    "limit": 2,
                    "similarity_threshold": 0.8,
                },
            )
            assert result.isError is not True
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["query"] == "architecture"

        await _run_error_test(_assert)

    async def test_should_succeed_with_boundary_threshold(self) -> None:
        """Validate that boundary values 0.0 and 1.0 are accepted."""

        async def _assert(session: ClientSession) -> None:
            result_zero = await session.call_tool(
                _SEARCH_CONTEXT_NAME,
                {"query": "test", "similarity_threshold": 0.0},
            )
            assert result_zero.isError is not True

            result_one = await session.call_tool(
                _SEARCH_CONTEXT_NAME,
                {"query": "test", "similarity_threshold": 1.0},
            )
            assert result_one.isError is not True

        await _run_error_test(_assert)


# ---------------------------------------------------------------------------
# TestResourceErrorHandling — via MCP protocol
# ---------------------------------------------------------------------------


class TestResourceErrorHandling:
    """Tests for resource error handling via the MCP protocol."""

    async def test_should_raise_for_nonexistent_resource(self) -> None:
        """Validate that reading a non-existent resource raises McpError."""

        async def _assert(session: ClientSession) -> None:
            with pytest.raises(McpError):
                await session.read_resource("context://nonexistent/resource")

        await _run_error_test(_assert)
