"""Tests for the logging setup module."""

from __future__ import annotations

import logging
import sys
from io import StringIO

import pytest

from atlas_mcp.config.logging import setup_logging


class TestSetupLogging:
    """Tests for the setup_logging function."""

    def setup_method(self) -> None:
        """Reset root logger before each test."""
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        root.setLevel(logging.WARNING)  # default

    def test_should_configure_text_format(self) -> None:
        """Validate that text format creates a human-readable formatter."""
        setup_logging("INFO", "text")

        root = logging.getLogger()
        assert root.level == logging.INFO
        assert len(root.handlers) == 1

        handler = root.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stderr

        fmt = handler.formatter
        assert fmt is not None
        assert "%(levelname)" in fmt._fmt

    def test_should_configure_json_format(self) -> None:
        """Validate that json format creates a structured formatter."""
        setup_logging("DEBUG", "json")

        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1

        fmt = root.handlers[0].formatter
        assert fmt is not None
        assert '"level"' in fmt._fmt

    def test_should_output_to_stderr(self) -> None:
        """Validate that log output is directed to stderr."""
        setup_logging("INFO", "text")

        handler = logging.getLogger().handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stderr

    def test_should_reset_existing_handlers(self) -> None:
        """Validate that prior handlers are removed on reconfiguration."""
        root = logging.getLogger()
        extra_a = logging.StreamHandler(StringIO())
        extra_b = logging.StreamHandler(StringIO())
        root.addHandler(extra_a)
        root.addHandler(extra_b)

        setup_logging("INFO", "text")

        # Only the handler created by setup_logging should remain
        # (pytest may add its own LogCaptureHandler, but our extras must be gone)
        assert extra_a not in root.handlers
        assert extra_b not in root.handlers
        stderr_handlers = [
            h
            for h in root.handlers
            if isinstance(h, logging.StreamHandler) and h.stream is sys.stderr
        ]
        assert len(stderr_handlers) == 1

    def test_should_reject_invalid_format(self) -> None:
        """Validate ValueError for unsupported format."""
        with pytest.raises(ValueError, match="Invalid log format"):
            setup_logging("INFO", "yaml")

    def test_should_reject_invalid_level(self) -> None:
        """Validate ValueError for unsupported log level."""
        with pytest.raises(ValueError, match="Invalid log level"):
            setup_logging("NONEXISTENT", "text")

    @pytest.mark.parametrize(
        ("level_name", "expected"),
        [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ],
    )
    def test_should_set_correct_numeric_level(self, level_name: str, expected: int) -> None:
        """Validate that each named level maps to the right numeric constant."""
        setup_logging(level_name, "text")

        assert logging.getLogger().level == expected

    def test_should_accept_case_insensitive_format(self) -> None:
        """Validate that format name is case-insensitive."""
        setup_logging("INFO", "JSON")
        fmt = logging.getLogger().handlers[0].formatter
        assert fmt is not None
        assert '"level"' in fmt._fmt

    def test_should_produce_log_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Validate that a logged message appears on stderr."""
        setup_logging("INFO", "text")
        test_logger = logging.getLogger("test.output")
        test_logger.info("hello from test")

        captured = capsys.readouterr()
        assert "hello from test" in captured.err
        assert captured.out == ""
