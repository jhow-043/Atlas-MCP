"""Tests for the server module."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from atlas_mcp.server import _SERVER_NAME, create_server


class TestCreateServer:
    """Tests for the create_server factory function."""

    def test_should_return_fastmcp_instance(self) -> None:
        """Validate that create_server returns a FastMCP instance."""
        server = create_server()
        assert isinstance(server, FastMCP)

    def test_should_set_server_name(self) -> None:
        """Validate that the server has the correct name."""
        server = create_server()
        assert server.name == _SERVER_NAME

    def test_should_set_instructions(self) -> None:
        """Validate that the server has instructions configured."""
        server = create_server()
        assert server.instructions is not None
        assert "Atlas MCP" in server.instructions
