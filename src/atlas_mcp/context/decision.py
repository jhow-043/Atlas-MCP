"""Decision Context Layer — ADR parser and provider.

Parses Architecture Decision Records from Markdown files
and provides structured data for MCP resources.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Regex patterns for ADR metadata extraction
_TITLE_PATTERN = re.compile(r"^#\s+ADR-(\d+):\s*(.+)$", re.MULTILINE)
_META_PATTERN = re.compile(
    r"^\*\*(?P<key>[^*:]+):\*\*\s*(?P<value>.+)$",
    re.MULTILINE,
)
_SECTION_PATTERN = re.compile(r"^###\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class ADRRecord:
    """Parsed representation of an Architecture Decision Record.

    Attributes:
        id: The ADR number (e.g. ``1`` for ADR-001).
        title: The decision title.
        date: The creation date string.
        status: The lifecycle status (PROPOSED, APPROVED, etc.).
        author: The author name.
        tags: List of tag strings.
        sections: Mapping of section name to section content.
        file_path: Path to the source Markdown file.
    """

    id: int
    title: str
    date: str = ""
    status: str = "PROPOSED"
    author: str = ""
    tags: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)
    file_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to a serializable dictionary.

        Returns:
            A dictionary suitable for JSON serialization.
        """
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "status": self.status,
            "author": self.author,
            "tags": self.tags,
            "sections": self.sections,
            "file_path": self.file_path,
        }

    def to_summary(self) -> dict[str, Any]:
        """Convert to a summary dict (without full section content).

        Returns:
            A dictionary with id, title, date, status, author, tags.
        """
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "status": self.status,
            "author": self.author,
            "tags": self.tags,
        }


def parse_adr(content: str, file_path: str = "") -> ADRRecord:
    """Parse an ADR Markdown file into an ``ADRRecord``.

    The parser extracts the title from ``# ADR-NNN: Title``,
    metadata from ``**Key:** Value`` lines, and section bodies
    from ``### Section`` headings.

    Args:
        content: The raw Markdown text.
        file_path: Optional path for reference.

    Returns:
        A parsed :class:`ADRRecord`.

    Raises:
        ValueError: If the title line cannot be found or parsed.
    """
    # Extract title and ID
    title_match = _TITLE_PATTERN.search(content)
    if not title_match:
        raise ValueError(f"Could not parse ADR title from: {file_path or 'input'}")

    adr_id = int(title_match.group(1))
    title = title_match.group(2).strip()

    # Extract metadata
    meta: dict[str, str] = {}
    for match in _META_PATTERN.finditer(content):
        key = match.group("key").strip().lower()
        value = match.group("value").strip()
        meta[key] = value

    date = meta.get("data", meta.get("date", ""))
    status = meta.get("status", "PROPOSED")
    author = meta.get("autor", meta.get("author", ""))
    tags_raw = meta.get("tags", "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    # Extract sections
    sections: dict[str, str] = {}
    section_matches = list(_SECTION_PATTERN.finditer(content))
    for i, sec_match in enumerate(section_matches):
        section_name = sec_match.group(1).strip()
        start = sec_match.end()
        end = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(content)
        section_body = content[start:end].strip()
        # Remove trailing section separator (---)
        section_body = re.sub(r"\n---\s*$", "", section_body).strip()
        sections[section_name] = section_body

    return ADRRecord(
        id=adr_id,
        title=title,
        date=date,
        status=status,
        author=author,
        tags=tags,
        sections=sections,
        file_path=file_path,
    )


class DecisionContextProvider:
    """Read and provide ADR data from the filesystem.

    Scans a directory for ``ADR-*.md`` files, parses them,
    and provides access by ID or as a full list.

    Args:
        adr_directory: Path to the directory containing ADR files.
    """

    def __init__(self, adr_directory: Path | None = None) -> None:
        """Initialize with ADR directory path.

        Args:
            adr_directory: Path to the ADR directory.
                Defaults to ``docs/adr/`` under the project root.
        """
        self._adr_dir = adr_directory or self._discover_adr_dir()
        self._cache: dict[int, ADRRecord] | None = None

    @staticmethod
    def _discover_adr_dir() -> Path:
        """Find the ADR directory relative to the project root.

        Returns:
            Path to the ``docs/adr/`` directory.

        Raises:
            FileNotFoundError: If the directory cannot be found.
        """
        current = Path(__file__).resolve().parent
        for parent in [current, *current.parents]:
            adr_path = parent / "docs" / "adr"
            if adr_path.is_dir():
                return adr_path
        raise FileNotFoundError("Could not find docs/adr/ directory")

    def _load_adrs(self) -> dict[int, ADRRecord]:
        """Load and cache all ADRs from the filesystem.

        Returns:
            A mapping of ADR ID to ``ADRRecord``.
        """
        if self._cache is not None:
            return self._cache

        self._cache = {}
        if not self._adr_dir.exists():
            logger.warning("ADR directory does not exist: %s", self._adr_dir)
            return self._cache

        for adr_file in sorted(self._adr_dir.glob("ADR-*.md")):
            # Skip template
            if "template" in adr_file.name.lower():
                continue
            try:
                content = adr_file.read_text(encoding="utf-8")
                record = parse_adr(content, file_path=str(adr_file))
                self._cache[record.id] = record
                logger.debug("Parsed ADR-%03d: %s", record.id, record.title)
            except (ValueError, OSError) as exc:
                logger.warning("Failed to parse %s: %s", adr_file.name, exc)

        logger.info("Loaded %d ADR(s) from %s", len(self._cache), self._adr_dir)
        return self._cache

    def invalidate_cache(self) -> None:
        """Clear the cached ADR data for reloading."""
        self._cache = None

    def list_adrs(self) -> list[dict[str, Any]]:
        """Return a summary list of all ADRs.

        Returns:
            A list of summary dicts (id, title, date, status, author, tags).
        """
        adrs = self._load_adrs()
        return [adr.to_summary() for adr in sorted(adrs.values(), key=lambda a: a.id)]

    def get_adr(self, adr_id: int) -> dict[str, Any] | None:
        """Return full details for a specific ADR.

        Args:
            adr_id: The ADR number to retrieve.

        Returns:
            A full dict representation, or ``None`` if not found.
        """
        adrs = self._load_adrs()
        record = adrs.get(adr_id)
        return record.to_dict() if record else None
