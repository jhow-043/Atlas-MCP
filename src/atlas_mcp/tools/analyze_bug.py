"""Tool: analyze_bug — Structured bug analysis with RAG context.

Accepts a bug report, searches for related project context
via the vector store, and returns a structured analysis as JSON.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp.exceptions import ToolError

from atlas_mcp.protocol.errors import format_tool_error

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from atlas_mcp.vectorization.embeddings import EmbeddingProvider
    from atlas_mcp.vectorization.store import VectorStore

logger = logging.getLogger(__name__)

_ANALYZE_BUG_NAME = "analyze_bug"
_ANALYZE_BUG_DESCRIPTION = (
    "Analyze a bug report with structured output. "
    "Searches for related project context to enrich the analysis."
)

# Module-level references set by configure()
_embedder: EmbeddingProvider | None = None
_store: VectorStore | None = None


def configure(
    embedder: EmbeddingProvider,
    store: VectorStore,
) -> None:
    """Configure the analyze_bug tool with dependencies.

    Args:
        embedder: The embedding provider for query vectorization.
        store: The vector store for context retrieval.
    """
    global _embedder, _store
    _embedder = embedder
    _store = store
    logger.info("analyze_bug configured with RAG pipeline.")


async def _search_related_context(
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search for context related to the bug.

    Args:
        query: The search query (typically title + description).
        limit: Maximum number of results.

    Returns:
        A list of related context entries, or empty list
        if the RAG pipeline is not configured.
    """
    if _embedder is None or _store is None:
        return []

    try:
        embedding = await _embedder.embed(query)
        results = await _store.search(
            embedding,
            limit=limit,
            similarity_threshold=0.5,
        )
        return [
            {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "content": r.content,
                "section_path": r.section_path,
                "similarity": round(r.similarity, 4),
            }
            for r in results
        ]
    except Exception:
        logger.exception("Failed to search related context for analyze_bug")
        return []


def register_analyze_bug(server: FastMCP) -> None:
    """Register the ``analyze_bug`` tool on *server*.

    The tool accepts a bug report and returns a structured analysis
    enriched with related project context from the vector store.

    Args:
        server: The FastMCP server instance to register on.
    """

    @server.tool(
        name=_ANALYZE_BUG_NAME,
        description=_ANALYZE_BUG_DESCRIPTION,
    )
    async def analyze_bug(
        title: str,
        description: str,
        expected_behavior: str = "",
        steps_to_reproduce: str = "",
    ) -> str:
        """Analyze a bug report with structured output.

        Args:
            title: Short title for the bug.
            description: Detailed description of the bug.
            expected_behavior: What should happen instead.
            steps_to_reproduce: Steps to reproduce (one per line).

        Returns:
            JSON string with the structured bug analysis.

        Raises:
            ToolError: If title or description is empty.
        """
        if not title or not title.strip():
            raise ToolError(
                format_tool_error(
                    "INVALID_PARAMETER",
                    "Parameter 'title' must be a non-empty string",
                    {"parameter": "title"},
                )
            )
        if not description or not description.strip():
            raise ToolError(
                format_tool_error(
                    "INVALID_PARAMETER",
                    "Parameter 'description' must be a non-empty string",
                    {"parameter": "description"},
                )
            )

        title = title.strip()
        description = description.strip()

        # Parse steps into a list
        steps_list = [s.strip() for s in steps_to_reproduce.strip().splitlines() if s.strip()]

        # Search for related context
        search_query = f"{title} {description}"
        related_context = await _search_related_context(search_query)

        response: dict[str, Any] = {
            "bug": {
                "title": title,
                "description": description,
                "expected_behavior": expected_behavior.strip(),
                "steps_to_reproduce": steps_list,
            },
            "related_context": related_context,
            "context_available": _embedder is not None and _store is not None,
        }

        logger.info(
            "analyze_bug: title=%r, related_context=%d",
            title,
            len(related_context),
        )

        return json.dumps(response, indent=2)

    logger.info("Registered tool %s", _ANALYZE_BUG_NAME)
