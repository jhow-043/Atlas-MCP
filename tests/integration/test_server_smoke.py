"""Smoke tests — verify the server starts and responds to MCP protocol.

These tests validate the full server lifecycle:
- In-memory session: fast, no subprocess, no DB required
- Subprocess session: real end-to-end via ``python -m atlas_mcp``

Usage::

    uv run pytest tests/integration/test_server_smoke.py --no-cov
"""

from __future__ import annotations

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage

from atlas_mcp.protocol.handler import ProtocolHandler


class TestInMemorySmoke:
    """Smoke tests using in-memory streams (no subprocess needed)."""

    async def _create_session(
        self,
    ) -> tuple[ClientSession, anyio.abc.TaskGroup, ProtocolHandler]:
        """Create a ProtocolHandler and wire it to a ClientSession."""
        handler = ProtocolHandler()
        return handler, handler._server

    async def test_should_initialize_successfully(self) -> None:
        """Validate that the server completes MCP handshake."""
        handler = ProtocolHandler()
        server = handler._server

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

                assert result.serverInfo.name == "Atlas MCP"
                assert result.capabilities is not None

                tg.cancel_scope.cancel()

    async def test_should_list_resources(self) -> None:
        """Validate that the server exposes resources."""
        handler = ProtocolHandler()
        server = handler._server

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

                resources = await session.list_resources()
                resource_uris = {str(r.uri) for r in resources.resources}

                # Expect at least the core resources
                expected = {
                    "context://core/stack",
                    "context://core/conventions",
                    "context://core/structure",
                }
                assert expected.issubset(resource_uris), (
                    f"Missing resources: {expected - resource_uris}"
                )

                tg.cancel_scope.cancel()

    async def test_should_list_tools(self) -> None:
        """Validate that the server exposes tools."""
        handler = ProtocolHandler()
        server = handler._server

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

                tools = await session.list_tools()
                tool_names = {t.name for t in tools.tools}

                expected = {
                    "search_context",
                    "plan_feature",
                    "analyze_bug",
                    "register_adr",
                }
                assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"

                tg.cancel_scope.cancel()

    async def test_should_read_core_stack_resource(self) -> None:
        """Validate that a core resource returns content."""
        handler = ProtocolHandler()
        server = handler._server

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

                result = await session.read_resource("context://core/stack")
                assert result.contents is not None
                assert len(result.contents) > 0

                # Content should mention Python
                text = result.contents[0].text
                assert text is not None
                assert "Python" in text

                tg.cancel_scope.cancel()

    async def test_should_call_search_context_without_rag(self) -> None:
        """Validate that search_context returns error when RAG not configured."""
        handler = ProtocolHandler()
        server = handler._server

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

                # search_context without RAG configured should return an error
                result = await session.call_tool(
                    "search_context",
                    arguments={"query": "test query"},
                )
                assert result.isError is True

                tg.cancel_scope.cancel()


class TestSubprocessSmoke:
    """Smoke tests using a real subprocess via stdio_client.

    These test the full startup including ``__main__.py``,
    argument parsing, and protocol negotiation. The server runs
    in **degraded mode** (no DB), so RAG tools return errors
    but resources work.
    """

    @pytest.fixture
    def _skip_if_no_uv(self) -> None:
        """Skip if uv is not available."""
        import shutil

        if not shutil.which("uv"):
            pytest.skip("uv not found in PATH")

    @pytest.mark.usefixtures("_skip_if_no_uv")
    async def test_should_start_and_respond_via_stdio(self) -> None:
        """Validate that the server starts as subprocess and responds."""
        from mcp.client.stdio import StdioServerParameters, stdio_client

        params = StdioServerParameters(
            command="uv",
            args=["run", "python", "-m", "atlas_mcp", "--transport", "stdio"],
        )

        async with stdio_client(params) as streams:
            read_stream, write_stream = streams
            async with ClientSession(read_stream, write_stream) as session:
                result = await session.initialize()

                assert result.serverInfo.name == "Atlas MCP"

                # List resources
                resources = await session.list_resources()
                assert len(resources.resources) >= 3

                # List tools
                tools = await session.list_tools()
                assert len(tools.tools) >= 4
