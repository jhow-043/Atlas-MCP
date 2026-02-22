"""Central registry for all MCP resources."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from atlas_mcp.resources.core_stack import register_core_stack

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


class ResourceRegistry:
    """Central point for registering MCP resources on the server.

    All resource registration functions are called from the static
    ``register`` method.  New resources should be added here as
    additional calls so that ``ProtocolHandler._configure_capabilities``
    remains a single-line delegation.
    """

    @staticmethod
    def register(server: FastMCP) -> None:
        """Register all MCP resources on *server*.

        Args:
            server: The FastMCP server instance to register resources on.
        """
        register_core_stack(server)
        logger.info("ResourceRegistry: all resources registered")
