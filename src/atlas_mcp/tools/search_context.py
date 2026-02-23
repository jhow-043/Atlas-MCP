"""Tool: search_context — Semantic search over project context (mock data)."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

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
        """
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
