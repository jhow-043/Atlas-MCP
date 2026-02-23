"""Entry point for execution via `python -m atlas_mcp`."""

from __future__ import annotations

import logging

from atlas_mcp import __version__
from atlas_mcp.protocol.handler import ProtocolHandler

logger = logging.getLogger(__name__)


def main() -> None:
    """Start the Atlas MCP Server."""
    logger.info("Atlas MCP Server v%s — starting", __version__)

    handler = ProtocolHandler()
    handler.run()


if __name__ == "__main__":
    main()
