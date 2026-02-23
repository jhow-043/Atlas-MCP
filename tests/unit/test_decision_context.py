"""Tests for the DecisionContextProvider and ADR parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from atlas_mcp.context.decision import (
    ADRRecord,
    DecisionContextProvider,
    parse_adr,
)

# Use the real ADR directory for testing
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ADR_DIR = _PROJECT_ROOT / "docs" / "adr"

_SAMPLE_ADR = """\
# ADR-042: Use Widget Framework

**Data:** 2026-03-01
**Status:** APPROVED
**Autor:** dev-user
**Tags:** framework, frontend

---

### Contexto

We need a widget framework for the project.

### Decisão

Use WidgetX as the main framework.

### Alternativas Consideradas

| Alternativa | Prós | Contras |
|-------------|------|---------|
| WidgetX | Fast | New |
| WidgetY | Stable | Slow |

### Consequências

Positive: faster development.
Negative: learning curve.
"""


class TestADRRecord:
    """Tests for the ADRRecord dataclass."""

    def test_should_store_fields(self) -> None:
        """Validate that all fields are stored correctly."""
        record = ADRRecord(id=1, title="Test Decision", status="APPROVED")
        assert record.id == 1
        assert record.title == "Test Decision"
        assert record.status == "APPROVED"

    def test_should_be_frozen(self) -> None:
        """Validate immutability."""
        record = ADRRecord(id=1, title="Test")
        with pytest.raises(AttributeError):
            record.id = 2  # type: ignore[misc]

    def test_to_dict_should_include_all_fields(self) -> None:
        """Validate that to_dict returns all fields."""
        record = ADRRecord(
            id=1,
            title="Test",
            date="2026-01-01",
            status="APPROVED",
            author="dev",
            tags=["tag1"],
            sections={"Contexto": "some context"},
            file_path="/path/to/file.md",
        )
        d = record.to_dict()
        assert d["id"] == 1
        assert d["title"] == "Test"
        assert d["sections"]["Contexto"] == "some context"
        assert d["file_path"] == "/path/to/file.md"

    def test_to_summary_should_exclude_sections(self) -> None:
        """Validate that to_summary omits sections and file_path."""
        record = ADRRecord(
            id=1,
            title="Test",
            sections={"Contexto": "data"},
            file_path="/path",
        )
        s = record.to_summary()
        assert "sections" not in s
        assert "file_path" not in s
        assert s["id"] == 1

    def test_default_values(self) -> None:
        """Validate default values for optional fields."""
        record = ADRRecord(id=1, title="Test")
        assert record.date == ""
        assert record.status == "PROPOSED"
        assert record.author == ""
        assert record.tags == []
        assert record.sections == {}


class TestParseADR:
    """Tests for the parse_adr function."""

    def test_should_parse_title_and_id(self) -> None:
        """Validate correct title and ID extraction."""
        record = parse_adr(_SAMPLE_ADR)
        assert record.id == 42
        assert record.title == "Use Widget Framework"

    def test_should_parse_metadata(self) -> None:
        """Validate metadata extraction."""
        record = parse_adr(_SAMPLE_ADR)
        assert record.date == "2026-03-01"
        assert record.status == "APPROVED"
        assert record.author == "dev-user"

    def test_should_parse_tags(self) -> None:
        """Validate tag parsing from comma-separated list."""
        record = parse_adr(_SAMPLE_ADR)
        assert record.tags == ["framework", "frontend"]

    def test_should_parse_sections(self) -> None:
        """Validate section extraction."""
        record = parse_adr(_SAMPLE_ADR)
        assert "Contexto" in record.sections
        assert "Decisão" in record.sections
        assert "Consequências" in record.sections

    def test_should_include_section_content(self) -> None:
        """Validate that section bodies contain expected text."""
        record = parse_adr(_SAMPLE_ADR)
        assert "widget framework" in record.sections["Contexto"]
        assert "WidgetX" in record.sections["Decisão"]

    def test_should_store_file_path(self) -> None:
        """Validate that file_path is stored."""
        record = parse_adr(_SAMPLE_ADR, file_path="/docs/adr/test.md")
        assert record.file_path == "/docs/adr/test.md"

    def test_should_raise_on_missing_title(self) -> None:
        """Validate ValueError when title is not found."""
        with pytest.raises(ValueError, match="Could not parse ADR title"):
            parse_adr("# Some random heading\n\nNo ADR title here.")

    def test_should_handle_english_metadata_keys(self) -> None:
        """Validate parsing with English metadata keys."""
        content = """\
