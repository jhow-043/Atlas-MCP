"""Resource: context://core/conventions — Project coding conventions."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from atlas_mcp.context.core import CoreContextProvider

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

_URI = "context://core/conventions"
_NAME = "core_conventions"
_DESCRIPTION = "Coding conventions and style rules for the Atlas MCP project"


def register_core_conventions(server: FastMCP) -> None:
    """Register the ``context://core/conventions`` resource on *server*.

    Returns coding conventions extracted from ``ruff.toml`` and
    ``pyproject.toml``.

    Args:
        server: The FastMCP server instance to register on.
    """
    provider = CoreContextProvider()

    @server.resource(
        _URI,
        name=_NAME,
        description=_DESCRIPTION,
        mime_type="application/json",
    )
    def core_conventions() -> str:
        """Return the project coding conventions as JSON."""
        return json.dumps(provider.get_conventions(), indent=2)

    logger.info("Registered resource %s", _URI)
