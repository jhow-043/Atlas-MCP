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
