"""Structured logging setup for the Atlas MCP server.

Configures Python's :mod:`logging` to write to **stderr** so that
log output never interferes with the MCP stdio transport on stdout.
"""

from __future__ import annotations

import logging
import sys

_TEXT_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s"
_TEXT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_JSON_FORMAT = (
    '{"time": "%(asctime)s", "level": "%(levelname)s", '
    '"logger": "%(name)s", "message": "%(message)s"}'
)
_JSON_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logging(level: str = "INFO", fmt: str = "text") -> None:
    """Configure root logger with structured output to stderr.

    Args:
        level: Python logging level name (e.g. ``"DEBUG"``, ``"INFO"``).
        fmt: Output format — ``"text"`` for human-readable or
            ``"json"`` for structured JSON lines.

    Raises:
        ValueError: If *fmt* is not ``"text"`` or ``"json"``.
    """
    fmt_lower = fmt.lower()
    if fmt_lower not in ("text", "json"):
        msg = f"Invalid log format {fmt!r}. Must be 'text' or 'json'."
        raise ValueError(msg)

    if fmt_lower == "json":
        log_format = _JSON_FORMAT
        date_format = _JSON_DATE_FORMAT
    else:
        log_format = _TEXT_FORMAT
        date_format = _TEXT_DATE_FORMAT

    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        msg = f"Invalid log level {level!r}."
        raise ValueError(msg)

    # Reset existing handlers to avoid duplicate output
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

    root.addHandler(handler)
    root.setLevel(numeric_level)
