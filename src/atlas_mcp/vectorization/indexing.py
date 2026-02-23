"""Indexing service orchestrating chunker, embedder, and vector store.

Provides :class:`IndexingService` which takes a document, chunks it,
generates embeddings, and stores the vectorized chunks. Also handles
removal of chunks when documents are deprecated.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from atlas_mcp.vectorization.chunker import MarkdownChunker
    from atlas_mcp.vectorization.embeddings import EmbeddingProvider
    from atlas_mcp.vectorization.store import VectorStore

logger = logging.getLogger(__name__)


class IndexingError(Exception):
    """Raised when an indexing operation fails."""


class IndexingService:
    """Orchestrate document indexing: chunk → embed → store.

    Connects the chunker, embedding provider, and vector store
    into a single pipeline for document indexing.

    Args:
        chunker: The Markdown chunker for splitting documents.
        embedder: The embedding provider for generating vectors.
        store: The vector store for persisting chunks.
    """

    def __init__(
        self,
        chunker: MarkdownChunker,
        embedder: EmbeddingProvider,
        store: VectorStore,
    ) -> None:
        """Initialize the indexing service.

        Args:
            chunker: The Markdown chunker.
            embedder: The embedding provider.
            store: The vector store.
        """
        self._chunker = chunker
        self._embedder = embedder
        self._store = store

    @property
    def embedder(self) -> EmbeddingProvider:
        """Return the embedding provider."""
        return self._embedder

    @property
    def store(self) -> VectorStore:
        """Return the vector store."""
        return self._store

    async def index_document(
        self,
        document_id: int,
        content: str,
        title: str = "",
        *,
        reindex: bool = False,
    ) -> list[int]:
        """Index a document by chunking, embedding, and storing.

        Args:
            document_id: The ID of the document to index.
            content: The full document text.
            title: Optional document title for metadata.
            reindex: If ``True``, remove existing chunks first.

        Returns:
            A list of chunk IDs that were stored.

        Raises:
            IndexingError: If the indexing pipeline fails.
        """
        if not content or not content.strip():
            msg = f"Cannot index empty document (id={document_id})"
            raise IndexingError(msg)

        try:
            if reindex:
                await self.remove_document(document_id)

            # Step 1: Chunk
            chunks = self._chunker.chunk(content, doc_title=title)
            if not chunks:
                logger.warning(
                    "Document #%d produced no chunks after chunking.",
                    document_id,
                )
                return []

            logger.info(
                "Document #%d chunked into %d pieces.",
                document_id,
                len(chunks),
            )

            # Step 2: Embed
            texts = [c.content for c in chunks]
            embeddings = await self._embedder.embed_batch(texts)

            logger.info(
                "Generated %d embeddings for document #%d.",
                len(embeddings),
                document_id,
            )

            # Step 3: Store
            from atlas_mcp.vectorization.store import ChunkRecord

            records = [
                ChunkRecord(
                    document_id=document_id,
                    content=chunk.content,
                    section_path=chunk.section_path,
                    chunk_index=chunk.chunk_index,
                    embedding=embedding,
                    metadata=chunk.metadata,
                )
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            ]

            ids = await self._store.store_chunks(records)

            logger.info(
                "Stored %d chunks for document #%d.",
                len(ids),
                document_id,
            )
            return ids

        except IndexingError:
            raise
        except Exception as exc:
            msg = f"Failed to index document #{document_id}: {exc}"
            raise IndexingError(msg) from exc

    async def remove_document(self, document_id: int) -> int:
        """Remove all indexed chunks for a document.

        Args:
            document_id: The ID of the document to remove.

        Returns:
            The number of chunks removed.
        """
        count = await self._store.delete_by_document(document_id)
        logger.info("Removed %d chunks for document #%d.", count, document_id)
        return count

    async def on_status_change(
        self,
        document_id: int,
        old_status: str | None,
        new_status: str,
        document: dict[str, Any] | None = None,
    ) -> None:
        """Handle document status transitions for indexing.

        This method is designed to be registered as a callback
        on the :class:`GovernanceService`.

        - ``APPROVED`` → index the document
        - ``DEPRECATED`` → remove the document's chunks

        Args:
            document_id: The document ID.
            old_status: The previous status (may be ``None``).
            new_status: The new status.
            document: Optional full document dict (avoids extra DB fetch).
        """
        if new_status == "APPROVED" and document is not None:
            content = document.get("content", "")
            title = document.get("title", "")
            try:
                await self.index_document(
                    document_id,
                    content,
                    title,
                    reindex=True,
                )
            except IndexingError:
                logger.exception(
                    "Failed to index document #%d on APPROVED.",
                    document_id,
                )

        elif new_status == "DEPRECATED":
            try:
                await self.remove_document(document_id)
            except Exception:
                logger.exception(
                    "Failed to remove chunks for document #%d on DEPRECATED.",
                    document_id,
                )
