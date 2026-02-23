"""Semantic Markdown chunker for document vectorization.

Splits Markdown documents into semantically coherent chunks
based on header hierarchy (``#``, ``##``, ``###``), preserving
section context via ``section_path``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

#: Maximum characters per chunk before subdivision.
MAX_CHUNK_SIZE: Final[int] = 2000

#: Minimum characters to keep a chunk (otherwise merge with previous).
MIN_CHUNK_SIZE: Final[int] = 100

#: Regex matching Markdown headers (levels 1-6).
_HEADER_RE: Final[re.Pattern[str]] = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class ChunkData:
    """A single chunk extracted from a document.

    Attributes:
        content: The text content of the chunk.
        section_path: Hierarchical path (e.g. ``"Decisão > Justificativa"``).
        chunk_index: Zero-based position within the document.
        metadata: Additional metadata about the chunk.
    """

    content: str
    section_path: str = ""
    chunk_index: int = 0
    metadata: dict[str, str] = field(default_factory=dict)


def _build_section_path(header_stack: list[tuple[int, str]]) -> str:
    """Build a section path string from the current header stack.

    Args:
        header_stack: List of ``(level, title)`` tuples representing
            the current header hierarchy.

    Returns:
        A ``" > "``-joined path string.
    """
    if not header_stack:
        return ""
    return " > ".join(title for _, title in header_stack)


def _split_by_paragraphs(text: str, max_size: int) -> list[str]:
    """Split text into paragraph-based sub-chunks under max_size.

    Args:
        text: The text to split.
        max_size: Maximum character count per sub-chunk.

    Returns:
        A list of text sub-chunks.
    """
    paragraphs = re.split(r"\n{2,}", text)
    sub_chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_len = len(para)

        if current_len + para_len + 2 > max_size and current:
            sub_chunks.append("\n\n".join(current))
            current = [para]
            current_len = para_len
        else:
            current.append(para)
            current_len += para_len + 2

    if current:
        sub_chunks.append("\n\n".join(current))

    return sub_chunks if sub_chunks else [text]


class MarkdownChunker:
    """Split Markdown documents into semantic chunks by header hierarchy.

    Chunks are created at each header boundary. Oversized chunks are
    subdivided by paragraph. Undersized chunks are merged with the
    previous chunk.

    Args:
        max_chunk_size: Maximum characters per chunk.
        min_chunk_size: Minimum characters to keep a standalone chunk.
    """

    def __init__(
        self,
        max_chunk_size: int = MAX_CHUNK_SIZE,
        min_chunk_size: int = MIN_CHUNK_SIZE,
    ) -> None:
        """Initialize the chunker.

        Args:
            max_chunk_size: Maximum characters per chunk.
            min_chunk_size: Minimum characters to keep a standalone chunk.
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size

    def chunk(self, text: str, doc_title: str = "") -> list[ChunkData]:
        """Chunk a Markdown document into semantic sections.

        Args:
            text: The full Markdown text.
            doc_title: Optional document title for metadata.

        Returns:
            A list of :class:`ChunkData` objects.
        """
        if not text or not text.strip():
            return []

        raw_sections = self._split_by_headers(text)
        merged = self._merge_small_sections(raw_sections)
        expanded = self._subdivide_large_sections(merged)

        chunks: list[ChunkData] = []
        for idx, (section_path, content) in enumerate(expanded):
            metadata: dict[str, str] = {}
            if doc_title:
                metadata["doc_title"] = doc_title
            chunks.append(
                ChunkData(
                    content=content.strip(),
                    section_path=section_path,
                    chunk_index=idx,
                    metadata=metadata,
                )
            )

        return chunks

    def _split_by_headers(self, text: str) -> list[tuple[str, str]]:
        """Split text into sections at header boundaries.

        Args:
            text: The Markdown text.

        Returns:
            List of ``(section_path, content)`` tuples.
        """
        sections: list[tuple[str, str]] = []
        header_stack: list[tuple[int, str]] = []
        matches = list(_HEADER_RE.finditer(text))

        if not matches:
            return [("", text.strip())]

        # Content before first header
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append(("", preamble))

        for i, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()

            # Update header stack: pop headers at same or deeper level
            while header_stack and header_stack[-1][0] >= level:
                header_stack.pop()
            header_stack.append((level, title))

            # Extract content between this header and the next
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()

            section_path = _build_section_path(header_stack)

            if content:
                sections.append((section_path, content))

        return sections

    def _merge_small_sections(self, sections: list[tuple[str, str]]) -> list[tuple[str, str]]:
        """Merge undersized sections with the previous section.

        Args:
            sections: List of ``(section_path, content)`` tuples.

        Returns:
            Merged list of sections.
        """
        if not sections:
            return []

        merged: list[tuple[str, str]] = [sections[0]]

        for section_path, content in sections[1:]:
            if len(content) < self.min_chunk_size and merged:
                prev_path, prev_content = merged[-1]
                merged[-1] = (prev_path, prev_content + "\n\n" + content)
            else:
                merged.append((section_path, content))

        return merged

    def _subdivide_large_sections(self, sections: list[tuple[str, str]]) -> list[tuple[str, str]]:
        """Subdivide oversized sections by paragraph.

        Args:
            sections: List of ``(section_path, content)`` tuples.

        Returns:
            Expanded list with oversized sections split.
        """
        expanded: list[tuple[str, str]] = []

        for section_path, content in sections:
            if len(content) <= self.max_chunk_size:
                expanded.append((section_path, content))
            else:
                sub_chunks = _split_by_paragraphs(content, self.max_chunk_size)
                for sub in sub_chunks:
                    expanded.append((section_path, sub))

        return expanded
