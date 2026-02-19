"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_query() -> str:
    """Return a sample search query for testing."""
    return "Como configurar o banco de dados?"
