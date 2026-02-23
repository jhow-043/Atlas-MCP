"""Application bootstrap — wires all components into a running server.

The :class:`ApplicationBootstrap` orchestrates the full startup and
shutdown sequence: database, migrations, vector codec, embedding
provider, vector store, indexing service, governance hooks, and
tool configuration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas_mcp.config.settings import Settings
    from atlas_mcp.governance.audit import AuditLogger
    from atlas_mcp.governance.service import GovernanceService
    from atlas_mcp.persistence.database import DatabaseManager
    from atlas_mcp.vectorization.embeddings import EmbeddingProvider
    from atlas_mcp.vectorization.indexing import IndexingService
    from atlas_mcp.vectorization.store import VectorStore

logger = logging.getLogger(__name__)


class ApplicationBootstrap:
    """Orchestrate application startup and shutdown.

    Holds references to all infrastructure components so they can
    be properly torn down on shutdown.

    Usage::

        bootstrap = ApplicationBootstrap()
        await bootstrap.startup(settings)
        # ... server runs ...
        await bootstrap.shutdown()
    """

    def __init__(self) -> None:
        """Initialize with no active components."""
        self._db: DatabaseManager | None = None
        self._embedder: EmbeddingProvider | None = None
        self._store: VectorStore | None = None
        self._indexing: IndexingService | None = None
        self._governance: GovernanceService | None = None
        self._audit: AuditLogger | None = None

    @property
    def db(self) -> DatabaseManager | None:
        """Return the database manager (if initialized)."""
        return self._db

    async def startup(self, settings: Settings) -> None:
        """Execute the full startup sequence.

        Steps:
            1. Initialize database connection pool.
            2. Run pending migrations.
            3. Register pgvector codec on the pool.
            4. Create embedding provider.
            5. Create vector store and indexing service.
            6. Configure RAG tools (search_context, plan_feature, analyze_bug).
            7. Wire governance → indexing callback.

        If the database is unavailable, the server enters **degraded mode**:
        resources and ``register_adr`` work normally, but RAG tools will
        return a ``SERVICE_UNAVAILABLE`` error when called.

        Args:
            settings: The application settings.
        """
        logger.info("Bootstrap: starting up...")

        try:
            await self._init_database(settings)
            await self._init_vectorization(settings)
            self._configure_tools()
            await self._init_governance()
            logger.info("Bootstrap: full startup complete — RAG enabled.")
        except Exception:
            logger.exception(
                "Bootstrap: database/RAG startup failed — running in degraded mode "
                "(resources and register_adr available, RAG tools unavailable)."
            )

    async def shutdown(self) -> None:
        """Shut down all components gracefully.

        Closes the database connection pool if it was initialized.
        """
        logger.info("Bootstrap: shutting down...")

        if self._db is not None:
            try:
                await self._db.close()
                logger.info("Bootstrap: database connection pool closed.")
            except Exception:
                logger.exception("Bootstrap: error closing database pool.")

        self._db = None
        self._embedder = None
        self._store = None
        self._indexing = None
        self._governance = None
        self._audit = None
        logger.info("Bootstrap: shutdown complete.")

    # ── private helpers ──────────────────────────────────────

    async def _init_database(self, settings: Settings) -> None:
        """Initialize database pool, run migrations, register codec.

        Args:
            settings: The application settings.

        Raises:
            Exception: If the database connection or migration fails.
        """
        from atlas_mcp.persistence.database import DatabaseManager
        from atlas_mcp.persistence.migrations import MigrationRunner
        from atlas_mcp.persistence.vector_codec import register_vector_codec

        self._db = DatabaseManager(settings.db)
        await self._db.initialize()
        logger.info("Bootstrap: database pool initialized.")

        runner = MigrationRunner(self._db.pool)
        applied = await runner.run()
        if applied:
            logger.info(
                "Bootstrap: applied %d migration(s): %s",
                len(applied),
                [m.version for m in applied],
            )
        else:
            logger.info("Bootstrap: all migrations already applied.")

        async with self._db.pool.acquire() as conn:
            await register_vector_codec(conn)
        logger.info("Bootstrap: pgvector codec registered.")

    async def _init_vectorization(self, settings: Settings) -> None:
        """Create embedding provider, vector store, and indexing service.

        Args:
            settings: The application settings.

        Raises:
            Exception: If provider initialization fails.
        """
        from atlas_mcp.vectorization.chunker import MarkdownChunker
        from atlas_mcp.vectorization.embeddings import create_embedding_provider
        from atlas_mcp.vectorization.indexing import IndexingService
        from atlas_mcp.vectorization.store import VectorStore

        assert self._db is not None  # noqa: S101

        # Map settings provider name to factory name
        provider_type = settings.embedding_provider
        if provider_type == "sentence-transformers":
            provider_type = "sentence_transformer"

        kwargs: dict[str, str | None] = {"model": settings.embedding_model}
        if settings.embedding_provider == "openai":
            kwargs["api_key"] = settings.openai_api_key

        self._embedder = create_embedding_provider(provider_type, **kwargs)
        self._store = VectorStore(self._db)

        chunker = MarkdownChunker()
        self._indexing = IndexingService(chunker, self._embedder, self._store)

        logger.info(
            "Bootstrap: vectorization initialized (provider=%s, model=%s, dim=%d).",
            settings.embedding_provider,
            settings.embedding_model,
            self._embedder.dimension,
        )

    def _configure_tools(self) -> None:
        """Configure RAG tools with the initialized embedder and store."""
        from atlas_mcp.tools import analyze_bug, plan_feature, search_context

        assert self._embedder is not None  # noqa: S101
        assert self._store is not None  # noqa: S101

        search_context.configure(self._embedder, self._store)
        plan_feature.configure(self._embedder, self._store)
        analyze_bug.configure(self._embedder, self._store)
        logger.info("Bootstrap: RAG tools configured.")

    async def _init_governance(self) -> None:
        """Wire governance service with indexing callback."""
        from atlas_mcp.governance.audit import AuditLogger
        from atlas_mcp.governance.service import GovernanceService

        assert self._db is not None  # noqa: S101
        assert self._indexing is not None  # noqa: S101

        self._audit = AuditLogger(self._db)
        self._governance = GovernanceService(self._db, self._audit)
        self._governance.register_on_status_change(self._indexing.on_status_change)
        logger.info("Bootstrap: governance → indexing hook registered.")
