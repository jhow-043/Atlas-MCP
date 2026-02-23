"""Tests for the MarkdownChunker module."""

from __future__ import annotations

import pytest

from atlas_mcp.vectorization.chunker import (
    MAX_CHUNK_SIZE,
    MIN_CHUNK_SIZE,
    ChunkData,
    MarkdownChunker,
    _build_section_path,
    _split_by_paragraphs,
)


class TestChunkData:
    """Tests for the ChunkData dataclass."""

    def test_should_store_fields(self) -> None:
        chunk = ChunkData(content="hello", section_path="A > B", chunk_index=0)
        assert chunk.content == "hello"
        assert chunk.section_path == "A > B"
        assert chunk.chunk_index == 0
        assert chunk.metadata == {}

    def test_should_store_metadata(self) -> None:
        chunk = ChunkData(
            content="text",
            section_path="",
            chunk_index=1,
            metadata={"doc_title": "Test"},
        )
        assert chunk.metadata["doc_title"] == "Test"

    def test_should_be_frozen(self) -> None:
        chunk = ChunkData(content="x", section_path="", chunk_index=0)
        with pytest.raises(AttributeError):
            chunk.content = "y"  # type: ignore[misc]

    def test_should_have_default_empty_path(self) -> None:
        chunk = ChunkData(content="x")
        assert chunk.section_path == ""
        assert chunk.chunk_index == 0


class TestBuildSectionPath:
    """Tests for _build_section_path helper."""

    def test_should_return_empty_for_empty_stack(self) -> None:
        assert _build_section_path([]) == ""

    def test_should_return_single_title(self) -> None:
        assert _build_section_path([(1, "Intro")]) == "Intro"

    def test_should_join_with_separator(self) -> None:
        stack = [(1, "A"), (2, "B"), (3, "C")]
        assert _build_section_path(stack) == "A > B > C"


class TestSplitByParagraphs:
    """Tests for _split_by_paragraphs helper."""

    def test_should_return_single_chunk_if_small(self) -> None:
        result = _split_by_paragraphs("Short text.", 100)
        assert len(result) == 1
        assert result[0] == "Short text."

    def test_should_split_large_text(self) -> None:
        para1 = "A" * 60
        para2 = "B" * 60
        text = f"{para1}\n\n{para2}"
        result = _split_by_paragraphs(text, 80)
        assert len(result) == 2
        assert para1 in result[0]
        assert para2 in result[1]

    def test_should_skip_empty_paragraphs(self) -> None:
        text = "First\n\n\n\nSecond"
        result = _split_by_paragraphs(text, 1000)
        assert len(result) == 1
        assert "First" in result[0]
        assert "Second" in result[0]

    def test_should_return_original_if_no_split_possible(self) -> None:
        text = "A" * 200
        result = _split_by_paragraphs(text, 100)
        # Single paragraph can't be split further
        assert len(result) == 1
        assert result[0] == text


class TestMarkdownChunkerInit:
    """Tests for MarkdownChunker initialization."""

    def test_should_use_default_sizes(self) -> None:
        chunker = MarkdownChunker()
        assert chunker.max_chunk_size == MAX_CHUNK_SIZE
        assert chunker.min_chunk_size == MIN_CHUNK_SIZE

    def test_should_accept_custom_sizes(self) -> None:
        chunker = MarkdownChunker(max_chunk_size=500, min_chunk_size=50)
        assert chunker.max_chunk_size == 500
        assert chunker.min_chunk_size == 50


