"""Tests for the Settings module."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from atlas_mcp.config.settings import Settings, _validate_choice
from atlas_mcp.persistence.config import DatabaseConfig


class TestValidateChoice:
    """Tests for the _validate_choice helper."""

    def test_should_accept_valid_value(self) -> None:
        """Validate that a value in the allowed set passes without error."""
        _validate_choice("TEST_VAR", "a", frozenset({"a", "b"}))

    def test_should_reject_invalid_value(self) -> None:
        """Validate that a value outside the allowed set raises ValueError."""
        with pytest.raises(ValueError, match="Invalid TEST_VAR='c'"):
            _validate_choice("TEST_VAR", "c", frozenset({"a", "b"}))


class TestSettingsDefaults:
    """Tests for Settings default values."""

    def test_should_have_correct_defaults(self) -> None:
        """Validate default attribute values on a bare Settings instance."""
        db = DatabaseConfig()
        s = Settings(db=db)

        assert s.embedding_provider == "openai"
        assert s.embedding_model == "text-embedding-3-small"
        assert s.embedding_dimension == 1536
        assert s.openai_api_key is None
        assert s.transport == "stdio"
        assert s.sse_host == "0.0.0.0"  # noqa: S104
        assert s.sse_port == 8000
        assert s.log_level == "INFO"
        assert s.log_format == "text"

    def test_should_be_frozen(self) -> None:
        """Validate that Settings is immutable."""
        s = Settings(db=DatabaseConfig())
        with pytest.raises(AttributeError):
            s.transport = "sse"  # type: ignore[misc]


class TestSettingsFromEnv:
    """Tests for Settings.from_env()."""

    @patch("atlas_mcp.config.settings.load_dotenv")
    @patch.dict(os.environ, {}, clear=True)
    def test_should_use_defaults_when_no_env_set(self, _mock_dotenv: object) -> None:
        """Validate that from_env() returns defaults when env is empty."""
        s = Settings.from_env()

        assert s.embedding_provider == "openai"
        assert s.embedding_model == "text-embedding-3-small"
        assert s.embedding_dimension == 1536
        assert s.transport == "stdio"
        assert s.log_level == "INFO"
        assert s.log_format == "text"

    @patch.dict(
        os.environ,
        {
            "EMBEDDING_PROVIDER": "sentence-transformers",
        },
        clear=True,
    )
    def test_should_use_sentence_transformer_defaults(self) -> None:
        """Validate provider-specific defaults for sentence-transformers."""
        s = Settings.from_env()

        assert s.embedding_provider == "sentence-transformers"
        assert s.embedding_model == "all-MiniLM-L6-v2"
        assert s.embedding_dimension == 384

    @patch.dict(
        os.environ,
        {
            "EMBEDDING_PROVIDER": "openai",
            "EMBEDDING_MODEL": "text-embedding-ada-002",
            "EMBEDDING_DIMENSION": "768",
            "OPENAI_API_KEY": "sk-test-key",
            "ATLAS_TRANSPORT": "sse",
            "ATLAS_SSE_HOST": "127.0.0.1",
            "ATLAS_SSE_PORT": "9000",
            "ATLAS_LOG_LEVEL": "debug",
            "ATLAS_LOG_FORMAT": "json",
        },
        clear=True,
    )
    def test_should_read_all_custom_env_vars(self) -> None:
        """Validate that from_env() reads every supported variable."""
        s = Settings.from_env()

        assert s.embedding_provider == "openai"
        assert s.embedding_model == "text-embedding-ada-002"
        assert s.embedding_dimension == 768
        assert s.openai_api_key == "sk-test-key"
        assert s.transport == "sse"
        assert s.sse_host == "127.0.0.1"
        assert s.sse_port == 9000
        assert s.log_level == "DEBUG"
        assert s.log_format == "json"

    @patch.dict(os.environ, {"EMBEDDING_PROVIDER": "invalid"}, clear=True)
    def test_should_reject_invalid_provider(self) -> None:
        """Validate ValueError for unsupported embedding provider."""
        with pytest.raises(ValueError, match="EMBEDDING_PROVIDER"):
            Settings.from_env()

    @patch.dict(os.environ, {"ATLAS_TRANSPORT": "grpc"}, clear=True)
    def test_should_reject_invalid_transport(self) -> None:
        """Validate ValueError for unsupported transport."""
        with pytest.raises(ValueError, match="ATLAS_TRANSPORT"):
            Settings.from_env()

    @patch.dict(os.environ, {"ATLAS_LOG_FORMAT": "yaml"}, clear=True)
    def test_should_reject_invalid_log_format(self) -> None:
        """Validate ValueError for unsupported log format."""
        with pytest.raises(ValueError, match="ATLAS_LOG_FORMAT"):
            Settings.from_env()

    @patch.dict(
        os.environ,
        {"EMBEDDING_PROVIDER": "OPENAI", "ATLAS_TRANSPORT": "SSE"},
        clear=True,
    )
    def test_should_normalize_values_to_lowercase(self) -> None:
        """Validate that provider and transport are lowercased."""
        s = Settings.from_env()

        assert s.embedding_provider == "openai"
        assert s.transport == "sse"

    @patch.dict(
        os.environ,
        {"ATLAS_LOG_LEVEL": "warning"},
        clear=True,
    )
    def test_should_uppercase_log_level(self) -> None:
        """Validate that the log level is uppercased."""
        s = Settings.from_env()

        assert s.log_level == "WARNING"

    @patch.dict(os.environ, {}, clear=True)
    def test_should_compose_database_config(self) -> None:
        """Validate that from_env() produces a valid DatabaseConfig."""
        s = Settings.from_env()

        assert isinstance(s.db, DatabaseConfig)
        assert s.db.host == "localhost"
