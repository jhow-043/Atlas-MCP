"""Fixtures compartilhadas para testes."""

import pytest


@pytest.fixture
def sample_query() -> str:
    """Query de exemplo para testes de busca."""
    return "Como configurar o banco de dados?"
