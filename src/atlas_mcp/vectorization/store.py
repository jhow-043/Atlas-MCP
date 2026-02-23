"""pgvector-backed vector store for chunk storage and similarity search.

Provides :class:`VectorStore` — a repository for storing and searching
document chunks with their embedding vectors in PostgreSQL using pgvector.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from atlas_mcp.persistence.database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    """A single result from a vector similarity search.

    Attributes:
        chunk_id: The database ID of the chunk.
        document_id: The ID of the parent document.
        content: The text content of the chunk.
        section_path: Hierarchical section path.
        chunk_index: Position of the chunk in the document.
        similarity: Cosine similarity score (0.0 to 1.0).
        metadata: Additional metadata stored with the chunk.
    """

    chunk_id: int
    document_id: int
    content: str
    section_path: str
    chunk_index: int
    similarity: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChunkRecord:
    """A stored chunk ready for insertion.

    Attributes:
        document_id: The ID of the parent document.
        content: The text content of the chunk.
        section_path: Hierarchical section path.
        chunk_index: Position of the chunk in the document.
        embedding: The embedding vector.
        metadata: Additional metadata.
    """

    document_id: int
    content: str
    section_path: str
    chunk_index: int
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStore:
    """Repository for storing and searching vectorized document chunks.

    Uses pgvector's cosine distance operator (``<=>``) for similarity
    search with optional metadata filtering.

    Args:
        db: The database manager providing connection pool access.
    """

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize the vector store.

        Args:
            db: An initialized :class:`DatabaseManager`.
        """
        self._db = db

    async def store_chunks(self, chunks: list[ChunkRecord]) -> list[int]:
        """Store multiple chunks with their embeddings.

        Args:
            chunks: A list of :class:`ChunkRecord` objects to insert.

        Returns:
            A list of database IDs for the inserted chunks.

        Raises:
            ValueError: If chunks list is empty.
        """
        if not chunks:
            msg = "Cannot store empty chunks list"
            raise ValueError(msg)

        ids: list[int] = []
        pool = self._db.pool

        async with pool.acquire() as conn:
            from atlas_mcp.persistence.vector_codec import register_vector_codec

            await register_vector_codec(conn)

            stmt = await conn.prepare(
                "INSERT INTO chunks "
                "(document_id, content, section_path, chunk_index, embedding, metadata) "
                "VALUES ($1, $2, $3, $4, $5, $6::jsonb) "
                "RETURNING id"
            )

            for chunk in chunks:
                import json

                metadata_json = json.dumps(chunk.metadata)
                row = await stmt.fetchrow(
                    chunk.document_id,
                    chunk.content,
                    chunk.section_path,
                    chunk.chunk_index,
                    chunk.embedding,
                    metadata_json,
                )
                if row is not None:
                    ids.append(row["id"])

        logger.info("Stored %d chunks for document(s).", len(ids))
        return ids

    async def search(
        self,
        query_embedding: list[float],
        *,
        limit: int = 5,
        similarity_threshold: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search for similar chunks using cosine similarity.

        Args:
            query_embedding: The embedding vector of the query.
            limit: Maximum number of results to return.
            similarity_threshold: Minimum similarity score (0.0 to 1.0).
            filters: Optional metadata filters. Supported keys:

                - ``doc_type``: Filter by document type (requires JOIN).
                - ``document_id``: Filter by specific document ID.
                - ``status``: Filter by document status (requires JOIN).

        Returns:
            A list of :class:`SearchResult` objects sorted by similarity
            (highest first).
        """
        conditions: list[str] = []
        params: list[Any] = [query_embedding]
        param_idx = 2  # $1 is query_embedding

        # Build WHERE conditions based on filters
        if filters:
            if "document_id" in filters:
                conditions.append(f"c.document_id = ${param_idx}")
                params.append(filters["document_id"])
                param_idx += 1

            if "doc_type" in filters:
                conditions.append(f"d.doc_type = ${param_idx}")
                params.append(filters["doc_type"])
                param_idx += 1

            if "status" in filters:
                conditions.append(f"d.status = ${param_idx}")
                params.append(filters["status"])
                param_idx += 1

        # Build query with optional JOIN
        needs_join = filters is not None and any(k in filters for k in ("doc_type", "status"))

        if needs_join:
            from_clause = "FROM chunks c JOIN documents d ON c.document_id = d.id"
        else:
            from_clause = "FROM chunks c"

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = (
            "SELECT c.id, c.document_id, c.content, c.section_path, "
            "c.chunk_index, c.metadata, "
            f"1 - (c.embedding <=> $1) AS similarity "
            f"{from_clause} "
            f"{where_clause} "
            f"ORDER BY c.embedding <=> $1 "
            f"LIMIT ${param_idx}"
        )
        params.append(limit)

        pool = self._db.pool
        async with pool.acquire() as conn:
            from atlas_mcp.persistence.vector_codec import register_vector_codec

            await register_vector_codec(conn)

            rows = await conn.fetch(query, *params)

        results: list[SearchResult] = []
        for row in rows:
            sim = float(row["similarity"])
            if sim < similarity_threshold:
                continue

            import json

            meta = row["metadata"]
            if isinstance(meta, str):
                meta = json.loads(meta)

            results.append(
                SearchResult(
                    chunk_id=row["id"],
                    document_id=row["document_id"],
                    content=row["content"],
                    section_path=row["section_path"],
                    chunk_index=row["chunk_index"],
                    similarity=sim,
                    metadata=meta if isinstance(meta, dict) else {},
                )
            )

        return results

    async def delete_by_document(self, document_id: int) -> int:
        """Delete all chunks for a given document.

        Args:
            document_id: The ID of the document whose chunks to delete.

        Returns:
            The number of deleted chunks.
        """
        result = await self._db.execute(
            "DELETE FROM chunks WHERE document_id = $1",
            document_id,
        )
        count = int(result.split()[-1]) if result else 0
        logger.info("Deleted %d chunks for document_id=%d.", count, document_id)
        return count

    async def get_stats(self) -> dict[str, Any]:
        """Return statistics about the vector store.

        Returns:
            A dictionary with total chunk count, document count,
            and average chunks per document.
        """
        total_chunks = await self._db.fetchval("SELECT COUNT(*) FROM chunks")
        doc_count = await self._db.fetchval("SELECT COUNT(DISTINCT document_id) FROM chunks")
        avg_chunks = round(total_chunks / doc_count, 2) if doc_count and total_chunks else 0.0

        return {
            "total_chunks": total_chunks or 0,
            "document_count": doc_count or 0,
            "avg_chunks_per_document": avg_chunks,
        }

    async def get_chunks_by_document(self, document_id: int) -> list[dict[str, Any]]:
        """Return all chunks for a given document.

        Args:
            document_id: The ID of the document.

        Returns:
            A list of chunk dictionaries.
        """
        rows = await self._db.fetch(
            "SELECT id, content, section_path, chunk_index, metadata "
            "FROM chunks WHERE document_id = $1 ORDER BY chunk_index",
            document_id,
        )

        results: list[dict[str, Any]] = []
        for row in rows:
            import json

            meta = row["metadata"]
            if isinstance(meta, str):
                meta = json.loads(meta)

            results.append(
                {
                    "id": row["id"],
                    "content": row["content"],
                    "section_path": row["section_path"],
                    "chunk_index": row["chunk_index"],
                    "metadata": meta if isinstance(meta, dict) else {},
                }
            )

        return results
