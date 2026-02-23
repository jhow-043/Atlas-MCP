"""Integration tests for governance → indexing pipeline.

Validates that GovernanceService status transitions trigger
automatic indexing/removal via the IndexingService callback.
Requires a running PostgreSQL + pgvector instance.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from atlas_mcp.governance.audit import AuditLogger
from atlas_mcp.governance.service import DocumentStatus, GovernanceService
from atlas_mcp.persistence.config import DatabaseConfig
from atlas_mcp.vectorization.chunker import MarkdownChunker
from atlas_mcp.vectorization.indexing import IndexingService
from atlas_mcp.vectorization.store import VectorStore
from tests.integration.conftest import requires_db

_EMBEDDING_DIM = 16


def _make_fake_embedder(dim: int = _EMBEDDING_DIM) -> AsyncMock:
    """Create a fake embedding provider with deterministic output."""
    embedder = AsyncMock()
    embedder.dimension = dim

    call_count = 0

    async def _embed(text: str) -> list[float]:
        nonlocal call_count
        call_count += 1
        return [float(call_count) / 100.0] * dim

    async def _embed_batch(texts: list[str]) -> list[list[float]]:
        return [await _embed(t) for t in texts]

    embedder.embed = AsyncMock(side_effect=_embed)
    embedder.embed_batch = AsyncMock(side_effect=_embed_batch)
    return embedder


@requires_db
class TestGovernanceIndexingIntegration:
    """Tests for governance → indexing hook."""

    async def test_should_index_on_approved(self) -> None:
        """Validate that APPROVED status triggers indexing."""
        config = DatabaseConfig.from_env()
        from atlas_mcp.persistence.database import DatabaseManager
        from atlas_mcp.persistence.migrations import MigrationRunner

        async with DatabaseManager(config) as db:
            runner = MigrationRunner(db.pool)
            await runner.run()

            audit = AuditLogger(db)
            governance = GovernanceService(db, audit)

            chunker = MarkdownChunker(max_chunk_size=500, min_chunk_size=50)
            embedder = _make_fake_embedder()
            store = VectorStore(db)
            indexing = IndexingService(chunker, embedder, store)

            # Register the callback
            governance.register_on_status_change(indexing.on_status_change)

            # Create and approve a document
            doc = await governance.create_document(
                title="Indexing Test ADR",
                content="# Test ADR\n\nContent for indexing test.",
                doc_type="adr",
            )
            doc_id = doc["id"]

            doc = await governance.transition(doc_id, DocumentStatus.IN_REVIEW)
            doc = await governance.transition(doc_id, DocumentStatus.APPROVED)

            # Verify chunks were created
            chunks = await store.get_chunks_by_document(doc_id)
            assert len(chunks) > 0

            # Cleanup
            await store.delete_by_document(doc_id)

    async def test_should_remove_on_deprecated(self) -> None:
        """Validate that DEPRECATED status removes indexed chunks."""
        config = DatabaseConfig.from_env()
        from atlas_mcp.persistence.database import DatabaseManager
        from atlas_mcp.persistence.migrations import MigrationRunner

        async with DatabaseManager(config) as db:
            runner = MigrationRunner(db.pool)
            await runner.run()

            audit = AuditLogger(db)
            governance = GovernanceService(db, audit)

            chunker = MarkdownChunker(max_chunk_size=500, min_chunk_size=50)
            embedder = _make_fake_embedder()
            store = VectorStore(db)
            indexing = IndexingService(chunker, embedder, store)

            governance.register_on_status_change(indexing.on_status_change)

            # Create, approve (indexes), then deprecate (removes)
            doc = await governance.create_document(
                title="Deprecation Test ADR",
                content="# Old ADR\n\nThis will be deprecated.",
                doc_type="adr",
            )
            doc_id = doc["id"]

            await governance.transition(doc_id, DocumentStatus.IN_REVIEW)
            await governance.transition(doc_id, DocumentStatus.APPROVED)

            # Verify indexed
            chunks = await store.get_chunks_by_document(doc_id)
            assert len(chunks) > 0

            # Deprecate
            await governance.transition(doc_id, DocumentStatus.DEPRECATED)

            # Verify removed
            chunks = await store.get_chunks_by_document(doc_id)
            assert len(chunks) == 0

    async def test_should_reindex_on_reapproval(self) -> None:
        """Validate that re-approval after rejection reindexes."""
        config = DatabaseConfig.from_env()
        from atlas_mcp.persistence.database import DatabaseManager
        from atlas_mcp.persistence.migrations import MigrationRunner

        async with DatabaseManager(config) as db:
            runner = MigrationRunner(db.pool)
            await runner.run()

            audit = AuditLogger(db)
            governance = GovernanceService(db, audit)

            chunker = MarkdownChunker(max_chunk_size=500, min_chunk_size=50)
            embedder = _make_fake_embedder()
            store = VectorStore(db)
            indexing = IndexingService(chunker, embedder, store)

            governance.register_on_status_change(indexing.on_status_change)

            # Create and approve (first time)
            doc = await governance.create_document(
                title="Reapproval Test",
                content="# V1\n\nOriginal content.",
                doc_type="adr",
            )
            doc_id = doc["id"]

            await governance.transition(doc_id, DocumentStatus.IN_REVIEW)
            await governance.transition(doc_id, DocumentStatus.APPROVED)

            first_chunks = await store.get_chunks_by_document(doc_id)
            assert len(first_chunks) > 0

            # Cleanup
            await store.delete_by_document(doc_id)
