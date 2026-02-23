"""Tests for the ApplicationBootstrap module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from atlas_mcp.bootstrap import ApplicationBootstrap
from atlas_mcp.config.settings import Settings
from atlas_mcp.persistence.config import DatabaseConfig


def _make_settings(**overrides: Any) -> Settings:
    """Create a Settings instance with sensible test defaults."""
    defaults: dict[str, Any] = {
        "db": DatabaseConfig(),
        "embedding_provider": "sentence-transformers",
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_dimension": 384,
        "openai_api_key": None,
        "transport": "stdio",
        "log_level": "INFO",
        "log_format": "text",
    }
    defaults.update(overrides)
    return Settings(**defaults)


class TestBootstrapInit:
    """Tests for ApplicationBootstrap initialization."""

    def test_should_start_with_no_components(self) -> None:
        """Validate that a fresh bootstrap has no active components."""
        bootstrap = ApplicationBootstrap()

        assert bootstrap.db is None
        assert bootstrap._embedder is None
        assert bootstrap._store is None
        assert bootstrap._indexing is None
        assert bootstrap._governance is None
        assert bootstrap._audit is None


class TestBootstrapStartup:
    """Tests for the startup sequence."""

    @pytest.mark.asyncio
    @patch("atlas_mcp.bootstrap.ApplicationBootstrap._init_governance", new_callable=AsyncMock)
    @patch("atlas_mcp.bootstrap.ApplicationBootstrap._configure_tools")
    @patch("atlas_mcp.bootstrap.ApplicationBootstrap._init_vectorization", new_callable=AsyncMock)
    @patch("atlas_mcp.bootstrap.ApplicationBootstrap._init_database", new_callable=AsyncMock)
    async def test_should_call_all_init_steps_in_order(
        self,
        mock_db: AsyncMock,
        mock_vec: AsyncMock,
        mock_tools: MagicMock,
        mock_gov: AsyncMock,
    ) -> None:
        """Validate that startup calls all init steps in the correct order."""
        bootstrap = ApplicationBootstrap()
        settings = _make_settings()

        await bootstrap.startup(settings)

        mock_db.assert_awaited_once_with(settings)
        mock_vec.assert_awaited_once_with(settings)
        mock_tools.assert_called_once()
        mock_gov.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("atlas_mcp.bootstrap.ApplicationBootstrap._init_database", new_callable=AsyncMock)
    async def test_should_enter_degraded_mode_on_db_failure(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Validate that a database failure does not crash the server."""
        mock_db.side_effect = ConnectionRefusedError("Connection refused")

        bootstrap = ApplicationBootstrap()
        settings = _make_settings()

        # Should NOT raise — degraded mode
        await bootstrap.startup(settings)

        # Components should remain None
        assert bootstrap._embedder is None
        assert bootstrap._store is None

    @pytest.mark.asyncio
    @patch("atlas_mcp.bootstrap.ApplicationBootstrap._init_governance", new_callable=AsyncMock)
    @patch("atlas_mcp.bootstrap.ApplicationBootstrap._configure_tools")
    @patch("atlas_mcp.bootstrap.ApplicationBootstrap._init_vectorization", new_callable=AsyncMock)
    @patch("atlas_mcp.bootstrap.ApplicationBootstrap._init_database", new_callable=AsyncMock)
    async def test_should_enter_degraded_mode_on_vectorization_failure(
        self,
        mock_db: AsyncMock,
        mock_vec: AsyncMock,
        mock_tools: MagicMock,
        mock_gov: AsyncMock,
    ) -> None:
        """Validate that a vectorization failure does not crash the server."""
        mock_vec.side_effect = RuntimeError("Model download failed")

        bootstrap = ApplicationBootstrap()
        settings = _make_settings()

        await bootstrap.startup(settings)

        mock_db.assert_awaited_once()
        mock_tools.assert_not_called()
        mock_gov.assert_not_called()


class TestBootstrapShutdown:
    """Tests for the shutdown sequence."""

    @pytest.mark.asyncio
    async def test_should_shutdown_cleanly_without_init(self) -> None:
        """Validate that shutdown() works even if startup was never called."""
        bootstrap = ApplicationBootstrap()
        await bootstrap.shutdown()  # should not raise

        assert bootstrap.db is None

    @pytest.mark.asyncio
    async def test_should_close_db_pool_on_shutdown(self) -> None:
        """Validate that shutdown closes the database pool."""
        bootstrap = ApplicationBootstrap()
        mock_db = AsyncMock()
        bootstrap._db = mock_db

        await bootstrap.shutdown()

        mock_db.close.assert_awaited_once()
        assert bootstrap._db is None

    @pytest.mark.asyncio
    async def test_should_null_all_refs_on_shutdown(self) -> None:
        """Validate that all component references are cleared."""
        bootstrap = ApplicationBootstrap()
        bootstrap._db = AsyncMock()
        bootstrap._embedder = MagicMock()
        bootstrap._store = MagicMock()
        bootstrap._indexing = MagicMock()
        bootstrap._governance = MagicMock()
        bootstrap._audit = MagicMock()

        await bootstrap.shutdown()

        assert bootstrap._db is None
        assert bootstrap._embedder is None
        assert bootstrap._store is None
        assert bootstrap._indexing is None
        assert bootstrap._governance is None
        assert bootstrap._audit is None

    @pytest.mark.asyncio
    async def test_should_handle_db_close_error_gracefully(self) -> None:
        """Validate that an error during pool close does not crash shutdown."""
        bootstrap = ApplicationBootstrap()
        mock_db = AsyncMock()
        mock_db.close.side_effect = RuntimeError("Pool close error")
        bootstrap._db = mock_db

        await bootstrap.shutdown()  # should not raise

        assert bootstrap._db is None

    @pytest.mark.asyncio
    async def test_should_be_idempotent(self) -> None:
        """Validate that calling shutdown() twice is safe."""
        bootstrap = ApplicationBootstrap()
        bootstrap._db = AsyncMock()

        await bootstrap.shutdown()
        await bootstrap.shutdown()

        assert bootstrap._db is None
