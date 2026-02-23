"""Tool: register_adr — Create and register an Architecture Decision Record.

Creates a Markdown ADR file on the filesystem and optionally
persists metadata to the database via GovernanceService.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def _discover_adr_dir() -> Path:
    """Locate the ``docs/adr`` directory from the project root.

    Returns:
        The resolved path to the ADR directory.

    Raises:
        FileNotFoundError: If the directory cannot be found.
    """
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "docs" / "adr"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("Could not locate docs/adr directory")


def _next_adr_id(adr_dir: Path) -> int:
    """Determine the next ADR ID by scanning existing files.

    Args:
        adr_dir: Path to the ADR directory.

    Returns:
        The next sequential ADR ID number.
    """
    pattern = re.compile(r"ADR-(\d+)")
    max_id = 0
    for f in adr_dir.glob("ADR-*.md"):
        match = pattern.search(f.name)
        if match:
            adr_num = int(match.group(1))
            if adr_num > max_id:
                max_id = adr_num
    return max_id + 1


def _render_adr_markdown(
    adr_id: int,
    title: str,
    context: str,
    decision: str,
    consequences: str,
    alternatives_considered: str = "",
    tags: str = "",
    author: str = "atlas-mcp",
) -> str:
    """Render an ADR as a Markdown string.

    Args:
        adr_id: The ADR number.
        title: The ADR title.
        context: The context/problem description.
        decision: The decision made.
        consequences: The consequences of the decision.
        alternatives_considered: Optional alternatives table/text.
        tags: Comma-separated tags.
        author: Author name.

    Returns:
        The complete ADR Markdown content.
    """
    date = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    sections = [
        f"# ADR-{adr_id:03d}: {title}",
        "",
        f"**Data:** {date}  ",
        "**Status:** PROPOSED  ",
        f"**Autor:** {author}  ",
    ]

    if tags:
        sections.append(f"**Tags:** {tags}")

    sections.extend(["", "---", "", "### Contexto", "", context])
    sections.extend(["", "### Decisão", "", decision])

    if alternatives_considered:
        sections.extend(["", "### Alternativas Consideradas", "", alternatives_considered])

    sections.extend(["", "### Consequências", "", consequences])
    sections.append("")

    return "\n".join(sections)


def register_register_adr(server: FastMCP) -> None:
    """Register the ``register_adr`` tool on the MCP server.

    The tool creates an ADR Markdown file in ``docs/adr/`` with
    auto-incrementing ID and returns the created ADR metadata.

    Args:
        server: The FastMCP server instance to register on.
    """

    @server.tool(name="register_adr", description="Register a new Architecture Decision Record")
    def register_adr(
        title: str,
        context: str,
        decision: str,
        consequences: str,
        alternatives_considered: str = "",
        tags: str = "",
        author: str = "atlas-mcp",
    ) -> dict[str, Any]:
        """Create a new ADR file and return its metadata.

        Args:
            title: The ADR title.
            context: The context/problem description.
            decision: The decision made.
            consequences: The consequences of the decision.
            alternatives_considered: Optional alternatives considered.
            tags: Comma-separated tags.
            author: Author name.

        Returns:
            A dictionary with the created ADR metadata.
        """
        if not title.strip():
            return {"error": "title cannot be empty"}
        if not context.strip():
            return {"error": "context cannot be empty"}
        if not decision.strip():
            return {"error": "decision cannot be empty"}
        if not consequences.strip():
            return {"error": "consequences cannot be empty"}

        try:
            adr_dir = _discover_adr_dir()
        except FileNotFoundError:
            return {"error": "Could not locate docs/adr directory"}

        adr_id = _next_adr_id(adr_dir)
        filename = f"ADR-{adr_id:03d}-{_slugify(title)}.md"
        filepath = adr_dir / filename

        content = _render_adr_markdown(
            adr_id=adr_id,
            title=title,
            context=context,
            decision=decision,
            consequences=consequences,
            alternatives_considered=alternatives_considered,
            tags=tags,
            author=author,
        )

        filepath.write_text(content, encoding="utf-8")

        logger.info("Created ADR-%03d: %s at %s", adr_id, title, filepath)

        return {
            "status": "created",
            "adr_id": adr_id,
            "title": title,
            "filename": filename,
            "path": str(filepath),
            "tags": [t.strip() for t in tags.split(",") if t.strip()] if tags else [],
        }

    logger.info("Registered tool: register_adr")


def _slugify(text: str) -> str:
    """Convert text to a URL/filename-friendly slug.

    Args:
        text: The text to slugify.

    Returns:
        A lowercase, hyphen-separated slug.
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")
