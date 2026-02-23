"""Integration tests for the vectorization pipeline.

End-to-end tests: chunk → embed → store → search.
Requires a running PostgreSQL + pgvector instance.
Run ``docker compose up -d`` and set env vars before executing.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from atlas_mcp.persistence.config import DatabaseConfig
from atlas_mcp.vectorization.chunker import MarkdownChunker
from atlas_mcp.vectorization.indexing import IndexingService
from atlas_mcp.vectorization.store import VectorStore
from tests.integration.conftest import requires_db

_SAMPLE_DOC = """\
# Architecture Overview

The Atlas MCP server provides structured context and semantic
retrieval for LLM agents in software engineering projects.

## Core Components

### Protocol Layer

Handles JSON-RPC 2.0 communication via stdio transport.
The protocol handler manages capability negotiation and
request/response lifecycle.

### Context Layer

Provides three levels of context:
- Core context (stack, conventions, structure)
- Workflow context (active development tasks)
- Decision context (ADRs and architectural decisions)

## Vectorization

Chunks documents semantically by Markdown headers,
embeds with configurable providers, and stores in pgvector
for similarity search.
"""

_EMBEDDING_DIM = 16


def _make_fake_embedder(dim: int = _EMBEDDING_DIM) -> AsyncMock:
    """Create a fake embedding provider with deterministic output.

    Returns:
        An AsyncMock that acts as an EmbeddingProvider.
    """
    embedder = AsyncMock()
    embedder.dimension = dim

    call_count = 0

    async def _embed(text: str) -> list[float]:
        nonlocal call_count
        call_count += 1
        base = [float(call_count) / 100.0] * dim
        # Vary slightly based on text length for different vectors
        for i in range(min(len(text), dim)):
            base[i] += ord(text[i]) / 10000.0
        return base

    async def _embed_batch(texts: list[str]) -> list[list[float]]:
        return [await _embed(t) for t in texts]

    embedder.embed = AsyncMock(side_effect=_embed)
    embedder.embed_batch = AsyncMock(side_effect=_embed_batch)
    return embedder


@requires_db
class TestVectorizationPipeline:
    """E2E tests for the chunk → embed → store → search pipeline."""

    async def test_should_store_and_search_chunks(self) -> None:
        """Validate full pipeline: chunk, embed, store, then search."""
        config = DatabaseConfig.from_env()
        from atlas_mcp.persistence.database import DatabaseManager
        from atlas_mcp.persistence.migrations import MigrationRunner

        async with DatabaseManager(config) as db:
            runner = MigrationRunner(db.pool)
            await runner.run()

            chunker = MarkdownChunker(max_chunk_size=500, min_chunk_size=50)
            embedder = _make_fake_embedder()
            store = VectorStore(db)

            service = IndexingService(chunker, embedder, store)

            # Index the sample document
            count = await service.index_document(
                document_id=9999,
                content=_SAMPLE_DOC,
                title="Architecture Overview",
            )
            assert count > 0

            # Search for related content
            query_embedding = await embedder.embed("protocol handler")
            results = await store.search(
                query_embedding,
                limit=5,
                similarity_threshold=0.0,
            )
            assert len(results) > 0
            assert all(r.document_id == 9999 for r in results)

            # Cleanup
            deleted = await store.delete_by_document(9999)
            assert deleted == count

    async def test_should_reindex_document(self) -> None:
        """Validate that reindexing replaces old chunks."""
        config = DatabaseConfig.from_env()
        from atlas_mcp.persistence.database import DatabaseManager
        from atlas_mcp.persistence.migrations import MigrationRunner

        async with DatabaseManager(config) as db:
            runner = MigrationRunner(db.pool)
            await runner.run()

            chunker = MarkdownChunker(max_chunk_size=500, min_chunk_size=50)
            embedder = _make_fake_embedder()
            store = VectorStore(db)
            service = IndexingService(chunker, embedder, store)

            # Index once
            count1 = await service.index_document(
                document_id=9998,
                content=_SAMPLE_DOC,
                title="Test Doc",
            )

            # Reindex with different content
            new_content = "# Updated\n\nThis is a short updated document."
            count2 = await service.index_document(
                document_id=9998,
                content=new_content,
                title="Test Doc",
                reindex=True,
            )

            # Verify new chunks replaced old ones
            chunks = await store.get_chunks_by_document(9998)
            assert len(chunks) == count2
            assert count2 != count1  # Different content = different chunk count

            # Cleanup
            await store.delete_by_document(9998)

    async def test_should_get_store_stats(self) -> None:
        """Validate that store stats reflect indexed content."""
        config = DatabaseConfig.from_env()
        from atlas_mcp.persistence.database import DatabaseManager
        from atlas_mcp.persistence.migrations import MigrationRunner

        async with DatabaseManager(config) as db:
            runner = MigrationRunner(db.pool)
            await runner.run()

            chunker = MarkdownChunker(max_chunk_size=500, min_chunk_size=50)
            embedder = _make_fake_embedder()
            store = VectorStore(db)
            service = IndexingService(chunker, embedder, store)

            await service.index_document(
                document_id=9997,
                content=_SAMPLE_DOC,
                title="Stats Test",
            )

            stats = await store.get_stats()
            assert stats["total_chunks"] > 0

            # Cleanup
            await store.delete_by_document(9997)

    async def test_should_remove_document(self) -> None:
        """Validate remove_document removes all chunks."""
        config = DatabaseConfig.from_env()
        from atlas_mcp.persistence.database import DatabaseManager
        from atlas_mcp.persistence.migrations import MigrationRunner

        async with DatabaseManager(config) as db:
            runner = MigrationRunner(db.pool)
            await runner.run()

            chunker = MarkdownChunker(max_chunk_size=500, min_chunk_size=50)
            embedder = _make_fake_embedder()
            store = VectorStore(db)
            service = IndexingService(chunker, embedder, store)

            await service.index_document(
                document_id=9996,
                content=_SAMPLE_DOC,
                title="Removal Test",
            )

            deleted = await service.remove_document(9996)
            assert deleted > 0

            chunks = await store.get_chunks_by_document(9996)
            assert len(chunks) == 0