# ADR-001: English ADR

**Date:** 2026-01-01
**Status:** PROPOSED
**Author:** user
**Tags:** test
"""
        record = parse_adr(content)
        assert record.date == "2026-01-01"
        assert record.author == "user"

    def test_should_handle_empty_tags(self) -> None:
        """Validate parsing with no tags."""
        content = """\
# ADR-005: No Tags

**Status:** PROPOSED
"""
        record = parse_adr(content)
        assert record.tags == []


class TestDecisionContextProvider:
    """Tests for the DecisionContextProvider class."""

    @pytest.fixture()
    def provider(self) -> DecisionContextProvider:
        """Return a provider using the real ADR directory."""
        return DecisionContextProvider(adr_directory=_ADR_DIR)

    def test_should_discover_adr_directory(self) -> None:
        """Validate auto-discovery of ADR directory."""
        provider = DecisionContextProvider()
        assert provider._adr_dir.exists()
        assert provider._adr_dir.name == "adr"

    def test_should_list_adrs(self, provider: DecisionContextProvider) -> None:
        """Validate that list_adrs returns real ADRs."""
        adrs = provider.list_adrs()
        assert len(adrs) >= 2  # At least ADR-001 and ADR-002
        assert all("id" in a for a in adrs)
        assert all("title" in a for a in adrs)

    def test_should_list_in_order(self, provider: DecisionContextProvider) -> None:
        """Validate that ADRs are returned in order by ID."""
        adrs = provider.list_adrs()
        ids = [a["id"] for a in adrs]
        assert ids == sorted(ids)

    def test_should_get_adr_by_id(self, provider: DecisionContextProvider) -> None:
        """Validate retrieval of ADR-001."""
        adr = provider.get_adr(1)
        assert adr is not None
        assert adr["id"] == 1
        assert "title" in adr
        assert "sections" in adr

    def test_should_return_none_for_missing_adr(self, provider: DecisionContextProvider) -> None:
        """Validate None for non-existent ADR."""
        result = provider.get_adr(999)
        assert result is None

    def test_should_skip_template(self, provider: DecisionContextProvider) -> None:
        """Validate that ADR-000-template.md is skipped."""
        adrs = provider.list_adrs()
        # The point is that the template is not in the list
        assert all(a["title"] != "ADR Template" for a in adrs)

    def test_should_cache_results(self, provider: DecisionContextProvider) -> None:
        """Validate that repeated calls use cache."""
        provider.list_adrs()
        cache_ref = provider._cache
        provider.list_adrs()
        assert provider._cache is cache_ref

    def test_should_invalidate_cache(self, provider: DecisionContextProvider) -> None:
        """Validate cache invalidation."""
        provider.list_adrs()
        assert provider._cache is not None
        provider.invalidate_cache()
        assert provider._cache is None

    def test_should_handle_empty_directory(self, tmp_path: Path) -> None:
        """Validate behavior with empty ADR directory."""
        provider = DecisionContextProvider(adr_directory=tmp_path)
        adrs = provider.list_adrs()
        assert adrs == []

    def test_should_handle_nonexistent_directory(self, tmp_path: Path) -> None:
        """Validate behavior when directory does not exist."""
        missing = tmp_path / "nonexistent"
        provider = DecisionContextProvider(adr_directory=missing)
        adrs = provider.list_adrs()
        assert adrs == []

    def test_should_parse_real_adr_001(self, provider: DecisionContextProvider) -> None:
        """Validate that real ADR-001 has expected fields."""
        adr = provider.get_adr(1)
        assert adr is not None
        assert "Python" in adr["title"] or "python" in adr["title"].lower()
        assert adr["status"] == "APPROVED"

    def test_should_parse_real_adr_002(self, provider: DecisionContextProvider) -> None:
        """Validate that real ADR-002 has expected fields."""
        adr = provider.get_adr(2)
        assert adr is not None
        assert adr["status"] == "APPROVED"
