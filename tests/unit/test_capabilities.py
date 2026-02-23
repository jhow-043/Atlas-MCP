"""Tests for MCP capability negotiation (initialize / initialized handshake)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import anyio
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage
from mcp.types import InitializeResult

from atlas_mcp import __version__
from atlas_mcp.protocol.handler import ProtocolHandler
from atlas_mcp.server import _SERVER_NAME, create_server

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _run_handshake_test(
    callback: Any,
) -> None:
    """Set up an in-memory MCP handshake and call *callback(result, session)*.

    This helper creates the Atlas MCP server, connects an in-memory
    ``ClientSession``, performs ``initialize()``, and passes both the
    ``InitializeResult`` and session to *callback* for assertions.
    The task group and streams are torn down automatically afterwards.
    """
    server = create_server()

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
            result = await session.initialize()
            await callback(result, session)
            tg.cancel_scope.cancel()


# ---------------------------------------------------------------------------
# TestCapabilityNegotiation
# ---------------------------------------------------------------------------


class TestCapabilityNegotiation:
    """Tests for the MCP initialize/initialized handshake."""

    async def test_should_complete_handshake_successfully(self) -> None:
        """Validate that the handshake completes and capabilities are available."""

        async def _assert(result: InitializeResult, _s: ClientSession) -> None:
            assert result.capabilities is not None

        await _run_handshake_test(_assert)

    async def test_should_return_correct_server_name(self) -> None:
        """Validate that server_info.name matches the Atlas MCP server name."""

        async def _assert(result: InitializeResult, _s: ClientSession) -> None:
            assert result.serverInfo.name == _SERVER_NAME

        await _run_handshake_test(_assert)

    async def test_should_return_correct_server_version(self) -> None:
        """Validate that server_info.version matches __version__."""

        async def _assert(result: InitializeResult, _s: ClientSession) -> None:
            assert result.serverInfo.version == __version__

        await _run_handshake_test(_assert)

    async def test_should_return_instructions(self) -> None:
        """Validate that instructions are present in the handshake result."""

        async def _assert(result: InitializeResult, _s: ClientSession) -> None:
            assert result.instructions is not None
            assert "Atlas MCP" in result.instructions

        await _run_handshake_test(_assert)

    async def test_should_return_protocol_version(self) -> None:
        """Validate that a protocol version string is returned."""

        async def _assert(result: InitializeResult, _s: ClientSession) -> None:
            assert result.protocolVersion is not None
            assert str(result.protocolVersion) != ""

        await _run_handshake_test(_assert)

    async def test_should_declare_tools_capability(self) -> None:
        """Validate that the tools capability is declared."""

        async def _assert(result: InitializeResult, _s: ClientSession) -> None:
            assert result.capabilities.tools is not None

        await _run_handshake_test(_assert)

    async def test_should_declare_resources_capability(self) -> None:
        """Validate that the resources capability is declared."""

        async def _assert(result: InitializeResult, _s: ClientSession) -> None:
            assert result.capabilities.resources is not None

        await _run_handshake_test(_assert)

    async def test_should_expose_capabilities_via_session(self) -> None:
        """Validate that capabilities are accessible via get_server_capabilities."""

        async def _assert(_r: InitializeResult, session: ClientSession) -> None:
            caps = session.get_server_capabilities()
            assert caps is not None
            assert caps.tools is not None
            assert caps.resources is not None

        await _run_handshake_test(_assert)


# ---------------------------------------------------------------------------
# TestCapabilityWithHandlers
# ---------------------------------------------------------------------------


class TestCapabilityWithHandlers:
    """Tests that verify capabilities reflect registered handlers."""

    async def test_should_list_registered_tool(self) -> None:
        """Validate that a registered tool appears via tools/list."""
        server = create_server()

        @server.tool(description="A test tool")
        def stub_tool(query: str) -> str:
            """Return the query as-is."""
            return query

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
                result = await session.list_tools()
                tool_names = [t.name for t in result.tools]
                assert "stub_tool" in tool_names
                tg.cancel_scope.cancel()

    async def test_should_list_registered_resource(self) -> None:
        """Validate that a registered resource appears via resources/list."""
        server = create_server()

        @server.resource("context://test/stub")
        def stub_resource() -> str:
            """Return stub data."""
            return '{"stub": true}'

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
                result = await session.list_resources()
                uris = [str(r.uri) for r in result.resources]
                assert "context://test/stub" in uris
                tg.cancel_scope.cancel()


# ---------------------------------------------------------------------------
# TestConfigureCapabilities
# ---------------------------------------------------------------------------


class TestConfigureCapabilities:
    """Tests for the ProtocolHandler._configure_capabilities hook."""

    def test_should_call_configure_capabilities_on_init(self) -> None:
        """Validate that _configure_capabilities is invoked during __init__."""
        with patch.object(
            ProtocolHandler,
            "_configure_capabilities",
            return_value=None,
        ) as mock_configure:
            handler = ProtocolHandler()
            mock_configure.assert_called_once()
            assert handler is not None

    def test_should_register_resources_and_tools_on_init(self) -> None:
        """Validate that _configure_capabilities registers real capabilities."""
        handler = ProtocolHandler()
        resources = handler.server._resource_manager.list_resources()
        tools = handler.server._tool_manager.list_tools()
        assert len(resources) >= 1
        assert len(tools) >= 1
