"""Database connection configuration.

Reads PostgreSQL connection parameters from environment variables
with sensible defaults for local development.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseConfig:
    """Immutable database connection configuration.

    Attributes:
        host: PostgreSQL host.
        port: PostgreSQL port.
        user: PostgreSQL user.
        password: PostgreSQL password.
        database: PostgreSQL database name.
        min_pool_size: Minimum connection pool size.
        max_pool_size: Maximum connection pool size.
    """

    host: str = "localhost"
    port: int = 5432
    user: str = "atlas"
    password: str = "atlas_dev"  # noqa: S105
    database: str = "atlas_mcp"
    min_pool_size: int = 2
    max_pool_size: int = 10

    @property
    def dsn(self) -> str:
        """Return the PostgreSQL DSN connection string.

        Returns:
            A ``postgresql://`` URI.
        """
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        """Create a configuration from environment variables.

        Reads ``POSTGRES_HOST``, ``POSTGRES_PORT``, ``POSTGRES_USER``,
        ``POSTGRES_PASSWORD``, ``POSTGRES_DB``, ``DB_MIN_POOL_SIZE``
        and ``DB_MAX_POOL_SIZE``.  Falls back to defaults when a
        variable is not set.

        If ``DATABASE_URL`` is set, it takes precedence and the
        individual variables are ignored.

        Returns:
            A new :class:`DatabaseConfig` instance.
        """
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            return cls._from_dsn(database_url)

        return cls(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            user=os.environ.get("POSTGRES_USER", "atlas"),
            password=os.environ.get("POSTGRES_PASSWORD", "atlas_dev"),
            database=os.environ.get("POSTGRES_DB", "atlas_mcp"),
            min_pool_size=int(os.environ.get("DB_MIN_POOL_SIZE", "2")),
            max_pool_size=int(os.environ.get("DB_MAX_POOL_SIZE", "10")),
        )

    @classmethod
    def _from_dsn(cls, dsn: str) -> DatabaseConfig:
        """Parse a ``DATABASE_URL`` into a config.

        Supports format: ``postgresql://user:password@host:port/database``

        Args:
            dsn: The database connection string.

        Returns:
            A new :class:`DatabaseConfig` instance.

        Raises:
            ValueError: If the DSN format is invalid.
        """
        from urllib.parse import urlparse

        parsed = urlparse(dsn)
        if not parsed.hostname:
            raise ValueError(f"Invalid DATABASE_URL: missing hostname in '{dsn}'")
        if not parsed.path or parsed.path == "/":
            raise ValueError(f"Invalid DATABASE_URL: missing database name in '{dsn}'")

        return cls(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username or "atlas",
            password=parsed.password or "",
            database=parsed.path.lstrip("/"),
            min_pool_size=int(os.environ.get("DB_MIN_POOL_SIZE", "2")),
            max_pool_size=int(os.environ.get("DB_MAX_POOL_SIZE", "10")),
        )
