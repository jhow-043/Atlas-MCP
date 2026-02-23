"""Smoke tests for the atlas_mcp package."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import atlas_mcp
from atlas_mcp.__main__ import main


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


class TestMain:
    """Tests for the __main__ entry point."""

    @patch("atlas_mcp.__main__._async_main")
    @patch("atlas_mcp.__main__.setup_logging")
    @patch("atlas_mcp.__main__.Settings.from_env")
    def test_should_run_main_without_error(
        self,
        mock_settings: MagicMock,
        mock_logging: MagicMock,
        mock_async_main: MagicMock,
    ) -> None:
        """Validate that main() executes without raising exceptions."""
        mock_settings.return_value = MagicMock(
            log_level="INFO", log_format="text", transport="stdio"
        )
        main(argv=[])

    @patch("atlas_mcp.__main__._async_main")
    @patch("atlas_mcp.__main__.setup_logging")
    @patch("atlas_mcp.__main__.Settings.from_env")
    def test_should_log_startup_message(
        self,
        mock_settings: MagicMock,
        mock_logging: MagicMock,
        mock_async_main: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Validate that main() logs a startup message with version."""
        import logging

        mock_settings.return_value = MagicMock(
            log_level="INFO", log_format="text", transport="stdio"
        )
        with caplog.at_level(logging.INFO):
            main(argv=[])
        assert "Atlas MCP Server" in caplog.text
        assert atlas_mcp.__version__ in caplog.text


class TestSubpackageImports:
    """Tests for convenience imports from sub-packages."""

    def test_should_import_protocol_handler(self) -> None:
        """Validate that ProtocolHandler is importable from atlas_mcp.protocol."""
        from atlas_mcp.protocol import ProtocolHandler

        assert ProtocolHandler is not None

    def test_should_import_resource_registry(self) -> None:
        """Validate that ResourceRegistry is importable from atlas_mcp.resources."""
        from atlas_mcp.resources import ResourceRegistry

        assert ResourceRegistry is not None

    def test_should_import_tool_executor(self) -> None:
        """Validate that ToolExecutor is importable from atlas_mcp.tools."""
        from atlas_mcp.tools import ToolExecutor

        assert ToolExecutor is not None
