"""Shared fixtures for integration tests.

Integration tests require a running PostgreSQL instance.
Use ``docker compose up -d`` before running.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from atlas_mcp.persistence.config import DatabaseConfig
from atlas_mcp.persistence.database import DatabaseManager
from atlas_mcp.persistence.migrations import MigrationRunner
from atlas_mcp.persistence.vector_codec import register_vector_codec


def _db_available() -> bool:
    """Check if DATABASE_URL or POSTGRES_* env vars are set."""
    return bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_HOST"))


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="Integration tests require DATABASE_URL or POSTGRES_* env vars",
)


def _db_config() -> DatabaseConfig:
    """Build a DatabaseConfig for the integration test database."""
    return DatabaseConfig(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ.get("POSTGRES_USER", "atlas"),
        password=os.environ.get("POSTGRES_PASSWORD", "atlas_dev"),
        database=os.environ.get("POSTGRES_DB", "atlas_mcp"),
    )


async def _db_is_reachable(config: DatabaseConfig) -> bool:
    """Try to connect to the PostgreSQL instance."""
    try:
        import asyncpg

        conn = await asyncio.wait_for(
            asyncpg.connect(dsn=config.dsn),
            timeout=3.0,
        )
        await conn.close()
    except Exception:
        return False
    else:
        return True


@pytest.fixture(scope="session")
def db_config() -> DatabaseConfig:
    """Provide the integration test database configuration."""
    return _db_config()


@pytest.fixture(scope="session")
def _check_db(db_config: DatabaseConfig) -> None:
    """Skip the entire session if the database is unreachable."""
    loop = asyncio.new_event_loop()
    reachable = loop.run_until_complete(_db_is_reachable(db_config))
    loop.close()
    if not reachable:
        pytest.skip(
            f"PostgreSQL not reachable at {db_config.host}:{db_config.port}. "
            "Run 'docker compose up -d' first.",
        )


@pytest_asyncio.fixture
async def db_manager(
    db_config: DatabaseConfig,
    _check_db: None,
) -> AsyncGenerator[DatabaseManager, None]:
    """Provide an initialized DatabaseManager and clean up after test."""
    manager = DatabaseManager(db_config)
    await manager.initialize()

    runner = MigrationRunner(manager.pool)
    await runner.run()

    async with manager.pool.acquire() as conn:
        await register_vector_codec(conn)

    yield manager

    # Clean up test data
    await manager.execute("DELETE FROM chunks")
    await manager.execute("DELETE FROM audit_log")
    await manager.execute("DELETE FROM documents")
    await manager.close()
