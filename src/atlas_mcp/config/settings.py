"""Centralized application settings.

Reads all configuration from environment variables (with ``.env`` support)
and composes the existing :class:`DatabaseConfig` for persistence.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from atlas_mcp.persistence.config import DatabaseConfig

_VALID_PROVIDERS = frozenset({"openai", "sentence-transformers"})
_VALID_TRANSPORTS = frozenset({"stdio", "sse"})
_VALID_LOG_FORMATS = frozenset({"text", "json"})

_DEFAULT_MODELS: dict[str, str] = {
    "openai": "text-embedding-3-small",
    "sentence-transformers": "all-MiniLM-L6-v2",
}

_DEFAULT_DIMENSIONS: dict[str, int] = {
    "openai": 1536,
    "sentence-transformers": 384,
}


@dataclass(frozen=True)
class Settings:
    """Immutable application settings.

    Attributes:
        db: Database connection configuration.
        embedding_provider: Embedding backend (``openai`` or ``sentence-transformers``).
        embedding_model: Model name for the embedding provider.
        embedding_dimension: Dimensionality of the embedding vectors.
        openai_api_key: OpenAI API key (required when provider is ``openai``).
        transport: MCP transport mode (``stdio`` or ``sse``).
        sse_host: Host to bind when using SSE transport.
        sse_port: Port to bind when using SSE transport.
        log_level: Python logging level name.
        log_format: Log output format (``text`` or ``json``).
    """

    db: DatabaseConfig
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    openai_api_key: str | None = None
    transport: str = "stdio"
    sse_host: str = "0.0.0.0"  # noqa: S104
    sse_port: int = 8000
    log_level: str = "INFO"
    log_format: str = "text"

    @classmethod
    def from_env(cls, *, dotenv_path: str | None = None) -> Settings:
        """Create settings from environment variables.

        Loads a ``.env`` file (if present) before reading ``os.environ``.

        Environment variables
        ---------------------
        ``EMBEDDING_PROVIDER``
            ``openai`` (default) or ``sentence-transformers``.
        ``EMBEDDING_MODEL``
            Model name; defaults depend on provider.
        ``EMBEDDING_DIMENSION``
            Vector dimension; defaults depend on provider.
        ``OPENAI_API_KEY``
            Required when ``EMBEDDING_PROVIDER=openai``.
        ``ATLAS_TRANSPORT``
            ``stdio`` (default) or ``sse``.
        ``ATLAS_SSE_HOST``
            Bind host for SSE (default ``0.0.0.0``).
        ``ATLAS_SSE_PORT``
            Bind port for SSE (default ``8000``).
        ``ATLAS_LOG_LEVEL``
            Python log level (default ``INFO``).
        ``ATLAS_LOG_FORMAT``
            ``text`` (default) or ``json``.

        Args:
            dotenv_path: Optional explicit path to a ``.env`` file.

        Returns:
            A new :class:`Settings` instance.

        Raises:
            ValueError: If an invalid provider, transport or log format is given.
        """
        load_dotenv(dotenv_path=dotenv_path, override=False)

        provider = os.environ.get("EMBEDDING_PROVIDER", "openai").lower()
        _validate_choice("EMBEDDING_PROVIDER", provider, _VALID_PROVIDERS)

        model = os.environ.get(
            "EMBEDDING_MODEL",
            _DEFAULT_MODELS.get(provider, "text-embedding-3-small"),
        )
        dimension = int(
            os.environ.get(
                "EMBEDDING_DIMENSION",
                str(_DEFAULT_DIMENSIONS.get(provider, 1536)),
            )
        )

        transport = os.environ.get("ATLAS_TRANSPORT", "stdio").lower()
        _validate_choice("ATLAS_TRANSPORT", transport, _VALID_TRANSPORTS)

        log_format = os.environ.get("ATLAS_LOG_FORMAT", "text").lower()
        _validate_choice("ATLAS_LOG_FORMAT", log_format, _VALID_LOG_FORMATS)

        return cls(
            db=DatabaseConfig.from_env(),
            embedding_provider=provider,
            embedding_model=model,
            embedding_dimension=dimension,
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            transport=transport,
            sse_host=os.environ.get("ATLAS_SSE_HOST", "0.0.0.0"),  # noqa: S104
            sse_port=int(os.environ.get("ATLAS_SSE_PORT", "8000")),
            log_level=os.environ.get("ATLAS_LOG_LEVEL", "INFO").upper(),
            log_format=log_format,
        )


def _validate_choice(name: str, value: str, valid: frozenset[str]) -> None:
    """Raise :class:`ValueError` if *value* is not in *valid*.

    Args:
        name: Environment variable name (for the error message).
        value: The value to validate.
        valid: Set of accepted values.

    Raises:
        ValueError: If *value* is not in *valid*.
    """
    if value not in valid:
        msg = f"Invalid {name}={value!r}. Must be one of: {sorted(valid)}"
        raise ValueError(msg)
