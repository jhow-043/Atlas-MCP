"""Tests for the migrations module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from atlas_mcp.persistence.migrations import (
    AUDIT_LOG_INDEX_SQL,
    AUDIT_LOG_TABLE_SQL,
    CHUNKS_INDEX_SQL,
    CHUNKS_TABLE_SQL,
    DOCUMENTS_INDEX_SQL,
    DOCUMENTS_TABLE_SQL,
    MIGRATION_TABLE_SQL,
    MIGRATIONS,
    PGVECTOR_EXTENSION_SQL,
    Migration,
    MigrationRunner,
)


class TestMigrationDataclass:
    """Tests for the Migration dataclass."""

    def test_should_store_fields(self) -> None:
        """Validate that Migration stores version, description, sql."""
        m = Migration(version=1, description="test", sql="SELECT 1")
        assert m.version == 1
        assert m.description == "test"
        assert m.sql == "SELECT 1"

    def test_should_be_frozen(self) -> None:
        """Validate that Migration is immutable."""
        m = Migration(version=1, description="test", sql="SELECT 1")
        with pytest.raises(AttributeError):
            m.version = 2  # type: ignore[misc]


class TestSQLConstants:
    """Tests for SQL schema constants."""

    def test_migration_table_has_version_column(self) -> None:
        """Validate schema_migrations schema."""
        assert "version INTEGER" in MIGRATION_TABLE_SQL
        assert "schema_migrations" in MIGRATION_TABLE_SQL

    def test_documents_table_has_required_columns(self) -> None:
        """Validate documents table schema."""
        assert "title TEXT NOT NULL" in DOCUMENTS_TABLE_SQL
        assert "content TEXT NOT NULL" in DOCUMENTS_TABLE_SQL
        assert "doc_type TEXT NOT NULL" in DOCUMENTS_TABLE_SQL
        assert "status TEXT NOT NULL" in DOCUMENTS_TABLE_SQL
        assert "metadata JSONB" in DOCUMENTS_TABLE_SQL

    def test_audit_log_table_has_required_columns(self) -> None:
        """Validate audit_log table schema."""
        assert "entity_type TEXT NOT NULL" in AUDIT_LOG_TABLE_SQL
        assert "entity_id INTEGER NOT NULL" in AUDIT_LOG_TABLE_SQL
        assert "action TEXT NOT NULL" in AUDIT_LOG_TABLE_SQL
        assert "old_status TEXT" in AUDIT_LOG_TABLE_SQL
        assert "new_status TEXT" in AUDIT_LOG_TABLE_SQL

    def test_documents_indexes(self) -> None:
        """Validate documents index SQL."""
        assert "idx_documents_status" in DOCUMENTS_INDEX_SQL
        assert "idx_documents_doc_type" in DOCUMENTS_INDEX_SQL

    def test_audit_log_indexes(self) -> None:
        """Validate audit_log index SQL."""
        assert "idx_audit_log_entity" in AUDIT_LOG_INDEX_SQL
        assert "idx_audit_log_action" in AUDIT_LOG_INDEX_SQL

    def test_pgvector_extension_sql(self) -> None:
        """Validate pgvector extension SQL."""
        assert "CREATE EXTENSION" in PGVECTOR_EXTENSION_SQL
        assert "vector" in PGVECTOR_EXTENSION_SQL

    def test_chunks_table_has_required_columns(self) -> None:
        """Validate chunks table schema."""
        assert "document_id INTEGER NOT NULL" in CHUNKS_TABLE_SQL
        assert "content TEXT NOT NULL" in CHUNKS_TABLE_SQL
        assert "section_path TEXT NOT NULL" in CHUNKS_TABLE_SQL
        assert "chunk_index INTEGER NOT NULL" in CHUNKS_TABLE_SQL
        assert "embedding vector(1536) NOT NULL" in CHUNKS_TABLE_SQL
        assert "metadata JSONB" in CHUNKS_TABLE_SQL
        assert "REFERENCES documents(id)" in CHUNKS_TABLE_SQL
        assert "ON DELETE CASCADE" in CHUNKS_TABLE_SQL

    def test_chunks_indexes(self) -> None:
        """Validate chunks index SQL."""
        assert "idx_chunks_document_id" in CHUNKS_INDEX_SQL
        assert "idx_chunks_embedding_hnsw" in CHUNKS_INDEX_SQL
        assert "vector_cosine_ops" in CHUNKS_INDEX_SQL
        assert "hnsw" in CHUNKS_INDEX_SQL.lower()


class TestMigrationsRegistry:
    """Tests for the MIGRATIONS list."""

    def test_should_have_sequential_versions(self) -> None:
        """Validate that migration versions are sequential starting at 1."""
        versions = [m.version for m in MIGRATIONS]
        assert versions == list(range(1, len(MIGRATIONS) + 1))

    def test_should_have_seven_migrations(self) -> None:
        """Validate the expected number of migrations."""
        assert len(MIGRATIONS) == 7

    def test_should_have_unique_versions(self) -> None:
        """Validate that no duplicate versions exist."""
        versions = [m.version for m in MIGRATIONS]
        assert len(versions) == len(set(versions))

    def test_all_have_non_empty_description(self) -> None:
        """Validate all migrations have descriptions."""
        for m in MIGRATIONS:
            assert m.description, f"Migration v{m.version} has empty description"

    def test_all_have_non_empty_sql(self) -> None:
        """Validate all migrations have SQL."""
        for m in MIGRATIONS:
            assert m.sql.strip(), f"Migration v{m.version} has empty SQL"


def _make_mock_pool() -> AsyncMock:
    """Create a mock asyncpg pool with connection and transaction support."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])

    mock_transaction = AsyncMock()
    mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
    mock_transaction.__aexit__ = AsyncMock(return_value=False)
    mock_conn.transaction = MagicMock(return_value=mock_transaction)

    mock_pool = AsyncMock()
    mock_acquire = AsyncMock()
    mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire.__aexit__ = AsyncMock(return_value=False)
    mock_pool.acquire = MagicMock(return_value=mock_acquire)

    return mock_pool


