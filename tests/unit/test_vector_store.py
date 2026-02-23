"""Tests for the VectorStore module."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from atlas_mcp.vectorization.store import (
    ChunkRecord,
    SearchResult,
    VectorStore,
)

_CODEC_PATCH = "atlas_mcp.persistence.vector_codec.register_vector_codec"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_db() -> MagicMock:
    """Create a mock DatabaseManager with pool and query helpers."""
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])

    # Prepared statement mock
    mock_stmt = AsyncMock()
    mock_conn.prepare = AsyncMock(return_value=mock_stmt)

    mock_acquire = AsyncMock()
    mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire)

    mock_db = MagicMock()
    mock_db.pool = mock_pool
    mock_db.execute = AsyncMock(return_value="DELETE 3")
    mock_db.fetch = AsyncMock(return_value=[])
    mock_db.fetchrow = AsyncMock(return_value=None)
    mock_db.fetchval = AsyncMock(return_value=0)

    return mock_db


def _make_chunk_record(
    document_id: int = 1,
    content: str = "test content",
    section_path: str = "Section A",
    chunk_index: int = 0,
    embedding: list[float] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ChunkRecord:
    """Create a ChunkRecord with defaults."""
    return ChunkRecord(
        document_id=document_id,
        content=content,
        section_path=section_path,
        chunk_index=chunk_index,
        embedding=embedding or [0.1, 0.2, 0.3],
        metadata=metadata or {},
    )


def _make_search_row(
    chunk_id: int = 1,
    document_id: int = 1,
    content: str = "found text",
    section_path: str = "Intro",
    chunk_index: int = 0,
    similarity: float = 0.95,
    metadata: str = "{}",
) -> dict[str, Any]:
    """Create a mock row dict simulating a database record."""
    return {
        "id": chunk_id,
        "document_id": document_id,
        "content": content,
        "section_path": section_path,
        "chunk_index": chunk_index,
        "similarity": similarity,
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# SearchResult dataclass
# ---------------------------------------------------------------------------


class TestSearchResult:
    """Tests for the SearchResult dataclass."""

    def test_should_store_all_fields(self) -> None:
        result = SearchResult(
            chunk_id=1,
            document_id=2,
            content="hello",
            section_path="A > B",
            chunk_index=0,
            similarity=0.95,
        )
        assert result.chunk_id == 1
        assert result.document_id == 2
        assert result.content == "hello"
        assert result.section_path == "A > B"
        assert result.chunk_index == 0
        assert result.similarity == 0.95
        assert result.metadata == {}

    def test_should_be_frozen(self) -> None:
        result = SearchResult(
            chunk_id=1,
            document_id=1,
            content="x",
            section_path="",
            chunk_index=0,
            similarity=0.9,
        )
        with pytest.raises(AttributeError):
            result.content = "y"  # type: ignore[misc]

    def test_should_store_metadata(self) -> None:
        result = SearchResult(
            chunk_id=1,
            document_id=1,
            content="x",
            section_path="",
            chunk_index=0,
            similarity=0.9,
            metadata={"doc_title": "ADR-001"},
        )
        assert result.metadata["doc_title"] == "ADR-001"


# ---------------------------------------------------------------------------
# ChunkRecord dataclass
# ---------------------------------------------------------------------------


class TestChunkRecord:
    """Tests for the ChunkRecord dataclass."""

    def test_should_store_all_fields(self) -> None:
        record = _make_chunk_record()
        assert record.document_id == 1
        assert record.content == "test content"
        assert record.section_path == "Section A"
        assert record.chunk_index == 0
        assert record.embedding == [0.1, 0.2, 0.3]
        assert record.metadata == {}

    def test_should_be_frozen(self) -> None:
        record = _make_chunk_record()
        with pytest.raises(AttributeError):
            record.content = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# VectorStore.store_chunks
# ---------------------------------------------------------------------------


class TestVectorStoreStoreChunks:
    """Tests for VectorStore.store_chunks."""

    async def test_should_raise_on_empty_list(self) -> None:
        mock_db = _make_mock_db()
        store = VectorStore(mock_db)

        with pytest.raises(ValueError, match="Cannot store empty chunks"):
            await store.store_chunks([])

    @patch(
        _CODEC_PATCH,
        new_callable=AsyncMock,
    )
    async def test_should_insert_single_chunk(self, mock_register: AsyncMock) -> None:
        mock_db = _make_mock_db()
        mock_conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        mock_stmt = mock_conn.prepare.return_value

        # Simulate RETURNING id
        mock_row = {"id": 42}
        mock_stmt.fetchrow = AsyncMock(return_value=mock_row)

        store = VectorStore(mock_db)
        chunk = _make_chunk_record()
        ids = await store.store_chunks([chunk])

        assert ids == [42]
        mock_register.assert_awaited_once()
        mock_conn.prepare.assert_awaited_once()
        mock_stmt.fetchrow.assert_awaited_once_with(
            1,
            "test content",
            "Section A",
            0,
            [0.1, 0.2, 0.3],
            "{}",
        )

    @patch(
        _CODEC_PATCH,
        new_callable=AsyncMock,
    )
    async def test_should_insert_multiple_chunks(self, mock_register: AsyncMock) -> None:
        mock_db = _make_mock_db()
        mock_conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        mock_stmt = mock_conn.prepare.return_value

        mock_stmt.fetchrow = AsyncMock(side_effect=[{"id": 1}, {"id": 2}, {"id": 3}])

        store = VectorStore(mock_db)
        chunks = [
            _make_chunk_record(chunk_index=0),
            _make_chunk_record(chunk_index=1),
            _make_chunk_record(chunk_index=2),
        ]
        ids = await store.store_chunks(chunks)

        assert ids == [1, 2, 3]
        assert mock_stmt.fetchrow.await_count == 3

    @patch(
        _CODEC_PATCH,
        new_callable=AsyncMock,
    )
    async def test_should_serialize_metadata_as_json(self, mock_register: AsyncMock) -> None:
        mock_db = _make_mock_db()
        mock_conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        mock_stmt = mock_conn.prepare.return_value
        mock_stmt.fetchrow = AsyncMock(return_value={"id": 1})

        store = VectorStore(mock_db)
        chunk = _make_chunk_record(metadata={"doc_title": "ADR-001"})
        await store.store_chunks([chunk])

        call_args = mock_stmt.fetchrow.call_args
        metadata_arg = call_args[0][5]
        parsed = json.loads(metadata_arg)
        assert parsed == {"doc_title": "ADR-001"}

    @patch(
        _CODEC_PATCH,
        new_callable=AsyncMock,
    )
    async def test_should_skip_none_returning_rows(self, mock_register: AsyncMock) -> None:
        mock_db = _make_mock_db()
        mock_conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        mock_stmt = mock_conn.prepare.return_value
        mock_stmt.fetchrow = AsyncMock(side_effect=[{"id": 1}, None, {"id": 3}])

        store = VectorStore(mock_db)
        chunks = [
            _make_chunk_record(chunk_index=0),
            _make_chunk_record(chunk_index=1),
            _make_chunk_record(chunk_index=2),
        ]
        ids = await store.store_chunks(chunks)

        assert ids == [1, 3]


# ---------------------------------------------------------------------------
# VectorStore.search
# ---------------------------------------------------------------------------


class TestVectorStoreSearch:
    """Tests for VectorStore.search."""

    @patch(
        _CODEC_PATCH,
        new_callable=AsyncMock,
    )
    async def test_should_return_results_above_threshold(self, mock_register: AsyncMock) -> None:
        mock_db = _make_mock_db()
        mock_conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(
            return_value=[
                _make_search_row(similarity=0.95),
                _make_search_row(chunk_id=2, similarity=0.3),
            ]
        )

        store = VectorStore(mock_db)
        results = await store.search(
            [0.1, 0.2],
            limit=5,
            similarity_threshold=0.5,
        )

        assert len(results) == 1
        assert results[0].similarity == 0.95

    @patch(
        _CODEC_PATCH,
        new_callable=AsyncMock,
    )
    async def test_should_return_all_without_threshold(self, mock_register: AsyncMock) -> None:
        mock_db = _make_mock_db()
        mock_conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(
            return_value=[
                _make_search_row(similarity=0.9),
                _make_search_row(chunk_id=2, similarity=0.1),
            ]
        )

        store = VectorStore(mock_db)
        results = await store.search([0.1, 0.2], limit=10)

        assert len(results) == 2

    @patch(
        _CODEC_PATCH,
        new_callable=AsyncMock,
    )
    async def test_should_parse_metadata_from_json_string(self, mock_register: AsyncMock) -> None:
        mock_db = _make_mock_db()
        mock_conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(
            return_value=[
                _make_search_row(metadata=json.dumps({"doc_title": "ADR-001"})),
            ]
        )

        store = VectorStore(mock_db)
        results = await store.search([0.1, 0.2])

        assert results[0].metadata == {"doc_title": "ADR-001"}

    @patch(
        _CODEC_PATCH,
        new_callable=AsyncMock,
    )
    async def test_should_handle_dict_metadata(self, mock_register: AsyncMock) -> None:
        mock_db = _make_mock_db()
        mock_conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(
            return_value=[
                _make_search_row(metadata={"key": "value"}),  # type: ignore[arg-type]
            ]
        )

        store = VectorStore(mock_db)
        results = await store.search([0.1, 0.2])

        assert results[0].metadata == {"key": "value"}

    @patch(
        _CODEC_PATCH,
        new_callable=AsyncMock,
    )
    async def test_should_return_empty_for_no_matches(self, mock_register: AsyncMock) -> None:
        mock_db = _make_mock_db()
        mock_conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(return_value=[])

        store = VectorStore(mock_db)
        results = await store.search([0.1, 0.2])

        assert results == []

    @patch(
        _CODEC_PATCH,
        new_callable=AsyncMock,
    )
    async def test_should_apply_document_id_filter(self, mock_register: AsyncMock) -> None:
        mock_db = _make_mock_db()
        mock_conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(return_value=[])

        store = VectorStore(mock_db)
        await store.search([0.1, 0.2], filters={"document_id": 42})

        query = mock_conn.fetch.call_args[0][0]
        assert "c.document_id = $2" in query
        assert mock_conn.fetch.call_args[0][2] == 42

    @patch(
        _CODEC_PATCH,
        new_callable=AsyncMock,
    )
    async def test_should_join_documents_for_doc_type_filter(
        self, mock_register: AsyncMock
    ) -> None:
        mock_db = _make_mock_db()
        mock_conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(return_value=[])

        store = VectorStore(mock_db)
        await store.search([0.1, 0.2], filters={"doc_type": "adr"})

        query = mock_conn.fetch.call_args[0][0]
        assert "JOIN documents d" in query
        assert "d.doc_type = $2" in query

    @patch(
        _CODEC_PATCH,
        new_callable=AsyncMock,
    )
    async def test_should_join_documents_for_status_filter(self, mock_register: AsyncMock) -> None:
        mock_db = _make_mock_db()
        mock_conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(return_value=[])

        store = VectorStore(mock_db)
        await store.search([0.1, 0.2], filters={"status": "APPROVED"})

        query = mock_conn.fetch.call_args[0][0]
        assert "JOIN documents d" in query
        assert "d.status = $2" in query

    @patch(
        _CODEC_PATCH,
        new_callable=AsyncMock,
    )
    async def test_should_combine_multiple_filters(self, mock_register: AsyncMock) -> None:
        mock_db = _make_mock_db()
        mock_conn = mock_db.pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(return_value=[])

        store = VectorStore(mock_db)
        await store.search(
            [0.1, 0.2],
            filters={"document_id": 1, "doc_type": "adr", "status": "APPROVED"},
        )

        query = mock_conn.fetch.call_args[0][0]
        assert "c.document_id = $2" in query
        assert "d.doc_type = $3" in query
        assert "d.status = $4" in query
        assert "JOIN documents d" in query


# ---------------------------------------------------------------------------
# VectorStore.delete_by_document
# ---------------------------------------------------------------------------


class TestVectorStoreDeleteByDocument:
    """Tests for VectorStore.delete_by_document."""

    async def test_should_delete_and_return_count(self) -> None:
        mock_db = _make_mock_db()
        mock_db.execute = AsyncMock(return_value="DELETE 5")

        store = VectorStore(mock_db)
        count = await store.delete_by_document(42)

        assert count == 5
        mock_db.execute.assert_awaited_once_with("DELETE FROM chunks WHERE document_id = $1", 42)

    async def test_should_return_zero_when_none_deleted(self) -> None:
        mock_db = _make_mock_db()
        mock_db.execute = AsyncMock(return_value="DELETE 0")

        store = VectorStore(mock_db)
        count = await store.delete_by_document(999)

        assert count == 0

    async def test_should_handle_empty_result(self) -> None:
        mock_db = _make_mock_db()
        mock_db.execute = AsyncMock(return_value="")

        store = VectorStore(mock_db)
        count = await store.delete_by_document(1)

        assert count == 0


# ---------------------------------------------------------------------------
# VectorStore.get_stats
# ---------------------------------------------------------------------------


class TestVectorStoreGetStats:
    """Tests for VectorStore.get_stats."""

    async def test_should_return_stats(self) -> None:
        mock_db = _make_mock_db()
        mock_db.fetchval = AsyncMock(side_effect=[100, 10])

        store = VectorStore(mock_db)
        stats = await store.get_stats()

        assert stats["total_chunks"] == 100
        assert stats["document_count"] == 10
        assert stats["avg_chunks_per_document"] == 10.0

    async def test_should_handle_zero_documents(self) -> None:
        mock_db = _make_mock_db()
        mock_db.fetchval = AsyncMock(side_effect=[0, 0])

        store = VectorStore(mock_db)
        stats = await store.get_stats()

        assert stats["total_chunks"] == 0
        assert stats["document_count"] == 0
        assert stats["avg_chunks_per_document"] == 0.0

    async def test_should_handle_none_values(self) -> None:
        mock_db = _make_mock_db()
        mock_db.fetchval = AsyncMock(side_effect=[None, None])

        store = VectorStore(mock_db)
        stats = await store.get_stats()

        assert stats["total_chunks"] == 0
        assert stats["document_count"] == 0
        assert stats["avg_chunks_per_document"] == 0.0


# ---------------------------------------------------------------------------
# VectorStore.get_chunks_by_document
# ---------------------------------------------------------------------------


class TestVectorStoreGetChunksByDocument:
    """Tests for VectorStore.get_chunks_by_document."""

    async def test_should_return_chunks_in_order(self) -> None:
        mock_db = _make_mock_db()
        mock_db.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "content": "chunk 1",
                    "section_path": "Intro",
                    "chunk_index": 0,
                    "metadata": "{}",
                },
                {
                    "id": 2,
                    "content": "chunk 2",
                    "section_path": "Body",
                    "chunk_index": 1,
                    "metadata": json.dumps({"key": "val"}),
                },
            ]
        )

        store = VectorStore(mock_db)
        chunks = await store.get_chunks_by_document(1)

        assert len(chunks) == 2
        assert chunks[0]["content"] == "chunk 1"
        assert chunks[1]["metadata"] == {"key": "val"}

    async def test_should_return_empty_for_no_chunks(self) -> None:
        mock_db = _make_mock_db()
        mock_db.fetch = AsyncMock(return_value=[])

        store = VectorStore(mock_db)
        chunks = await store.get_chunks_by_document(999)

        assert chunks == []

    async def test_should_handle_dict_metadata(self) -> None:
        mock_db = _make_mock_db()
        mock_db.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "content": "chunk",
                    "section_path": "",
                    "chunk_index": 0,
                    "metadata": {"already": "parsed"},
                },
            ]
        )

        store = VectorStore(mock_db)
        chunks = await store.get_chunks_by_document(1)

        assert chunks[0]["metadata"] == {"already": "parsed"}
