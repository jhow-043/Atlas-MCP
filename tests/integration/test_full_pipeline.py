"""Integration tests — full pipeline with real PostgreSQL.

These tests require a running PostgreSQL instance with pgvector extension.
Run ``docker compose up -d`` before executing.

Usage::

    uv run pytest tests/integration/ -m integration --no-cov
"""

from __future__ import annotations

from typing import Any

import pytest

from atlas_mcp.governance.audit import AuditLogger
from atlas_mcp.governance.service import DocumentStatus, GovernanceService
from atlas_mcp.persistence.database import DatabaseManager  # noqa: TC001
from atlas_mcp.vectorization.chunker import MarkdownChunker
from atlas_mcp.vectorization.embeddings import create_embedding_provider
from atlas_mcp.vectorization.indexing import IndexingService
from atlas_mcp.vectorization.store import VectorStore

pytestmark = [pytest.mark.integration]


# ── Helpers ──────────────────────────────────────────────────

SAMPLE_DOCUMENT = """\
# Architecture Overview

Atlas MCP is a Model Context Protocol server implemented in Python.
It provides structured context and semantic retrieval for LLM agents.

## Stack

- **Language:** Python 3.12
- **Database:** PostgreSQL 16 with pgvector
- **Transport:** stdio and SSE

## Components

The server exposes resources (read-only, URI-based) and tools
(actions with typed input/output) following the MCP specification.
"""

SAMPLE_ADR = """\
# ADR-001: Use Python MCP SDK

## Status

Accepted

## Context

We need a protocol layer for communication with LLM agents.

## Decision

Use the official Python MCP SDK (FastMCP) for protocol handling.

## Consequences

- Tight coupling with MCP specification
- Easy upgrade path when spec evolves
"""


# ── Database health ──────────────────────────────────────────