class TestMarkdownChunkerChunk:
    """Tests for MarkdownChunker.chunk method."""

    def test_should_return_empty_for_empty_text(self) -> None:
        chunker = MarkdownChunker()
        assert chunker.chunk("") == []
        assert chunker.chunk("   ") == []

    def test_should_chunk_plain_text_without_headers(self) -> None:
        chunker = MarkdownChunker()
        result = chunker.chunk("Just some plain text.")
        assert len(result) == 1
        assert result[0].content == "Just some plain text."
        assert result[0].section_path == ""

    def test_should_chunk_by_h1_headers(self) -> None:
        text = "# Section A\nContent A\n# Section B\nContent B"
        chunker = MarkdownChunker(min_chunk_size=1)
        result = chunker.chunk(text)
        assert len(result) == 2
        assert result[0].section_path == "Section A"
        assert "Content A" in result[0].content
        assert result[1].section_path == "Section B"
        assert "Content B" in result[1].content

    def test_should_chunk_by_h2_headers(self) -> None:
        text = "## Intro\nText here\n## Details\nMore text"
        chunker = MarkdownChunker(min_chunk_size=1)
        result = chunker.chunk(text)
        assert len(result) == 2
        assert result[0].section_path == "Intro"
        assert result[1].section_path == "Details"

    def test_should_preserve_header_hierarchy(self) -> None:
        text = "# Root\nTop\n## Child\nMid\n### Grandchild\nDeep"
        chunker = MarkdownChunker(min_chunk_size=1)
        result = chunker.chunk(text)
        paths = [c.section_path for c in result]
        assert "Root" in paths
        assert "Root > Child" in paths
        assert "Root > Child > Grandchild" in paths

    def test_should_handle_sibling_headers(self) -> None:
        text = "# A\nFirst\n## B\nSecond\n## C\nThird"
        chunker = MarkdownChunker(min_chunk_size=1)
        result = chunker.chunk(text)
        paths = [c.section_path for c in result]
        assert "A" in paths
        assert "A > B" in paths
        assert "A > C" in paths

    def test_should_include_preamble_before_first_header(self) -> None:
        text = "Preamble text\n\n# Section\nContent"
        chunker = MarkdownChunker()
        result = chunker.chunk(text)
        assert result[0].section_path == ""
        assert "Preamble" in result[0].content

    def test_should_set_sequential_chunk_index(self) -> None:
        text = "# A\nOne\n# B\nTwo\n# C\nThree"
        chunker = MarkdownChunker()
        result = chunker.chunk(text)
        indices = [c.chunk_index for c in result]
        assert indices == list(range(len(result)))

    def test_should_include_doc_title_in_metadata(self) -> None:
        text = "# Section\nContent"
        chunker = MarkdownChunker()
        result = chunker.chunk(text, doc_title="My Doc")
        assert all(c.metadata.get("doc_title") == "My Doc" for c in result)

    def test_should_not_include_doc_title_when_empty(self) -> None:
        text = "# Section\nContent"
        chunker = MarkdownChunker()
        result = chunker.chunk(text)
        assert all("doc_title" not in c.metadata for c in result)

    def test_should_merge_small_sections(self) -> None:
        # Create sections where second is very small
        text = "# Big Section\n" + "A" * 200 + "\n# Tiny\nX"
        chunker = MarkdownChunker(min_chunk_size=100)
        result = chunker.chunk(text)
        # The tiny section should be merged into the previous
        assert len(result) == 1

    def test_should_subdivide_large_sections(self) -> None:
        # Create a section with multiple paragraphs exceeding max
        para1 = "A" * 150
        para2 = "B" * 150
        para3 = "C" * 150
        text = f"# Section\n{para1}\n\n{para2}\n\n{para3}"
        chunker = MarkdownChunker(max_chunk_size=200, min_chunk_size=10)
        result = chunker.chunk(text)
        # Should be split into multiple chunks
        assert len(result) > 1
        # All chunks should have the same section_path
        assert all(c.section_path == "Section" for c in result)

    def test_should_handle_adr_format(self) -> None:
        text = """# ADR-001 — Use FastMCP SDK

## Status
APPROVED

## Contexto
We need an MCP SDK for protocol handling.

## Decisão
Use the official FastMCP Python SDK.

## Consequências
Simplified protocol implementation.
"""
        chunker = MarkdownChunker(min_chunk_size=10)
        result = chunker.chunk(text, doc_title="ADR-001")
        assert len(result) >= 3
        paths = [c.section_path for c in result]
        assert any("Status" in p for p in paths)
        assert any("Contexto" in p for p in paths) or any("Decisão" in p for p in paths)

    def test_should_handle_header_level_jumps(self) -> None:
        # Jump from h1 to h3 (skipping h2)
        text = "# Root\nTop\n### Deep\nContent"
        chunker = MarkdownChunker(min_chunk_size=1)
        result = chunker.chunk(text)
        paths = [c.section_path for c in result]
        assert "Root" in paths
        assert "Root > Deep" in paths

    def test_should_handle_back_to_higher_level(self) -> None:
        text = "# A\nFirst\n## A1\nSub\n# B\nSecond"
        chunker = MarkdownChunker(min_chunk_size=1)
        result = chunker.chunk(text)
        paths = [c.section_path for c in result]
        assert "A" in paths
        assert "A > A1" in paths
        assert "B" in paths

    def test_should_strip_whitespace_from_content(self) -> None:
        text = "# Section\n\n   Content with spaces   \n\n"
        chunker = MarkdownChunker()
        result = chunker.chunk(text)
        assert result[0].content == "Content with spaces"

    def test_should_handle_single_header_no_content(self) -> None:
        text = "# Just a Title"
        chunker = MarkdownChunker()
        result = chunker.chunk(text)
        # No content after header → no chunk
        assert len(result) == 0

    def test_should_handle_multiple_empty_headers(self) -> None:
        text = "# A\n# B\n# C\nFinally content"
        chunker = MarkdownChunker()
        result = chunker.chunk(text)
        # Only C has content
        assert len(result) >= 1
        assert "Finally content" in result[-1].content