class TestMigrationRunner:
    """Tests for the MigrationRunner class."""

    async def test_should_create_migration_table(self) -> None:
        """Validate that run creates schema_migrations table."""
        mock_pool = _make_mock_pool()
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value

        runner = MigrationRunner(mock_pool)
        await runner.run(migrations=[])

        # First execute call is the migration table creation
        calls = mock_conn.execute.call_args_list
        # Check that MIGRATION_TABLE_SQL was passed as first positional arg
        executed_sqls = [c.args[0] if c.args else "" for c in calls]
        assert MIGRATION_TABLE_SQL in executed_sqls

    async def test_should_apply_pending_migrations(self) -> None:
        """Validate that pending migrations are applied."""
        mock_pool = _make_mock_pool()
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        # No migrations applied yet
        mock_conn.fetch = AsyncMock(return_value=[])

        test_migrations = [
            Migration(version=1, description="test1", sql="CREATE TABLE t1 (id INT)"),
            Migration(version=2, description="test2", sql="CREATE TABLE t2 (id INT)"),
        ]

        runner = MigrationRunner(mock_pool)
        applied = await runner.run(migrations=test_migrations)

        assert len(applied) == 2
        assert applied[0].version == 1
        assert applied[1].version == 2

    async def test_should_skip_already_applied(self) -> None:
        """Validate that already-applied migrations are skipped."""
        mock_pool = _make_mock_pool()
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        # Version 1 already applied
        mock_conn.fetch = AsyncMock(return_value=[{"version": 1}])

        test_migrations = [
            Migration(version=1, description="test1", sql="CREATE TABLE t1 (id INT)"),
            Migration(version=2, description="test2", sql="CREATE TABLE t2 (id INT)"),
        ]

        runner = MigrationRunner(mock_pool)
        applied = await runner.run(migrations=test_migrations)

        assert len(applied) == 1
        assert applied[0].version == 2

    async def test_should_return_empty_when_all_applied(self) -> None:
        """Validate empty result when all migrations are applied."""
        mock_pool = _make_mock_pool()
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(return_value=[{"version": 1}, {"version": 2}])

        test_migrations = [
            Migration(version=1, description="test1", sql="SELECT 1"),
            Migration(version=2, description="test2", sql="SELECT 2"),
        ]

        runner = MigrationRunner(mock_pool)
        applied = await runner.run(migrations=test_migrations)

        assert len(applied) == 0

    async def test_should_insert_into_schema_migrations(self) -> None:
        """Validate that applied migrations are recorded in schema_migrations."""
        mock_pool = _make_mock_pool()
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(return_value=[])

        test_migrations = [
            Migration(version=1, description="Create stuff", sql="SELECT 1"),
        ]

        runner = MigrationRunner(mock_pool)
        await runner.run(migrations=test_migrations)

        # Should have: migration_table, migration SQL, INSERT
        calls = mock_conn.execute.call_args_list
        insert_calls = [c for c in calls if "INSERT INTO schema_migrations" in str(c)]
        assert len(insert_calls) == 1

    async def test_should_use_default_migrations_when_none_provided(self) -> None:
        """Validate that default MIGRATIONS are used when none passed."""
        mock_pool = _make_mock_pool()
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        # All default migrations already applied
        mock_conn.fetch = AsyncMock(return_value=[{"version": m.version} for m in MIGRATIONS])

        runner = MigrationRunner(mock_pool)
        applied = await runner.run()

        assert len(applied) == 0


class TestMigrationRunnerGetStatus:
    """Tests for the get_status method."""

    async def test_should_return_status_for_all_migrations(self) -> None:
        """Validate status returns all migrations with applied flag."""
        mock_pool = _make_mock_pool()
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(return_value=[{"version": 1}])

        runner = MigrationRunner(mock_pool)
        status = await runner.get_status()

        assert len(status) == len(MIGRATIONS)
        # v1 should be applied, rest not
        v1 = next(s for s in status if s["version"] == 1)
        v2 = next(s for s in status if s["version"] == 2)
        assert v1["applied"] is True
        assert v2["applied"] is False

    async def test_should_return_all_not_applied_when_fresh(self) -> None:
        """Validate that fresh DB shows all as not applied."""
        mock_pool = _make_mock_pool()
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(return_value=[])

        runner = MigrationRunner(mock_pool)
        status = await runner.get_status()

        assert all(s["applied"] is False for s in status)

    async def test_status_contains_description(self) -> None:
        """Validate that status entries contain description."""
        mock_pool = _make_mock_pool()
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch = AsyncMock(return_value=[])

        runner = MigrationRunner(mock_pool)
        status = await runner.get_status()

        for s in status:
            assert "description" in s
            assert isinstance(s["description"], str)
            assert s["description"]
