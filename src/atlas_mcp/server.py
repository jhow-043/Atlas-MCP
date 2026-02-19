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

    Returns:
        A configured FastMCP server ready to run.
    """
    server = FastMCP(
        name=_SERVER_NAME,
        instructions=_SERVER_INSTRUCTIONS,
    )

    logger.info("Atlas MCP Server v%s created with stdio transport", __version__)

    return server
