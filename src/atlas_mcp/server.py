"""MCP Server setup and initialization."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from atlas_mcp import __version__

logger = logging.getLogger(__name__)

_SERVER_NAME = "Atlas MCP"
_SERVER_INSTRUCTIONS = (
    "Atlas MCP Server provides structured context and semantic retrieval (RAG) "
    "for LLM agents in software engineering projects."
)


def create_server() -> FastMCP:
    """Create and configure the Atlas MCP server instance.

    The server is created with the project name, instructions, and version.
    The version is set on the low-level MCP server so that capability
    negotiation returns the Atlas MCP version (not the SDK version).

    Returns:
        A configured FastMCP server ready to run.
    """
    server = FastMCP(
        name=_SERVER_NAME,
        instructions=_SERVER_INSTRUCTIONS,
    )
    server._mcp_server.version = __version__

    logger.info("Atlas MCP Server v%s created with stdio transport", __version__)

    return server
