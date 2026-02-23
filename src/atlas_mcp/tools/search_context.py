"""Tool: search_context — Semantic search over project context (mock data)."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from mcp.server.fastmcp.exceptions import ToolError

from atlas_mcp.protocol.errors import format_tool_error

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

_SEARCH_CONTEXT_NAME = "search_context"
_SEARCH_CONTEXT_DESCRIPTION = (
    "Search project context using semantic similarity. "
    "Returns relevant code snippets, documentation, and decisions."
)

_MOCK_RESULTS: list[dict[str, object]] = [
    {
        "id": "ctx-001",
        "type": "documentation",
        "title": "Project Architecture Overview",
        "content": "Atlas MCP follows a layered architecture with protocol, "
        "resources, tools, context, vectorization, governance, "
        "and persistence layers.",
        "similarity": 0.92,
        "source": "docs/architecture/context.md",
    },
    {
        "id": "ctx-002",
        "type": "convention",
        "title": "Code Style Conventions",
        "content": "Line length: 100 chars. Indentation: 4 spaces. "
        "Quotes: double quotes. Type hints: mandatory.",
        "similarity": 0.87,
        "source": "docs/conventions.md",
    },
    {
        "id": "ctx-003",
        "type": "decision",
        "title": "ADR-001: Use FastMCP SDK",
        "content": "Decision to use the official MCP Python SDK (FastMCP) "
        "for protocol handling instead of a custom implementation.",
        "similarity": 0.83,
        "source": "docs/adr/adr-001.md",
    },
]


def _validate_search_params(
    query: str,
    limit: int,
    similarity_threshold: float,
) -> None:
    """Validate search_context parameters.

    Args:
        query: The search query string.
        limit: Maximum number of results.
        similarity_threshold: Minimum similarity score.

    Raises:
        ToolError: If any parameter is invalid.
    """
    if not query or not query.strip():
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                "Parameter 'query' must be a non-empty string",
                {"parameter": "query"},
            )
        )
    if limit < 1:
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                "Parameter 'limit' must be >= 1",
                {"parameter": "limit", "value": limit},
            )
        )
    if not (0.0 <= similarity_threshold <= 1.0):
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                "Parameter 'similarity_threshold' must be between 0.0 and 1.0",
                {"parameter": "similarity_threshold", "value": similarity_threshold},
            )
        )


def register_search_context(server: FastMCP) -> None:
    """Register the ``search_context`` tool on *server*.

    The tool performs semantic search over the project context.
    In this phase the results are **mock/static**; the tool will
    be connected to the vectorization layer in Phase 2.

    Args:
        server: The FastMCP server instance to register on.
    """

    @server.tool(
        name=_SEARCH_CONTEXT_NAME,
        description=_SEARCH_CONTEXT_DESCRIPTION,
    )
    async def search_context(
        query: str,
        filters: dict[str, str] | None = None,
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> str:
        """Search project context using semantic similarity.

        Args:
            query: The search query string.
            filters: Optional key-value filters (e.g. {"type": "decision"}).
            limit: Maximum number of results to return.
            similarity_threshold: Minimum similarity score (0.0 to 1.0).

        Returns:
            JSON string with matching context entries.

        Raises:
            ToolError: If any parameter fails validation.
        """
        _validate_search_params(query, limit, similarity_threshold)

        results = _MOCK_RESULTS

        if filters:
            for key, value in filters.items():
                results = [r for r in results if str(r.get(key, "")).lower() == value.lower()]

        results = [
            r
            for r in results
            if isinstance(r.get("similarity"), (int, float))
            and float(str(r["similarity"])) >= similarity_threshold
        ]

        results = results[:limit]

        response = {
            "query": query,
            "total_results": len(results),
            "filters_applied": filters or {},
            "similarity_threshold": similarity_threshold,
            "results": results,
        }

        logger.info(
            "search_context: query=%r, results=%d",
            query,
            len(results),
        )

        return json.dumps(response, indent=2)

    logger.info("Registered tool %s", _SEARCH_CONTEXT_NAME)
