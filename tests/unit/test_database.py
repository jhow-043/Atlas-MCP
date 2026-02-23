"""Tests for the DatabaseManager module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from atlas_mcp.persistence.config import DatabaseConfig
from atlas_mcp.persistence.database import DatabaseManager


@pytest.fixture
def db_config() -> DatabaseConfig:
    """Return a default DatabaseConfig for testing."""
    return DatabaseConfig()


@pytest.fixture
def db_manager(db_config: DatabaseConfig) -> DatabaseManager:
    """Return a DatabaseManager with default config."""
    return DatabaseManager(db_config)


class TestDatabaseManagerInit:
    """Tests for DatabaseManager initialization."""

    def test_should_store_config(self, db_config: DatabaseConfig) -> None:
        """Validate that config is stored on the instance."""
        manager = DatabaseManager(db_config)
        assert manager.config is db_config

    def test_should_start_with_no_pool(self, db_manager: DatabaseManager) -> None:
        """Validate that pool is None before initialization."""
        assert db_manager._pool is None


class TestDatabaseManagerPool:
    """Tests for the pool property."""

    def test_should_raise_if_not_initialized(self, db_manager: DatabaseManager) -> None:
        """Validate that accessing pool before init raises RuntimeError."""
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = db_manager.pool

    def test_should_return_pool_when_initialized(self, db_manager: DatabaseManager) -> None:
        """Validate that pool returns the set pool object."""
        mock_pool = MagicMock()
        db_manager._pool = mock_pool
        assert db_manager.pool is mock_pool


class TestDatabaseManagerInitialize:
    """Tests for the initialize method."""

    @patch("atlas_mcp.persistence.database.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_should_create_pool(
        self, mock_create_pool: AsyncMock, db_manager: DatabaseManager
    ) -> None:
        """Validate that initialize creates an asyncpg pool with correct params."""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        await db_manager.initialize()

        mock_create_pool.assert_called_once_with(
            dsn=db_manager.config.dsn,
            min_size=db_manager.config.min_pool_size,
            max_size=db_manager.config.max_pool_size,
        )
        assert db_manager._pool is mock_pool

    @patch("atlas_mcp.persistence.database.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_should_skip_if_already_initialized(
        self, mock_create_pool: AsyncMock, db_manager: DatabaseManager
    ) -> None:
        """Validate that re-calling initialize does not create a second pool."""
        db_manager._pool = MagicMock()

        await db_manager.initialize()

        mock_create_pool.assert_not_called()


class TestDatabaseManagerClose:
    """Tests for the close method."""

    async def test_should_close_pool(self, db_manager: DatabaseManager) -> None:
        """Validate that close calls pool.close() and sets pool to None."""
        mock_pool = AsyncMock()
        db_manager._pool = mock_pool

        await db_manager.close()

        mock_pool.close.assert_called_once()
        assert db_manager._pool is None

    async def test_should_noop_if_no_pool(self, db_manager: DatabaseManager) -> None:
        """Validate that close does nothing if pool is already None."""
        await db_manager.close()
        assert db_manager._pool is None


class TestDatabaseManagerHealthCheck:
    """Tests for the health_check method."""

    async def test_should_return_healthy(self, db_manager: DatabaseManager) -> None:
        """Validate healthy status when query succeeds."""
        mock_pool = AsyncMock()
        mock_record: dict[str, Any] = {"server_version": "PostgreSQL 16.1"}
        mock_pool.fetchrow = AsyncMock(return_value=mock_record)
        db_manager._pool = mock_pool

        result = await db_manager.health_check()

        assert result["status"] == "healthy"
        assert result["host"] == "localhost"
        assert result["database"] == "atlas_mcp"
        assert result["server_version"] == "PostgreSQL 16.1"

    async def test_should_return_unhealthy_on_error(self, db_manager: DatabaseManager) -> None:
        """Validate unhealthy status when query fails."""
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(side_effect=ConnectionError("connection refused"))
        db_manager._pool = mock_pool

        result = await db_manager.health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "connection refused" in result["error"]

    async def test_should_return_unknown_version_if_row_is_none(
        self, db_manager: DatabaseManager
    ) -> None:
        """Validate server_version is 'unknown' when fetchrow returns None."""
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=None)
        db_manager._pool = mock_pool

        result = await db_manager.health_check()

        assert result["status"] == "healthy"
        assert result["server_version"] == "unknown"


class TestDatabaseManagerQueryMethods:
    """Tests for execute, fetch, fetchrow, fetchval."""

    async def test_execute_delegates_to_pool(self, db_manager: DatabaseManager) -> None:
        """Validate that execute delegates to pool.execute."""
        mock_pool = AsyncMock()
        mock_pool.execute = AsyncMock(return_value="INSERT 0 1")
        db_manager._pool = mock_pool

        result = await db_manager.execute("INSERT INTO t VALUES ($1)", "val")

        mock_pool.execute.assert_called_once_with("INSERT INTO t VALUES ($1)", "val")
        assert result == "INSERT 0 1"

    async def test_fetch_delegates_to_pool(self, db_manager: DatabaseManager) -> None:
        """Validate that fetch delegates to pool.fetch."""
        mock_pool = AsyncMock()
        mock_records = [{"id": 1}, {"id": 2}]
        mock_pool.fetch = AsyncMock(return_value=mock_records)
        db_manager._pool = mock_pool

        result = await db_manager.fetch("SELECT * FROM t")

        mock_pool.fetch.assert_called_once_with("SELECT * FROM t")
        assert result == mock_records

    async def test_fetchrow_delegates_to_pool(self, db_manager: DatabaseManager) -> None:
        """Validate that fetchrow delegates to pool.fetchrow."""
        mock_pool = AsyncMock()
        mock_record: dict[str, int] = {"id": 1}
        mock_pool.fetchrow = AsyncMock(return_value=mock_record)
        db_manager._pool = mock_pool

        result = await db_manager.fetchrow("SELECT * FROM t WHERE id = $1", 1)

        mock_pool.fetchrow.assert_called_once_with("SELECT * FROM t WHERE id = $1", 1)
        assert result == mock_record

    async def test_fetchval_delegates_to_pool(self, db_manager: DatabaseManager) -> None:
        """Validate that fetchval delegates to pool.fetchval."""
        mock_pool = AsyncMock()
        mock_pool.fetchval = AsyncMock(return_value=42)
        db_manager._pool = mock_pool

        result = await db_manager.fetchval("SELECT count(*) FROM t")

        mock_pool.fetchval.assert_called_once_with("SELECT count(*) FROM t")
        assert result == 42


class TestDatabaseManagerContextManager:
    """Tests for async context manager protocol."""

    @patch("atlas_mcp.persistence.database.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_should_initialize_and_close(
        self, mock_create_pool: AsyncMock, db_config: DatabaseConfig
    ) -> None:
        """Validate that entering creates pool and exiting closes it."""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        async with DatabaseManager(db_config) as manager:
            assert manager._pool is mock_pool

        mock_pool.close.assert_called_once()

    @patch("atlas_mcp.persistence.database.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_should_close_on_exception(
        self, mock_create_pool: AsyncMock, db_config: DatabaseConfig
    ) -> None:
        """Validate that pool is closed even when exception occurs."""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        with pytest.raises(ValueError, match="test error"):
            async with DatabaseManager(db_config):
                raise ValueError("test error")

        mock_pool.close.assert_called_once()
