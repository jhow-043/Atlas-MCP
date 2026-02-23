"""Shared fixtures for integration tests.

Integration tests require a running PostgreSQL instance.
Use ``docker compose up -d`` before running.
"""

from __future__ import annotations

import os

import pytest


def _db_available() -> bool:
    """Check if DATABASE_URL or POSTGRES_* env vars are set."""
    return bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_HOST"))


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="Integration tests require DATABASE_URL or POSTGRES_* env vars",
)
