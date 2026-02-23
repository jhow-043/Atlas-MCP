"""Entry point for execution via ``python -m atlas_mcp``."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from typing import Any, Literal

from atlas_mcp import __version__
from atlas_mcp.bootstrap import ApplicationBootstrap
from atlas_mcp.config.logging import setup_logging
from atlas_mcp.config.settings import Settings
from atlas_mcp.protocol.handler import ProtocolHandler

logger = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Parsed :class:`argparse.Namespace`.
    """
    parser = argparse.ArgumentParser(
        prog="atlas-mcp",
        description="Atlas MCP Server — structured context and RAG for LLM agents.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default=None,
        help="MCP transport mode (default: from ATLAS_TRANSPORT env or 'stdio').",
    )
    return parser.parse_args(argv)


async def _async_main(settings: Settings, bootstrap: ApplicationBootstrap) -> None:
    """Run the async startup, server, and shutdown sequence.

    Args:
        settings: Application settings.
        bootstrap: The application bootstrap instance.
    """
    shutdown_event = asyncio.Event()

    def _signal_handler(*_args: Any) -> None:
        logger.info("Received shutdown signal.")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _signal_handler)

    try:
        await bootstrap.startup(settings)
        handler = ProtocolHandler()

        logger.info(
            "Atlas MCP Server v%s — starting with %s transport.",
            __version__,
            settings.transport,
        )
        await handler.run_async(transport=_as_transport(settings.transport))
    finally:
        await bootstrap.shutdown()


def _as_transport(value: str) -> Literal["stdio", "sse"]:
    """Cast a string to the transport literal type.

    Args:
        value: Must be ``"stdio"`` or ``"sse"``.

    Returns:
        The value typed as a Literal.

    Raises:
        ValueError: If value is invalid.
    """
    if value in ("stdio", "sse"):
        return value  # type: ignore[return-value]
    msg = f"Invalid transport: {value!r}"
    raise ValueError(msg)


def main(argv: list[str] | None = None) -> None:
    """Start the Atlas MCP Server.

    Args:
        argv: Optional argument list for testing.
    """
    args = _parse_args(argv)
    settings = Settings.from_env()

    # CLI flag overrides environment variable
    if args.transport is not None:
        settings = Settings(
            db=settings.db,
            embedding_provider=settings.embedding_provider,
            embedding_model=settings.embedding_model,
            embedding_dimension=settings.embedding_dimension,
            openai_api_key=settings.openai_api_key,
            transport=args.transport,
            sse_host=settings.sse_host,
            sse_port=settings.sse_port,
            log_level=settings.log_level,
            log_format=settings.log_format,
        )

    setup_logging(settings.log_level, settings.log_format)
    logger.info("Atlas MCP Server v%s — initializing...", __version__)

    bootstrap = ApplicationBootstrap()

    try:
        asyncio.run(_async_main(settings, bootstrap))
    except KeyboardInterrupt:
        logger.info("Atlas MCP Server stopped by user.")


if __name__ == "__main__":
    main()
