"""Tool: search_context — Semantic search over project context via RAG.

Performs real vector similarity search using the embedding provider
and pgvector store. Falls back gracefully when the database or
embedding provider is unavailable.
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

_SEARCH_CONTEXT_NAME = "search_context"
_SEARCH_CONTEXT_DESCRIPTION = (
    "Search project context using semantic similarity. "
    "Returns relevant code snippets, documentation, and decisions."
)

# Module-level references set by configure()
_embedder: EmbeddingProvider | None = None
_store: VectorStore | None = None


def configure(
    embedder: EmbeddingProvider,
    store: VectorStore,
) -> None:
    """Configure the search_context tool with real dependencies.

    Must be called before the tool is invoked. Typically called
    during server initialization after the indexing service is set up.

    Args:
        embedder: The embedding provider for query vectorization.
        store: The vector store for similarity search.
    """
    global _embedder, _store
    _embedder = embedder
    _store = store
    logger.info("search_context configured with real RAG pipeline.")


_MAX_QUERY_LENGTH = 5_000
_MAX_LIMIT = 100


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
    if len(query) > _MAX_QUERY_LENGTH:
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                f"Parameter 'query' exceeds maximum length of {_MAX_QUERY_LENGTH}",
                {"parameter": "query", "max_length": _MAX_QUERY_LENGTH},
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
    if limit > _MAX_LIMIT:
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                f"Parameter 'limit' must be <= {_MAX_LIMIT}",
                {"parameter": "limit", "value": limit, "max_limit": _MAX_LIMIT},
            )
        )
    if not (0.0 <= similarity_threshold <= 1.0):
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                "Parameter 'similarity_threshold' must be between 0.0 and 1.0",
                {
                    "parameter": "similarity_threshold",
                    "value": similarity_threshold,
                },
            )
        )


def _build_filters(
    filters: dict[str, str] | None,
) -> dict[str, Any] | None:
    """Convert user-facing filters to store-compatible filters.

    Args:
        filters: Optional key-value filters from the user.

    Returns:
        A dictionary compatible with :meth:`VectorStore.search`,
        or ``None`` if no filters were provided.
    """
    if not filters:
        return None

    store_filters: dict[str, Any] = {}

    if "type" in filters:
        store_filters["doc_type"] = filters["type"]
    if "doc_type" in filters:
        store_filters["doc_type"] = filters["doc_type"]
    if "status" in filters:
        store_filters["status"] = filters["status"]
    if "document_id" in filters:
        store_filters["document_id"] = int(filters["document_id"])

    return store_filters if store_filters else None


def register_search_context(server: FastMCP) -> None:
    """Register the ``search_context`` tool on *server*.

    The tool performs semantic search over the project context
    using the real RAG pipeline (embed query → pgvector search).

    Falls back with an informative error if the RAG pipeline
    is not configured.

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
            ToolError: If any parameter fails validation or
                the RAG pipeline is unavailable.
        """
        _validate_search_params(query, limit, similarity_threshold)

        if _embedder is None or _store is None:
            raise ToolError(
                format_tool_error(
                    "SERVICE_UNAVAILABLE",
                    "search_context requires a configured RAG pipeline. "
                    "Ensure the database and embedding provider "
                    "are initialized.",
                    {"configured": False},
                )
            )

        try:
            # Step 1: Embed the query
            query_embedding = await _embedder.embed(query)

            # Step 2: Search the vector store
            store_filters = _build_filters(filters)
            search_results = await _store.search(
                query_embedding,
                limit=limit,
                similarity_threshold=similarity_threshold,
                filters=store_filters,
            )

            # Step 3: Format results
            results: list[dict[str, Any]] = [
                {
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "content": r.content,
                    "section_path": r.section_path,
                    "similarity": round(r.similarity, 4),
                    "metadata": r.metadata,
                }
                for r in search_results
            ]

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

        except ToolError:
            raise
        except Exception as exc:
            logger.exception("search_context failed: %s", exc)
            raise ToolError(
                format_tool_error(
                    "SEARCH_FAILED",
                    f"Search operation failed: {exc}",
                    {"query": query},
                )
            ) from exc

    logger.info("Registered tool %s", _SEARCH_CONTEXT_NAME)
