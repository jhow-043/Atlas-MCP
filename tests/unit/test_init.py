"""Smoke tests for the atlas_mcp package."""

from __future__ import annotations

import atlas_mcp


class TestPackageInit:
    """Tests for package initialization and metadata."""

    def test_should_expose_version(self) -> None:
        """Validate that the package exposes a __version__ attribute."""
        assert hasattr(atlas_mcp, "__version__")
        assert isinstance(atlas_mcp.__version__, str)

    def test_should_have_valid_semver_format(self) -> None:
        """Validate that __version__ follows semantic versioning."""
        parts = atlas_mcp.__version__.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_should_match_expected_version(self) -> None:
        """Validate current version is 0.0.1."""
        assert atlas_mcp.__version__ == "0.0.1"
