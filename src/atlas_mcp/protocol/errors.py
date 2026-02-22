"""Custom error types and helpers for Atlas MCP.

This module defines the exception hierarchy used across the Atlas MCP
server and provides helper functions for building standardised
JSON-RPC error payloads.

The SDK already converts most exceptions automatically:
- ``ToolError``  →  ``CallToolResult(isError=True)``
- ``McpError``   →  JSON-RPC error response with custom code
- Generic ``Exception``  →  ``ErrorData(code=0)``

Atlas MCP exceptions add semantic meaning on top of these mechanisms
and ensure that error messages follow a consistent format.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.types import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    ErrorData,
)

logger = logging.getLogger(__name__)

# Re-export SDK error codes for convenience
__all__ = [
    "INTERNAL_ERROR",
    "INVALID_PARAMS",
    "INVALID_REQUEST",
    "METHOD_NOT_FOUND",
    "AtlasMCPError",
    "ContextNotFoundError",
    "InvalidParameterError",
    "create_error_data",
    "format_tool_error",
]

# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class AtlasMCPError(Exception):
    """Base exception for all Atlas MCP errors.

    Attributes:
        message: Human-readable error description.
    """

    def __init__(self, message: str) -> None:
        """Initialize with an error *message*."""
        super().__init__(message)
        self.message = message


class InvalidParameterError(AtlasMCPError):
    """Raised when a tool or resource receives an invalid parameter.

    Attributes:
        parameter: The name of the invalid parameter.
        reason: Why the parameter is invalid.
    """

    def __init__(self, parameter: str, reason: str) -> None:
        """Initialize with the invalid *parameter* name and *reason*."""
        self.parameter = parameter
        self.reason = reason
        super().__init__(f"Invalid parameter '{parameter}': {reason}")


class ContextNotFoundError(AtlasMCPError):
    """Raised when a requested context entry is not found.

    Attributes:
        context_id: The identifier of the missing context.
    """

    def __init__(self, context_id: str) -> None:
        """Initialize with the missing *context_id*."""
        self.context_id = context_id
        super().__init__(f"Context not found: {context_id}")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def create_error_data(
    code: int,
    message: str,
    data: Any = None,
) -> ErrorData:
    """Create an ``ErrorData`` instance with a standardised format.

    Args:
        code: JSON-RPC error code (e.g. ``INVALID_PARAMS``).
        message: Short, human-readable error description.
        data: Optional additional data attached to the error.

    Returns:
        An ``ErrorData`` ready to be wrapped in ``McpError``.
    """
    return ErrorData(code=code, message=message, data=data)


def format_tool_error(
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> str:
    """Format an error as a JSON string for tool responses.

    Tools in the MCP SDK return plain strings.  When an error occurs
    inside a tool, this helper produces a consistent JSON payload so
    that consumers can distinguish error responses from normal results.

    Args:
        error_code: Machine-readable error code (e.g. ``"INVALID_PARAMETER"``).
        message: Human-readable error description.
        details: Optional extra context about the error.

    Returns:
        A JSON string with keys ``error_code``, ``message``, and ``details``.
    """
    payload: dict[str, Any] = {
        "error": True,
        "error_code": error_code,
        "message": message,
    }
    if details is not None:
        payload["details"] = details
    return json.dumps(payload, indent=2)
