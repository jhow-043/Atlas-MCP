"""Tool: plan_feature — Structured feature planning with RAG context.

Accepts a feature specification, searches for related project context
via the vector store, and returns a structured plan as JSON.
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

_PLAN_FEATURE_NAME = "plan_feature"
_PLAN_FEATURE_DESCRIPTION = (
    "Plan a new feature with structured analysis. "
    "Searches for related project context to enrich the plan."
)

# Module-level references set by configure()
_embedder: EmbeddingProvider | None = None
_store: VectorStore | None = None


def configure(
    embedder: EmbeddingProvider,
    store: VectorStore,
) -> None:
    """Configure the plan_feature tool with dependencies.

    Args:
        embedder: The embedding provider for query vectorization.
        store: The vector store for context retrieval.
    """
    global _embedder, _store
    _embedder = embedder
    _store = store
    logger.info("plan_feature configured with RAG pipeline.")


async def _search_related_context(
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search for context related to the feature.

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
        logger.exception("Failed to search related context for plan_feature")
        return []


def register_plan_feature(server: FastMCP) -> None:
    """Register the ``plan_feature`` tool on *server*.

    The tool accepts a feature specification and returns a structured
    plan enriched with related project context from the vector store.

    Args:
        server: The FastMCP server instance to register on.
    """

    @server.tool(
        name=_PLAN_FEATURE_NAME,
        description=_PLAN_FEATURE_DESCRIPTION,
    )
    async def plan_feature(
        title: str,
        description: str,
        requirements: str = "",
        constraints: str = "",
    ) -> str:
        """Plan a new feature with structured analysis.

        Args:
            title: Short title for the feature.
            description: Detailed description of the feature.
            requirements: Optional list of requirements (one per line).
            constraints: Optional constraints or limitations.

        Returns:
            JSON string with the structured feature plan.

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

        # Parse requirements into a list
        req_list = [r.strip() for r in requirements.strip().splitlines() if r.strip()]

        # Parse constraints into a list
        constraint_list = [c.strip() for c in constraints.strip().splitlines() if c.strip()]

        # Search for related context
        search_query = f"{title} {description}"
        related_context = await _search_related_context(search_query)

        response: dict[str, Any] = {
            "feature": {
                "title": title,
                "description": description,
                "requirements": req_list,
                "constraints": constraint_list,
            },
            "related_context": related_context,
            "context_available": _embedder is not None and _store is not None,
        }

        logger.info(
            "plan_feature: title=%r, related_context=%d",
            title,
            len(related_context),
        )

        return json.dumps(response, indent=2)

    logger.info("Registered tool %s", _PLAN_FEATURE_NAME)
