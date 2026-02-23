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

from mcp.server.fastmcp.exceptions import ToolError

from atlas_mcp.protocol.errors import format_tool_error

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


_MAX_TITLE_LENGTH = 200
_MAX_FIELD_LENGTH = 10_000


def _validate_adr_params(
    title: str,
    context: str,
    decision: str,
    consequences: str,
) -> None:
    """Validate register_adr parameters.

    Args:
        title: The ADR title.
        context: The context/problem description.
        decision: The decision made.
        consequences: The consequences of the decision.

    Raises:
        ToolError: If any required parameter is empty or too long.
    """
    if not title or not title.strip():
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                "Parameter 'title' must be a non-empty string",
                {"parameter": "title"},
            )
        )
    if len(title) > _MAX_TITLE_LENGTH:
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                f"Parameter 'title' exceeds maximum length of {_MAX_TITLE_LENGTH}",
                {"parameter": "title", "max_length": _MAX_TITLE_LENGTH},
            )
        )
    if not context or not context.strip():
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                "Parameter 'context' must be a non-empty string",
                {"parameter": "context"},
            )
        )
    if len(context) > _MAX_FIELD_LENGTH:
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                f"Parameter 'context' exceeds maximum length of {_MAX_FIELD_LENGTH}",
                {"parameter": "context", "max_length": _MAX_FIELD_LENGTH},
            )
        )
    if not decision or not decision.strip():
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                "Parameter 'decision' must be a non-empty string",
                {"parameter": "decision"},
            )
        )
    if len(decision) > _MAX_FIELD_LENGTH:
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                f"Parameter 'decision' exceeds maximum length of {_MAX_FIELD_LENGTH}",
                {"parameter": "decision", "max_length": _MAX_FIELD_LENGTH},
            )
        )
    if not consequences or not consequences.strip():
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                "Parameter 'consequences' must be a non-empty string",
                {"parameter": "consequences"},
            )
        )
    if len(consequences) > _MAX_FIELD_LENGTH:
        raise ToolError(
            format_tool_error(
                "INVALID_PARAMETER",
                f"Parameter 'consequences' exceeds maximum length of {_MAX_FIELD_LENGTH}",
                {"parameter": "consequences", "max_length": _MAX_FIELD_LENGTH},
            )
        )


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

        Raises:
            ToolError: If required parameters are empty or ADR directory
                cannot be found.
        """
        _validate_adr_params(title, context, decision, consequences)

        title = title.strip()
        context = context.strip()
        decision = decision.strip()
        consequences = consequences.strip()

        try:
            adr_dir = _discover_adr_dir()
        except FileNotFoundError as exc:
            raise ToolError(
                format_tool_error(
                    "ADR_DIR_NOT_FOUND",
                    "Could not locate docs/adr directory. Ensure the project structure is correct.",
                    {"expected_path": "docs/adr"},
                )
            ) from exc

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
