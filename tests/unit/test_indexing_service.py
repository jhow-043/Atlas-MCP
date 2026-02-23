"""Tests for the IndexingService module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from atlas_mcp.vectorization.chunker import ChunkData
from atlas_mcp.vectorization.indexing import (
    IndexingError,
    IndexingService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_indexing_service(
    chunker: MagicMock | None = None,
    embedder: MagicMock | None = None,
    store: MagicMock | None = None,
) -> tuple[IndexingService, MagicMock, MagicMock, MagicMock]:
    """Create an IndexingService with mock dependencies."""
    mock_chunker = chunker or MagicMock()
    mock_embedder = embedder or MagicMock()
    mock_store = store or MagicMock()

    # Default sensible behaviors (only when not provided externally)
    if chunker is None:
        mock_chunker.chunk = MagicMock(
            return_value=[
                ChunkData(
                    content="chunk 1",
                    section_path="Intro",
                    chunk_index=0,
                ),
                ChunkData(
                    content="chunk 2",
                    section_path="Body",
                    chunk_index=1,
                ),
            ]
        )
    if embedder is None:
        mock_embedder.embed_batch = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4]])
    if store is None:
        mock_store.store_chunks = AsyncMock(return_value=[1, 2])
        mock_store.delete_by_document = AsyncMock(return_value=0)

    service = IndexingService(mock_chunker, mock_embedder, mock_store)
    return service, mock_chunker, mock_embedder, mock_store


# ---------------------------------------------------------------------------
# IndexingService properties
# ---------------------------------------------------------------------------


class TestIndexingServiceProperties:
    """Tests for IndexingService properties."""

    def test_should_expose_embedder(self) -> None:
        service, _, mock_embedder, _ = _make_indexing_service()
        assert service.embedder is mock_embedder

    def test_should_expose_store(self) -> None:
        service, _, _, mock_store = _make_indexing_service()
        assert service.store is mock_store


# ---------------------------------------------------------------------------
# IndexingService.index_document
# ---------------------------------------------------------------------------


class TestIndexingServiceIndexDocument:
    """Tests for IndexingService.index_document."""

    async def test_should_chunk_embed_and_store(self) -> None:
        service, mock_chunker, mock_embedder, mock_store = _make_indexing_service()

        ids = await service.index_document(
            document_id=1,
            content="# Title\n\nSome text",
            title="Test Doc",
        )

        assert ids == [1, 2]
        mock_chunker.chunk.assert_called_once_with("# Title\n\nSome text", doc_title="Test Doc")
        mock_embedder.embed_batch.assert_awaited_once_with(["chunk 1", "chunk 2"])
        mock_store.store_chunks.assert_awaited_once()

        # Validate ChunkRecord content
        stored_records = mock_store.store_chunks.call_args[0][0]
        assert len(stored_records) == 2
        assert stored_records[0].document_id == 1
        assert stored_records[0].content == "chunk 1"
        assert stored_records[0].embedding == [0.1, 0.2]
        assert stored_records[1].content == "chunk 2"
        assert stored_records[1].embedding == [0.3, 0.4]

    async def test_should_raise_on_empty_content(self) -> None:
        service, _, _, _ = _make_indexing_service()

        with pytest.raises(IndexingError, match="Cannot index empty document"):
            await service.index_document(document_id=1, content="")

    async def test_should_raise_on_whitespace_only_content(self) -> None:
        service, _, _, _ = _make_indexing_service()

        with pytest.raises(IndexingError, match="Cannot index empty document"):
            await service.index_document(document_id=1, content="   ")

    async def test_should_return_empty_when_no_chunks(self) -> None:
        mock_chunker = MagicMock()
        mock_chunker.chunk = MagicMock(return_value=[])
        service, _, _, _ = _make_indexing_service(chunker=mock_chunker)

        ids = await service.index_document(document_id=1, content="Some content")

        assert ids == []

    async def test_should_reindex_by_removing_first(self) -> None:
        service, _, _, mock_store = _make_indexing_service()

        await service.index_document(
            document_id=1,
            content="# Title\n\nText",
            reindex=True,
        )

        mock_store.delete_by_document.assert_awaited_once_with(1)
        mock_store.store_chunks.assert_awaited_once()

    async def test_should_not_remove_when_not_reindex(self) -> None:
        service, _, _, mock_store = _make_indexing_service()

        await service.index_document(document_id=1, content="# Title\n\nText")

        mock_store.delete_by_document.assert_not_awaited()

    async def test_should_wrap_embedding_error(self) -> None:
        mock_embedder = MagicMock()
        mock_embedder.embed_batch = AsyncMock(side_effect=RuntimeError("API failure"))
        service, _, _, _ = _make_indexing_service(embedder=mock_embedder)

        with pytest.raises(IndexingError, match="Failed to index document"):
            await service.index_document(document_id=1, content="# Content")

    async def test_should_wrap_store_error(self) -> None:
        mock_store = MagicMock()
        mock_store.store_chunks = AsyncMock(side_effect=RuntimeError("DB error"))
        mock_store.delete_by_document = AsyncMock(return_value=0)
        service, _, _, _ = _make_indexing_service(store=mock_store)

        with pytest.raises(IndexingError, match="Failed to index document"):
            await service.index_document(document_id=1, content="# Content")


# ---------------------------------------------------------------------------
# IndexingService.remove_document
# ---------------------------------------------------------------------------


class TestIndexingServiceRemoveDocument:
    """Tests for IndexingService.remove_document."""

    async def test_should_delete_chunks(self) -> None:
        service, _, _, mock_store = _make_indexing_service()
        mock_store.delete_by_document = AsyncMock(return_value=5)

        count = await service.remove_document(42)

        assert count == 5
        mock_store.delete_by_document.assert_awaited_once_with(42)

    async def test_should_return_zero_when_none_found(self) -> None:
        service, _, _, mock_store = _make_indexing_service()
        mock_store.delete_by_document = AsyncMock(return_value=0)

        count = await service.remove_document(999)

        assert count == 0


# ---------------------------------------------------------------------------
# IndexingService.on_status_change
# ---------------------------------------------------------------------------


class TestIndexingServiceOnStatusChange:
    """Tests for the on_status_change callback handler."""

    async def test_should_index_on_approved(self) -> None:
        service, mock_chunker, mock_embedder, mock_store = _make_indexing_service()

        document = {
            "id": 1,
            "title": "ADR-001",
            "content": "# Decision\n\nUse Python.",
        }

        await service.on_status_change(
            document_id=1,
            old_status="IN_REVIEW",
            new_status="APPROVED",
            document=document,
        )

        mock_chunker.chunk.assert_called_once()
        mock_embedder.embed_batch.assert_awaited_once()
        mock_store.store_chunks.assert_awaited_once()

    async def test_should_remove_on_deprecated(self) -> None:
        service, _, _, mock_store = _make_indexing_service()

        await service.on_status_change(
            document_id=1,
            old_status="APPROVED",
            new_status="DEPRECATED",
        )

        mock_store.delete_by_document.assert_awaited_once_with(1)

    async def test_should_ignore_other_transitions(self) -> None:
        service, mock_chunker, _, mock_store = _make_indexing_service()

        await service.on_status_change(
            document_id=1,
            old_status="PROPOSED",
            new_status="IN_REVIEW",
        )

        mock_chunker.chunk.assert_not_called()
        mock_store.delete_by_document.assert_not_awaited()

    async def test_should_not_crash_on_indexing_error(self) -> None:
        mock_embedder = MagicMock()
        mock_embedder.embed_batch = AsyncMock(side_effect=RuntimeError("fail"))
        service, _, _, _ = _make_indexing_service(embedder=mock_embedder)

        # Should not raise — logs the error instead
        await service.on_status_change(
            document_id=1,
            old_status="IN_REVIEW",
            new_status="APPROVED",
            document={"id": 1, "title": "T", "content": "# X\n\nY"},
        )

    async def test_should_not_crash_on_remove_error(self) -> None:
        mock_store = MagicMock()
        mock_store.delete_by_document = AsyncMock(side_effect=RuntimeError("DB down"))
        mock_store.store_chunks = AsyncMock(return_value=[])
        service, _, _, _ = _make_indexing_service(store=mock_store)

        # Should not raise — logs the error instead
        await service.on_status_change(
            document_id=1,
            old_status="APPROVED",
            new_status="DEPRECATED",
        )

    async def test_should_skip_approved_without_document(self) -> None:
        service, mock_chunker, _, _ = _make_indexing_service()

        await service.on_status_change(
            document_id=1,
            old_status="IN_REVIEW",
            new_status="APPROVED",
            document=None,
        )

        # No indexing because document data is not available
        mock_chunker.chunk.assert_not_called()
