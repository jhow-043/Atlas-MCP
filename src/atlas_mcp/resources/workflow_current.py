"""Resource: context://workflow/current — Active workflow context."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from atlas_mcp.context.workflow import WorkflowContextProvider

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

_WORKFLOW_URI = "context://workflow/current"
_WORKFLOW_NAME = "workflow_current"
_WORKFLOW_DESCRIPTION = "Current active development workflow context"

# Module-level provider instance shared across resource calls.
_provider = WorkflowContextProvider()


def get_workflow_provider() -> WorkflowContextProvider:
    """Return the module-level workflow provider.

    This allows tools and other modules to access the same
    provider instance used by the resource.

    Returns:
        The shared WorkflowContextProvider instance.
    """
    return _provider


def register_workflow_current(server: FastMCP) -> None:
    """Register the ``context://workflow/current`` resource.

    Returns the active workflow context or an idle status message.

    Args:
        server: The FastMCP server instance to register on.
    """

    @server.resource(
        _WORKFLOW_URI,
        name=_WORKFLOW_NAME,
        description=_WORKFLOW_DESCRIPTION,
        mime_type="application/json",
    )
    def workflow_current() -> str:
        """Return the current workflow context as JSON."""
        return json.dumps(_provider.get_current_context(), indent=2)

    logger.info("Registered resource %s", _WORKFLOW_URI)
