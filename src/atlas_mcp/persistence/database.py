"""Async database connection manager using asyncpg.

Provides connection pool management, query execution helpers,
and health check functionality for PostgreSQL.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import asyncpg

if TYPE_CHECKING:
    from atlas_mcp.persistence.config import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manage an asyncpg connection pool with lifecycle control.

    Usage::

        db = DatabaseManager(config)
        await db.initialize()
        row = await db.fetchrow("SELECT 1 AS ok")
        await db.close()

    Or as an async context manager::

        async with DatabaseManager(config) as db:
            row = await db.fetchrow("SELECT 1 AS ok")

    Attributes:
        config: The database configuration.
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """Initialize with database configuration.

        Args:
            config: The database connection configuration.
        """
        self.config = config
        self._pool: asyncpg.Pool[asyncpg.Record] | None = None

    @property
    def pool(self) -> asyncpg.Pool[asyncpg.Record]:
        """Return the current connection pool.

        Returns:
            The active asyncpg connection pool.

        Raises:
            RuntimeError: If the pool has not been initialized.
        """
        if self._pool is None:
            raise RuntimeError("DatabaseManager is not initialized. Call initialize() first.")
        return self._pool

    async def initialize(self) -> None:
        """Create the asyncpg connection pool.

        Raises:
            asyncpg.PostgresError: If the connection fails.
        """
        if self._pool is not None:
            logger.warning("DatabaseManager already initialized, skipping.")
            return

        logger.info("Initializing database connection pool: %s", self.config.host)
        self._pool = await asyncpg.create_pool(
            dsn=self.config.dsn,
            min_size=self.config.min_pool_size,
            max_size=self.config.max_pool_size,
        )
        logger.info("Database connection pool created successfully.")

    async def close(self) -> None:
        """Close the connection pool and release resources."""
        if self._pool is not None:
            logger.info("Closing database connection pool.")
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed.")

    async def health_check(self) -> dict[str, Any]:
        """Check database connectivity.

        Returns:
            A dictionary with ``status``, ``host``, ``database``
            and optionally ``server_version``.
        """
        base: dict[str, Any] = {
            "host": self.config.host,
            "database": self.config.database,
        }
        try:
            row = await self.fetchrow("SELECT version() AS server_version")
            return {
                "status": "healthy",
                **base,
                "server_version": row["server_version"] if row else "unknown",
            }
        except Exception as exc:
            logger.error("Health check failed: %s", exc)
            return {"status": "unhealthy", **base, "error": str(exc)}

    async def execute(self, query: str, *args: Any) -> str:
        """Execute a SQL statement.

        Args:
            query: The SQL query string.
            *args: Query parameters.

        Returns:
            The command status string (e.g. ``'INSERT 0 1'``).
        """
        return await self.pool.execute(query, *args)  # type: ignore[no-any-return]

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        """Execute a query and return all rows.

        Args:
            query: The SQL query string.
            *args: Query parameters.

        Returns:
            A list of :class:`asyncpg.Record` objects.
        """
        return await self.pool.fetch(query, *args)  # type: ignore[no-any-return]

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        """Execute a query and return a single row.

        Args:
            query: The SQL query string.
            *args: Query parameters.

        Returns:
            A single :class:`asyncpg.Record` or ``None``.
        """
        return await self.pool.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Any:
        """Execute a query and return a single value.

        Args:
            query: The SQL query string.
            *args: Query parameters.

        Returns:
            The first column of the first row, or ``None``.
        """
        return await self.pool.fetchval(query, *args)

    async def __aenter__(self) -> DatabaseManager:
        """Enter context manager — initialize the pool."""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager — close the pool."""
        await self.close()
