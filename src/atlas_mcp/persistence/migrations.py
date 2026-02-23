"""Database schema migrations for Atlas MCP.

Defines SQL schemas and a runner that applies migrations
sequentially in a single transaction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

MIGRATION_TABLE_SQL: Final[str] = """\
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version INTEGER NOT NULL UNIQUE,
    description TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

DOCUMENTS_TABLE_SQL: Final[str] = """\
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROPOSED',
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

AUDIT_LOG_TABLE_SQL: Final[str] = """\
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

DOCUMENTS_INDEX_SQL: Final[str] = """\
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents (doc_type);
"""

AUDIT_LOG_INDEX_SQL: Final[str] = """\
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log (action);
"""

PGVECTOR_EXTENSION_SQL: Final[str] = """\
CREATE EXTENSION IF NOT EXISTS vector;
"""

CHUNKS_TABLE_SQL: Final[str] = """\
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    section_path TEXT NOT NULL DEFAULT '',
    chunk_index INTEGER NOT NULL DEFAULT 0,
    embedding vector(1536) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CHUNKS_INDEX_SQL: Final[str] = """\
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops);
"""


# ---------------------------------------------------------------------------
# Migration registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Migration:
    """A single schema migration step.

    Attributes:
        version: Sequential migration version number.
        description: Human-readable description of the migration.
        sql: The SQL statement(s) to execute.
    """

    version: int
    description: str
    sql: str


#: Ordered list of all migrations. New migrations must be appended.
MIGRATIONS: Final[list[Migration]] = [
    Migration(
        version=1,
        description="Create documents table",
        sql=DOCUMENTS_TABLE_SQL,
    ),
    Migration(
        version=2,
        description="Create audit_log table",
        sql=AUDIT_LOG_TABLE_SQL,
    ),
    Migration(
        version=3,
        description="Create indexes for documents",
        sql=DOCUMENTS_INDEX_SQL,
    ),
    Migration(
        version=4,
        description="Create indexes for audit_log",
        sql=AUDIT_LOG_INDEX_SQL,
    ),
    Migration(
        version=5,
        description="Enable pgvector extension",
        sql=PGVECTOR_EXTENSION_SQL,
    ),
    Migration(
        version=6,
        description="Create chunks table for vector storage",
        sql=CHUNKS_TABLE_SQL,
    ),
    Migration(
        version=7,
        description="Create HNSW index on chunks embedding",
        sql=CHUNKS_INDEX_SQL,
    ),
]


# ---------------------------------------------------------------------------
# Migration runner
# ---------------------------------------------------------------------------


class MigrationRunner:
    """Apply pending migrations to a database.

    The runner tracks which migrations have already been applied
    via the ``schema_migrations`` table and only executes new ones.

    Args:
        pool: An asyncpg connection pool.
    """

    def __init__(self, pool: asyncpg.Pool[asyncpg.Record]) -> None:
        """Initialize with an asyncpg connection pool.

        Args:
            pool: An active asyncpg connection pool.
        """
        self._pool = pool

    async def _ensure_migration_table(self, conn: asyncpg.Connection[asyncpg.Record]) -> None:
        """Create the schema_migrations table if it does not exist."""
        await conn.execute(MIGRATION_TABLE_SQL)

    async def _get_applied_versions(self, conn: asyncpg.Connection[asyncpg.Record]) -> set[int]:
        """Return the set of already-applied migration versions."""
        rows = await conn.fetch("SELECT version FROM schema_migrations")
        return {row["version"] for row in rows}

    async def run(self, *, migrations: list[Migration] | None = None) -> list[Migration]:
        """Apply all pending migrations inside a transaction.

        Args:
            migrations: Optional list of migrations to consider.
                Defaults to :data:`MIGRATIONS`.

        Returns:
            The list of migrations that were applied.
        """
        target = migrations if migrations is not None else MIGRATIONS

        applied: list[Migration] = []
        async with self._pool.acquire() as conn, conn.transaction():
            await self._ensure_migration_table(conn)
            already_applied = await self._get_applied_versions(conn)

            for migration in target:
                if migration.version in already_applied:
                    logger.debug(
                        "Migration v%d already applied, skipping.",
                        migration.version,
                    )
                    continue

                logger.info(
                    "Applying migration v%d: %s",
                    migration.version,
                    migration.description,
                )
                await conn.execute(migration.sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES ($1, $2)",
                    migration.version,
                    migration.description,
                )
                applied.append(migration)

        if applied:
            logger.info("Applied %d migration(s).", len(applied))
        else:
            logger.info("No pending migrations.")

        return applied

    async def get_status(self) -> list[dict[str, object]]:
        """Return the status of all known migrations.

        Returns:
            A list of dicts with ``version``, ``description``,
            and ``applied`` fields.
        """
        async with self._pool.acquire() as conn:
            await self._ensure_migration_table(conn)
            applied_versions = await self._get_applied_versions(conn)

        target = MIGRATIONS
        return [
            {
                "version": m.version,
                "description": m.description,
                "applied": m.version in applied_versions,
            }
            for m in target
        ]
