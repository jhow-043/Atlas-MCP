"""Resource: context://core/structure — Project directory structure."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from atlas_mcp.context.core import CoreContextProvider

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

_URI = "context://core/structure"
_NAME = "core_structure"
_DESCRIPTION = "Directory structure and key files of the Atlas MCP project"


def register_core_structure(server: FastMCP) -> None:
    """Register the ``context://core/structure`` resource on *server*.

    Returns the project directory tree scanned from the filesystem.

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
    def core_structure() -> str:
        """Return the project directory structure as JSON."""
        return json.dumps(provider.get_structure(), indent=2)

    logger.info("Registered resource %s", _URI)
