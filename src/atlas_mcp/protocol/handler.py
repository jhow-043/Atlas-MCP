"""Protocol handler for JSON-RPC 2.0 communication via MCP SDK."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from atlas_mcp.resources import ResourceRegistry
from atlas_mcp.server import create_server

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


class ProtocolHandler:
    """Manages the MCP server lifecycle and stdio transport.

    This class wraps the FastMCP server instance and provides
    a clean interface to start the server with stdio transport.

    Lifecycle:
        1. ``__init__`` — creates the FastMCP server via ``create_server()``.
        2. ``_configure_capabilities`` — extension point for registering
           MCP resources, tools and prompts on the server instance.
           Called automatically at the end of ``__init__``.
        3. ``run`` — starts the server with stdio transport (blocking).

    Attributes:
        server: The underlying FastMCP server instance.
    """

    def __init__(self) -> None:
        """Initialize the ProtocolHandler with a new FastMCP server."""
        self._server: FastMCP = create_server()
        self._configure_capabilities()
        logger.info("ProtocolHandler initialized")

    def _configure_capabilities(self) -> None:
        """Register MCP capabilities (resources, tools, prompts) on the server.

        This method is the single extension point for capability registration.
        It is called automatically during ``__init__`` after server creation.
        """
        ResourceRegistry.register(self._server)
        logger.info("Capabilities configured")

    @property
    def server(self) -> FastMCP:
        """Return the underlying FastMCP server instance."""
        return self._server

    def run(self) -> None:
        """Start the MCP server with stdio transport.

        This method blocks until the server is shut down.
        It uses stdio transport as recommended by the MCP spec
        for local development and CLI-based integrations.
        """
        logger.info("Starting MCP server with stdio transport")
        self._server.run(transport="stdio")
