"""Tests for the persistence configuration module."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from atlas_mcp.persistence.config import DatabaseConfig


class TestDatabaseConfig:
    """Tests for DatabaseConfig dataclass."""

    def test_should_have_sensible_defaults(self) -> None:
        """Validate that default values work for local development."""
        config = DatabaseConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.user == "atlas"
        assert config.password == "atlas_dev"  # noqa: S105
        assert config.database == "atlas_mcp"
        assert config.min_pool_size == 2
        assert config.max_pool_size == 10

    def test_should_generate_correct_dsn(self) -> None:
        """Validate that the dsn property builds the correct URI."""
        config = DatabaseConfig()
        assert config.dsn == "postgresql://atlas:atlas_dev@localhost:5432/atlas_mcp"

    def test_should_generate_dsn_with_custom_values(self) -> None:
        """Validate DSN with non-default values."""
        config = DatabaseConfig(
            host="db.example.com",
            port=5433,
            user="admin",
            password="secret",  # noqa: S106
            database="prod_db",
        )
        assert config.dsn == "postgresql://admin:secret@db.example.com:5433/prod_db"

    def test_should_be_immutable(self) -> None:
        """Validate that DatabaseConfig is frozen (immutable)."""
        config = DatabaseConfig()
        with pytest.raises(AttributeError):
            config.host = "other"  # type: ignore[misc]


class TestDatabaseConfigFromEnv:
    """Tests for DatabaseConfig.from_env() factory."""

    def test_should_use_defaults_when_no_env_vars(self) -> None:
        """Validate fallback to defaults with empty environment."""
        env: dict[str, str] = {}
        with patch.dict(os.environ, env, clear=True):
            config = DatabaseConfig.from_env()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.user == "atlas"
        assert config.database == "atlas_mcp"

    def test_should_read_individual_env_vars(self) -> None:
        """Validate that individual POSTGRES_* vars are read."""
        env = {
            "POSTGRES_HOST": "db.prod.com",
            "POSTGRES_PORT": "5433",
            "POSTGRES_USER": "prod_user",
            "POSTGRES_PASSWORD": "prod_pass",
            "POSTGRES_DB": "prod_db",
            "DB_MIN_POOL_SIZE": "5",
            "DB_MAX_POOL_SIZE": "20",
        }
        with patch.dict(os.environ, env, clear=True):
            config = DatabaseConfig.from_env()
        assert config.host == "db.prod.com"
        assert config.port == 5433
        assert config.user == "prod_user"
        assert config.password == "prod_pass"  # noqa: S105
        assert config.database == "prod_db"
        assert config.min_pool_size == 5
        assert config.max_pool_size == 20

    def test_should_prefer_database_url_over_individual_vars(self) -> None:
        """Validate that DATABASE_URL takes precedence."""
        env = {
            "DATABASE_URL": "postgresql://url_user:url_pass@url_host:5434/url_db",
            "POSTGRES_HOST": "should_be_ignored",
            "POSTGRES_USER": "should_be_ignored",
        }
        with patch.dict(os.environ, env, clear=True):
            config = DatabaseConfig.from_env()
        assert config.host == "url_host"
        assert config.port == 5434
        assert config.user == "url_user"
        assert config.password == "url_pass"  # noqa: S105
        assert config.database == "url_db"

    def test_should_handle_database_url_without_port(self) -> None:
        """Validate that DATABASE_URL without port defaults to 5432."""
        env = {"DATABASE_URL": "postgresql://user:pass@myhost/mydb"}
        with patch.dict(os.environ, env, clear=True):
            config = DatabaseConfig.from_env()
        assert config.host == "myhost"
        assert config.port == 5432

    def test_should_raise_for_invalid_database_url_no_host(self) -> None:
        """Validate that DATABASE_URL without hostname raises ValueError."""
        env = {"DATABASE_URL": "postgresql:///mydb"}
        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="missing hostname"),
        ):
            DatabaseConfig.from_env()

    def test_should_raise_for_invalid_database_url_no_db(self) -> None:
        """Validate that DATABASE_URL without database raises ValueError."""
        env = {"DATABASE_URL": "postgresql://user:pass@host/"}
        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="missing database name"),
        ):
            DatabaseConfig.from_env()

    def test_should_handle_partial_env_vars(self) -> None:
        """Validate that only set variables override defaults."""
        env = {"POSTGRES_HOST": "custom-host"}
        with patch.dict(os.environ, env, clear=True):
            config = DatabaseConfig.from_env()
        assert config.host == "custom-host"
        assert config.port == 5432
        assert config.user == "atlas"
