"""Resource: context://core/stack — Core technology stack (real data)."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from atlas_mcp.context.core import CoreContextProvider

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

_CORE_STACK_URI = "context://core/stack"
_CORE_STACK_NAME = "core_stack"
_CORE_STACK_DESCRIPTION = "Core technology stack for the Atlas MCP project"


def register_core_stack(server: FastMCP) -> None:
    """Register the ``context://core/stack`` resource on *server*.

    The resource returns a JSON representation of the project's
    technology stack read from ``pyproject.toml`` and ``ruff.toml``.

    Args:
        server: The FastMCP server instance to register on.
    """
    provider = CoreContextProvider()

    @server.resource(
        _CORE_STACK_URI,
        name=_CORE_STACK_NAME,
        description=_CORE_STACK_DESCRIPTION,
        mime_type="application/json",
    )
    def core_stack() -> str:
        """Return the core technology stack as JSON."""
        return json.dumps(provider.get_stack(), indent=2)

    logger.info("Registered resource %s", _CORE_STACK_URI)
