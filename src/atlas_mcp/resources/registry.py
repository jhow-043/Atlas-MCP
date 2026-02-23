"""Central registry for all MCP resources."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from atlas_mcp.resources.core_conventions import register_core_conventions
from atlas_mcp.resources.core_stack import register_core_stack
from atlas_mcp.resources.core_structure import register_core_structure
from atlas_mcp.resources.decision_adrs import register_decision_adrs
from atlas_mcp.resources.governance_audit import register_governance_audit
from atlas_mcp.resources.workflow_current import register_workflow_current

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
        register_core_conventions(server)
        register_core_structure(server)
        register_decision_adrs(server)
        register_governance_audit(server)
        register_workflow_current(server)
        logger.info("ResourceRegistry: all resources registered")
