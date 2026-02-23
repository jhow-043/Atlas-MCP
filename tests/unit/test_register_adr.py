"""Tests for the register_adr tool module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from atlas_mcp.tools.register_adr import (
    _discover_adr_dir,
    _next_adr_id,
    _render_adr_markdown,
    _slugify,
    register_register_adr,
)

# ---------------------------------------------------------------------------
# _slugify tests
# ---------------------------------------------------------------------------


class TestSlugify:
    """Tests for the _slugify helper."""

    def test_should_lowercase(self) -> None:
        assert _slugify("Hello World") == "hello-world"

    def test_should_replace_spaces(self) -> None:
        assert _slugify("use python sdk") == "use-python-sdk"

    def test_should_remove_special_chars(self) -> None:
        assert _slugify("use asyncpg (driver)") == "use-asyncpg-driver"

    def test_should_handle_underscores(self) -> None:
        assert _slugify("some_thing") == "some-thing"

    def test_should_strip_edges(self) -> None:
        assert _slugify("  hello  ") == "hello"

    def test_should_collapse_dashes(self) -> None:
        assert _slugify("a - b") == "a-b"


# ---------------------------------------------------------------------------
# _discover_adr_dir tests
# ---------------------------------------------------------------------------


class TestDiscoverAdrDir:
    """Tests for _discover_adr_dir."""

    def test_should_find_docs_adr_directory(self) -> None:
        adr_dir = _discover_adr_dir()
        assert adr_dir.is_dir()
        assert adr_dir.name == "adr"

    def test_should_contain_existing_adrs(self) -> None:
        adr_dir = _discover_adr_dir()
        files = list(adr_dir.glob("ADR-*.md"))
        assert len(files) >= 1


# ---------------------------------------------------------------------------
# _next_adr_id tests
# ---------------------------------------------------------------------------


class TestNextAdrId:
    """Tests for _next_adr_id."""

    def test_should_return_next_sequential_id(self, tmp_path: Path) -> None:
        (tmp_path / "ADR-001-first.md").touch()
        (tmp_path / "ADR-002-second.md").touch()
        assert _next_adr_id(tmp_path) == 3

    def test_should_return_1_for_empty_dir(self, tmp_path: Path) -> None:
        assert _next_adr_id(tmp_path) == 1

    def test_should_skip_template_file(self, tmp_path: Path) -> None:
        (tmp_path / "ADR-000-template.md").touch()
        (tmp_path / "ADR-003-something.md").touch()
        assert _next_adr_id(tmp_path) == 4

    def test_should_handle_gaps_in_ids(self, tmp_path: Path) -> None:
        (tmp_path / "ADR-001-first.md").touch()
        (tmp_path / "ADR-005-fifth.md").touch()
        assert _next_adr_id(tmp_path) == 6


# ---------------------------------------------------------------------------
# _render_adr_markdown tests
# ---------------------------------------------------------------------------


class TestRenderAdrMarkdown:
    """Tests for _render_adr_markdown."""

    def test_should_include_title_with_id(self) -> None:
        md = _render_adr_markdown(
            adr_id=4,
            title="Use Docker",
            context="Need containers",
            decision="Use Docker",
            consequences="Must install Docker",
        )
        assert "# ADR-004: Use Docker" in md

    def test_should_include_status_proposed(self) -> None:
        md = _render_adr_markdown(
            adr_id=1,
            title="Test",
            context="C",
            decision="D",
            consequences="E",
        )
        assert "**Status:** PROPOSED" in md

    def test_should_include_sections(self) -> None:
        md = _render_adr_markdown(
            adr_id=1,
            title="Test",
            context="The context",
            decision="The decision",
            consequences="The consequences",
        )
        assert "### Contexto" in md
        assert "The context" in md
        assert "### Decisão" in md
        assert "The decision" in md
        assert "### Consequências" in md
        assert "The consequences" in md

    def test_should_include_alternatives_when_provided(self) -> None:
        md = _render_adr_markdown(
            adr_id=1,
            title="Test",
            context="C",
            decision="D",
            consequences="E",
            alternatives_considered="Alt A vs Alt B",
        )
        assert "### Alternativas Consideradas" in md
        assert "Alt A vs Alt B" in md

    def test_should_omit_alternatives_when_empty(self) -> None:
        md = _render_adr_markdown(
            adr_id=1,
            title="Test",
            context="C",
            decision="D",
            consequences="E",
        )
        assert "### Alternativas Consideradas" not in md

    def test_should_include_tags_when_provided(self) -> None:
        md = _render_adr_markdown(
            adr_id=1,
            title="Test",
            context="C",
            decision="D",
            consequences="E",
            tags="python, mcp",
        )
        assert "**Tags:** python, mcp" in md

    def test_should_include_author(self) -> None:
        md = _render_adr_markdown(
            adr_id=1,
            title="Test",
            context="C",
            decision="D",
            consequences="E",
            author="test-user",
        )
        assert "**Autor:** test-user" in md


# ---------------------------------------------------------------------------
# register_adr tool tests
# ---------------------------------------------------------------------------


class TestRegisterAdrTool:
    """Tests for the register_adr tool function."""

    @pytest.fixture()
    def server(self) -> MagicMock:
        """Create a mock FastMCP server that captures the tool function."""
        mock_server = MagicMock()
        # Capture the decorated function
        mock_server.tool.return_value = lambda fn: fn
        return mock_server

    @pytest.fixture()
    def tool_fn(self, server: MagicMock) -> MagicMock:
        """Register the tool and return the captured function."""
        register_register_adr(server)
        # The decorated function is the one passed to @server.tool()
        return server.tool.return_value

    def test_should_register_tool_on_server(self, server: MagicMock) -> None:
        register_register_adr(server)
        server.tool.assert_called_once()
        call_kwargs = server.tool.call_args.kwargs
        assert call_kwargs["name"] == "register_adr"

    @patch("atlas_mcp.tools.register_adr._discover_adr_dir")
    def test_should_create_adr_file(
        self,
        mock_discover: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = tmp_path

        # We need to actually get to the inner function
        captured_fn = None

        def capture_tool(**kwargs: object) -> object:
            def decorator(fn: object) -> object:
                nonlocal captured_fn
                captured_fn = fn
                return fn

            return decorator

        mock_server = MagicMock()
        mock_server.tool = capture_tool
        register_register_adr(mock_server)

        assert captured_fn is not None
        result = captured_fn(
            title="Use asyncpg",
            context="Need async DB driver",
            decision="Use asyncpg",
            consequences="Requires asyncpg dep",
        )

        assert result["status"] == "created"
        assert result["adr_id"] == 1
        files = list(tmp_path.glob("ADR-*.md"))
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert "# ADR-001: Use asyncpg" in content

    @patch("atlas_mcp.tools.register_adr._discover_adr_dir")
    def test_should_increment_id(
        self,
        mock_discover: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = tmp_path
        (tmp_path / "ADR-001-first.md").touch()
        (tmp_path / "ADR-002-second.md").touch()

        captured_fn = None

        def capture_tool(**kwargs: object) -> object:
            def decorator(fn: object) -> object:
                nonlocal captured_fn
                captured_fn = fn
                return fn

            return decorator

        mock_server = MagicMock()
        mock_server.tool = capture_tool
        register_register_adr(mock_server)

        assert captured_fn is not None
        result = captured_fn(
            title="Third ADR",
            context="C",
            decision="D",
            consequences="E",
        )

        assert result["adr_id"] == 3

    @patch("atlas_mcp.tools.register_adr._discover_adr_dir")
    def test_should_reject_empty_title(
        self,
        mock_discover: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = tmp_path

        captured_fn = None

        def capture_tool(**kwargs: object) -> object:
            def decorator(fn: object) -> object:
                nonlocal captured_fn
                captured_fn = fn
                return fn

            return decorator

        mock_server = MagicMock()
        mock_server.tool = capture_tool
        register_register_adr(mock_server)

        assert captured_fn is not None
        with pytest.raises(ToolError):
            captured_fn(title="", context="C", decision="D", consequences="E")

    @patch("atlas_mcp.tools.register_adr._discover_adr_dir")
    def test_should_reject_empty_context(
        self,
        mock_discover: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = tmp_path

        captured_fn = None

        def capture_tool(**kwargs: object) -> object:
            def decorator(fn: object) -> object:
                nonlocal captured_fn
                captured_fn = fn
                return fn

            return decorator

        mock_server = MagicMock()
        mock_server.tool = capture_tool
        register_register_adr(mock_server)

        assert captured_fn is not None
        with pytest.raises(ToolError):
            captured_fn(title="T", context="", decision="D", consequences="E")

    @patch("atlas_mcp.tools.register_adr._discover_adr_dir")
    def test_should_reject_empty_decision(
        self,
        mock_discover: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = tmp_path

        captured_fn = None

        def capture_tool(**kwargs: object) -> object:
            def decorator(fn: object) -> object:
                nonlocal captured_fn
                captured_fn = fn
                return fn

            return decorator

        mock_server = MagicMock()
        mock_server.tool = capture_tool
        register_register_adr(mock_server)

        assert captured_fn is not None
        with pytest.raises(ToolError):
            captured_fn(title="T", context="C", decision="", consequences="E")

    @patch("atlas_mcp.tools.register_adr._discover_adr_dir")
    def test_should_reject_empty_consequences(
        self,
        mock_discover: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = tmp_path

        captured_fn = None

        def capture_tool(**kwargs: object) -> object:
            def decorator(fn: object) -> object:
                nonlocal captured_fn
                captured_fn = fn
                return fn

            return decorator

        mock_server = MagicMock()
        mock_server.tool = capture_tool
        register_register_adr(mock_server)

        assert captured_fn is not None
        with pytest.raises(ToolError):
            captured_fn(title="T", context="C", decision="D", consequences="")

    @patch("atlas_mcp.tools.register_adr._discover_adr_dir")
    def test_should_include_tags_in_result(
        self,
        mock_discover: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = tmp_path

        captured_fn = None

        def capture_tool(**kwargs: object) -> object:
            def decorator(fn: object) -> object:
                nonlocal captured_fn
                captured_fn = fn
                return fn

            return decorator

        mock_server = MagicMock()
        mock_server.tool = capture_tool
        register_register_adr(mock_server)

        assert captured_fn is not None
        result = captured_fn(
            title="Test",
            context="C",
            decision="D",
            consequences="E",
            tags="python, mcp, sdk",
        )

        assert result["tags"] == ["python", "mcp", "sdk"]

    @patch(
        "atlas_mcp.tools.register_adr._discover_adr_dir",
        side_effect=FileNotFoundError("Not found"),
    )
    def test_should_handle_missing_adr_dir(
        self,
        mock_discover: MagicMock,
    ) -> None:
        captured_fn = None

        def capture_tool(**kwargs: object) -> object:
            def decorator(fn: object) -> object:
                nonlocal captured_fn
                captured_fn = fn
                return fn

            return decorator

        mock_server = MagicMock()
        mock_server.tool = capture_tool
        register_register_adr(mock_server)

        assert captured_fn is not None
        with pytest.raises(ToolError, match="docs/adr"):
            captured_fn(title="T", context="C", decision="D", consequences="E")
