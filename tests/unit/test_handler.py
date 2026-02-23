"""Tests for the ProtocolHandler module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from atlas_mcp.protocol.handler import ProtocolHandler


class TestProtocolHandler:
    """Tests for ProtocolHandler class."""

    def test_should_initialize_without_error(self) -> None:
        """Validate that ProtocolHandler initializes correctly."""
        handler = ProtocolHandler()
        assert handler is not None

    def test_should_expose_server_property(self) -> None:
        """Validate that the server property returns a FastMCP instance."""
        from mcp.server.fastmcp import FastMCP

        handler = ProtocolHandler()
        assert isinstance(handler.server, FastMCP)

    @patch.object(ProtocolHandler, "_server", create=True)
    def test_should_call_run_with_stdio_transport(self, _mock_server: MagicMock) -> None:
        """Validate that run() starts the server with stdio transport."""
        handler = ProtocolHandler()
        mock_run = MagicMock()
        handler._server.run = mock_run  # type: ignore[attr-defined]
        handler.run()
        mock_run.assert_called_once_with(transport="stdio")

    def test_should_have_configure_capabilities_method(self) -> None:
        """Validate that _configure_capabilities exists and is callable."""
        handler = ProtocolHandler()
        assert hasattr(handler, "_configure_capabilities")
        assert callable(handler._configure_capabilities)

    def test_should_register_resources_after_init(self) -> None:
        """Validate that resources are registered on the server after init."""
        handler = ProtocolHandler()
        resources = handler.server._resource_manager.list_resources()
        assert len(resources) >= 1

    def test_should_register_tools_after_init(self) -> None:
        """Validate that tools are registered on the server after init."""
        handler = ProtocolHandler()
        tools = handler.server._tool_manager.list_tools()
        assert len(tools) >= 1

    def test_should_create_independent_servers(self) -> None:
        """Validate that separate ProtocolHandler instances use separate servers."""
        handler_a = ProtocolHandler()
        handler_b = ProtocolHandler()
        assert handler_a.server is not handler_b.server