class TestDatabaseHealth:
    """Verify database connectivity and schema."""

    async def test_should_connect_successfully(self, db_manager: DatabaseManager) -> None:
        """Validate that the database is reachable."""
        health = await db_manager.health_check()
        assert health["status"] == "healthy"

    async def test_should_have_pgvector_extension(self, db_manager: DatabaseManager) -> None:
        """Validate that the pgvector extension is available."""
        row = await db_manager.fetchrow("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        assert row is not None, "pgvector extension not installed"
        assert row["extname"] == "vector"

    async def test_should_have_documents_table(self, db_manager: DatabaseManager) -> None:
        """Validate that the documents table exists."""
        row = await db_manager.fetchrow(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename = 'documents'"
        )
        assert row is not None

    async def test_should_have_chunks_table(self, db_manager: DatabaseManager) -> None:
        """Validate that the chunks table exists."""
        row = await db_manager.fetchrow(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = 'chunks'"
        )
        assert row is not None


# ── Vectorization pipeline ───────────────────────────────────


class TestVectorizationPipeline:
    """Test the full chunking → embedding → store → search pipeline."""

    async def test_should_index_and_search_document(self, db_manager: DatabaseManager) -> None:
        """Validate end-to-end: chunk → embed → store → search."""
        embedder = create_embedding_provider(
            "sentence_transformer",
            model="all-MiniLM-L6-v2",
        )
        store = VectorStore(db_manager)
        chunker = MarkdownChunker()
        indexing = IndexingService(chunker, embedder, store)

        # Create a document in DB
        row = await db_manager.fetchrow(
            "INSERT INTO documents (title, content, doc_type, status) "
            "VALUES ($1, $2, $3, $4) RETURNING id",
            "Architecture Overview",
            SAMPLE_DOCUMENT,
            "architecture",
            "APPROVED",
        )
        assert row is not None
        doc_id = row["id"]

        # Index the document
        chunk_ids = await indexing.index_document(
            doc_id, SAMPLE_DOCUMENT, title="Architecture Overview"
        )
        assert len(chunk_ids) > 0

        # Search for something in the document
        query_embedding = await embedder.embed("Python database PostgreSQL")
        results = await store.search(
            query_embedding,
            limit=5,
            similarity_threshold=0.0,
        )
        assert len(results) > 0

        # At least one result should be from our document
        doc_ids = {r.document_id for r in results}
        assert doc_id in doc_ids

        # Results should have non-empty content
        for result in results:
            assert result.content
            assert result.similarity > 0

    async def test_should_filter_by_document_id(self, db_manager: DatabaseManager) -> None:
        """Validate that search filters by document_id work."""
        embedder = create_embedding_provider(
            "sentence_transformer",
            model="all-MiniLM-L6-v2",
        )
        store = VectorStore(db_manager)
        chunker = MarkdownChunker()
        indexing = IndexingService(chunker, embedder, store)

        # Create and index two documents
        row1 = await db_manager.fetchrow(
            "INSERT INTO documents (title, content, doc_type, status) "
            "VALUES ($1, $2, $3, $4) RETURNING id",
            "Doc One",
            SAMPLE_DOCUMENT,
            "architecture",
            "APPROVED",
        )
        row2 = await db_manager.fetchrow(
            "INSERT INTO documents (title, content, doc_type, status) "
            "VALUES ($1, $2, $3, $4) RETURNING id",
            "Doc Two",
            SAMPLE_ADR,
            "adr",
            "APPROVED",
        )
        assert row1 is not None and row2 is not None
        doc_id_1 = row1["id"]
        doc_id_2 = row2["id"]

        await indexing.index_document(doc_id_1, SAMPLE_DOCUMENT)
        await indexing.index_document(doc_id_2, SAMPLE_ADR)

        # Search filtered to doc_id_2 only
        query_embedding = await embedder.embed("MCP SDK")
        results = await store.search(
            query_embedding,
            limit=10,
            similarity_threshold=0.0,
            filters={"document_id": doc_id_2},
        )
        for r in results:
            assert r.document_id == doc_id_2

    async def test_should_respect_similarity_threshold(self, db_manager: DatabaseManager) -> None:
        """Validate that results below threshold are excluded."""
        embedder = create_embedding_provider(
            "sentence_transformer",
            model="all-MiniLM-L6-v2",
        )
        store = VectorStore(db_manager)
        chunker = MarkdownChunker()
        indexing = IndexingService(chunker, embedder, store)

        row = await db_manager.fetchrow(
            "INSERT INTO documents (title, content, doc_type, status) "
            "VALUES ($1, $2, $3, $4) RETURNING id",
            "Sample",
            SAMPLE_DOCUMENT,
            "architecture",
            "APPROVED",
        )
        assert row is not None
        doc_id = row["id"]
        await indexing.index_document(doc_id, SAMPLE_DOCUMENT)

        query_embedding = await embedder.embed("Python database")

        # With a very high threshold, we should get fewer (or zero) results
        results_high = await store.search(
            query_embedding,
            limit=10,
            similarity_threshold=0.99,
        )
        results_low = await store.search(
            query_embedding,
            limit=10,
            similarity_threshold=0.0,
        )
        assert len(results_high) <= len(results_low)


# ── Governance pipeline ──────────────────────────────────────


class TestGovernancePipeline:
    """Test document lifecycle and governance transitions."""

    async def test_should_create_document_as_proposed(self, db_manager: DatabaseManager) -> None:
        """Validate that new documents start with PROPOSED status."""
        audit = AuditLogger(db_manager)
        gov = GovernanceService(db_manager, audit)

        doc = await gov.create_document(
            title="Test Doc",
            content="Some content",
            doc_type="test",
        )
        assert doc["status"] == "PROPOSED"
        assert doc["id"] > 0

    async def test_should_transition_through_lifecycle(self, db_manager: DatabaseManager) -> None:
        """Validate full lifecycle: PROPOSED → IN_REVIEW → APPROVED."""
        audit = AuditLogger(db_manager)
        gov = GovernanceService(db_manager, audit)

        doc = await gov.create_document(
            title="Lifecycle Test",
            content="Content for lifecycle test",
            doc_type="test",
        )
        doc_id: int = doc["id"]

        # PROPOSED → IN_REVIEW
        doc = await gov.transition(doc_id, DocumentStatus.IN_REVIEW)
        assert doc["status"] == "IN_REVIEW"

        # IN_REVIEW → APPROVED
        doc = await gov.transition(doc_id, DocumentStatus.APPROVED)
        assert doc["status"] == "APPROVED"

    async def test_should_reject_invalid_transition(self, db_manager: DatabaseManager) -> None:
        """Validate that invalid transitions raise errors."""
        from atlas_mcp.governance.service import InvalidTransitionError

        audit = AuditLogger(db_manager)
        gov = GovernanceService(db_manager, audit)

        doc = await gov.create_document(
            title="Invalid Transition Test",
            content="Content",
            doc_type="test",
        )
        doc_id = doc["id"]

        # PROPOSED → APPROVED should fail (must go through IN_REVIEW)
        with pytest.raises(InvalidTransitionError):
            await gov.transition(doc_id, DocumentStatus.APPROVED)

    async def test_should_log_audit_entries(self, db_manager: DatabaseManager) -> None:
        """Validate that transitions generate audit log entries."""
        audit = AuditLogger(db_manager)
        gov = GovernanceService(db_manager, audit)

        doc = await gov.create_document(
            title="Audit Test",
            content="Audit content",
            doc_type="test",
        )
        doc_id = doc["id"]
        await gov.transition(doc_id, DocumentStatus.IN_REVIEW)

        entries = await audit.get_entries(entity_type="document", entity_id=doc_id)
        assert len(entries) >= 2  # CREATE + transition


# ── Governance → Indexing integration ────────────────────────


class TestGovernanceIndexingIntegration:
    """Test that governance transitions trigger indexing."""

    async def test_should_index_on_approval(self, db_manager: DatabaseManager) -> None:
        """Validate that approving a document triggers vector indexing."""
        embedder = create_embedding_provider(
            "sentence_transformer",
            model="all-MiniLM-L6-v2",
        )
        store = VectorStore(db_manager)
        chunker = MarkdownChunker()
        indexing = IndexingService(chunker, embedder, store)

        audit = AuditLogger(db_manager)
        gov = GovernanceService(db_manager, audit)
        gov.register_on_status_change(indexing.on_status_change)

        # Create and push through lifecycle
        doc = await gov.create_document(
            title="Indexing Trigger Test",
            content=SAMPLE_DOCUMENT,
            doc_type="architecture",
        )
        doc_id: int = doc["id"]

        await gov.transition(doc_id, DocumentStatus.IN_REVIEW)
        await gov.transition(doc_id, DocumentStatus.APPROVED)

        # Verify chunks were stored
        rows = await db_manager.fetch("SELECT id FROM chunks WHERE document_id = $1", doc_id)
        assert len(rows) > 0, "No chunks indexed after document approval"

    async def test_should_remove_chunks_on_deprecation(self, db_manager: DatabaseManager) -> None:
        """Validate that deprecating a document removes its chunks."""
        embedder = create_embedding_provider(
            "sentence_transformer",
            model="all-MiniLM-L6-v2",
        )
        store = VectorStore(db_manager)
        chunker = MarkdownChunker()
        indexing = IndexingService(chunker, embedder, store)

        audit = AuditLogger(db_manager)
        gov = GovernanceService(db_manager, audit)
        gov.register_on_status_change(indexing.on_status_change)

        doc = await gov.create_document(
            title="Deprecation Test",
            content=SAMPLE_DOCUMENT,
            doc_type="architecture",
        )
        doc_id: int = doc["id"]

        # Approve (triggers indexing)
        await gov.transition(doc_id, DocumentStatus.IN_REVIEW)
        await gov.transition(doc_id, DocumentStatus.APPROVED)

        # Ensure chunks exist
        rows = await db_manager.fetch("SELECT id FROM chunks WHERE document_id = $1", doc_id)
        assert len(rows) > 0

        # Deprecate (triggers removal)
        await gov.transition(doc_id, DocumentStatus.DEPRECATED)

        # Verify chunks were removed
        rows = await db_manager.fetch("SELECT id FROM chunks WHERE document_id = $1", doc_id)
        assert len(rows) == 0, "Chunks not removed after document deprecation"


# ── Full RAG pipeline ────────────────────────────────────────


class TestFullRAGPipeline:
    """Test the complete RAG pipeline: index → configure tools → search."""

    async def _setup_rag(
        self, db_manager: DatabaseManager
    ) -> tuple[Any, VectorStore, IndexingService]:
        """Set up the full RAG infrastructure."""
        embedder = create_embedding_provider(
            "sentence_transformer",
            model="all-MiniLM-L6-v2",
        )
        store = VectorStore(db_manager)
        chunker = MarkdownChunker()
        indexing = IndexingService(chunker, embedder, store)
        return embedder, store, indexing

    async def test_should_search_context_end_to_end(self, db_manager: DatabaseManager) -> None:
        """Validate full search pipeline: index → embed query → search."""
        embedder, store, indexing = await self._setup_rag(db_manager)

        # Insert and index a document
        row = await db_manager.fetchrow(
            "INSERT INTO documents (title, content, doc_type, status) "
            "VALUES ($1, $2, $3, $4) RETURNING id",
            "Full RAG Test",
            SAMPLE_DOCUMENT,
            "architecture",
            "APPROVED",
        )
        assert row is not None
        doc_id = row["id"]
        await indexing.index_document(doc_id, SAMPLE_DOCUMENT, title="Full RAG Test")

        # Configure tools module-level state
        from atlas_mcp.tools import search_context as sc_module

        sc_module.configure(embedder, store)

        # Embed a query and search
        query_embedding = await embedder.embed("MCP server Python PostgreSQL")
        results = await store.search(
            query_embedding,
            limit=5,
            similarity_threshold=0.0,
        )
        assert len(results) > 0

        # Verify result quality — at least one should mention Python
        contents = " ".join(r.content for r in results)
        assert "Python" in contents or "python" in contents

    async def test_should_reindex_on_update(self, db_manager: DatabaseManager) -> None:
        """Validate that reindexing replaces old chunks."""
        _embedder, _store, indexing = await self._setup_rag(db_manager)

        row = await db_manager.fetchrow(
            "INSERT INTO documents (title, content, doc_type, status) "
            "VALUES ($1, $2, $3, $4) RETURNING id",
            "Reindex Test",
            SAMPLE_DOCUMENT,
            "architecture",
            "APPROVED",
        )
        assert row is not None
        doc_id = row["id"]

        # Index once
        ids_first = await indexing.index_document(doc_id, SAMPLE_DOCUMENT)

        # Reindex with different content
        ids_second = await indexing.index_document(
            doc_id,
            SAMPLE_ADR,
            title="Updated Content",
            reindex=True,
        )

        # Old chunks should be gone
        for old_id in ids_first:
            row = await db_manager.fetchrow("SELECT id FROM chunks WHERE id = $1", old_id)
            assert row is None, f"Old chunk {old_id} not removed after reindex"

        # New chunks should exist
        assert len(ids_second) > 0
        for new_id in ids_second:
            row = await db_manager.fetchrow("SELECT id FROM chunks WHERE id = $1", new_id)
            assert row is not None
