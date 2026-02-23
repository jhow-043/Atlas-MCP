"""Central executor for all MCP tools."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from atlas_mcp.tools.analyze_bug import register_analyze_bug
from atlas_mcp.tools.plan_feature import register_plan_feature
from atlas_mcp.tools.register_adr import register_register_adr
from atlas_mcp.tools.search_context import register_search_context

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Central point for registering MCP tools on the server.

    All tool registration functions are called from the static
    ``register`` method.  New tools should be added here as
    additional calls so that ``ProtocolHandler._configure_capabilities``
    remains a single-line delegation.
    """

    @staticmethod
    def register(server: FastMCP) -> None:
        """Register all MCP tools on *server*.

        Args:
            server: The FastMCP server instance to register tools on.
        """
        register_search_context(server)
        register_register_adr(server)
        register_plan_feature(server)
        register_analyze_bug(server)
        logger.info("ToolExecutor: all tools registered")
