"""Embedding providers for vectorization.

Defines the abstract :class:`EmbeddingProvider` interface and concrete
implementations for OpenAI API and Sentence Transformers (local).
A factory function :func:`create_embedding_provider` selects the
appropriate provider via configuration.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Supported embedding provider types."""

    OPENAI = "openai"
    SENTENCE_TRANSFORMER = "sentence_transformer"


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers.

    All providers must implement :meth:`embed` and :meth:`embed_batch`,
    and declare their output dimension via the :attr:`dimension` property.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of the embedding vectors produced."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            EmbeddingError: If the embedding request fails.
        """

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts.

        Args:
            texts: A list of input texts to embed.

        Returns:
            A list of embedding vectors, one per input text.

        Raises:
            EmbeddingError: If the embedding request fails.
        """


class EmbeddingError(Exception):
    """Raised when an embedding operation fails."""


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using the OpenAI API.

    Uses the ``text-embedding-3-small`` model by default (1536 dimensions).

    Args:
        api_key: OpenAI API key. Falls back to ``OPENAI_API_KEY`` env var.
        model: The embedding model name.
    """

    #: Default embedding model.
    DEFAULT_MODEL = "text-embedding-3-small"

    #: Dimension for ``text-embedding-3-small``.
    DEFAULT_DIMENSION = 1536

    #: Known model dimensions.
    _MODEL_DIMENSIONS: ClassVar[dict[str, int]] = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        """Initialize the OpenAI embedding provider.

        Args:
            api_key: OpenAI API key. If not provided, reads from
                the ``OPENAI_API_KEY`` environment variable.
            model: The embedding model to use.

        Raises:
            EmbeddingError: If no API key is found.
        """
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not resolved_key:
            msg = (
                "OpenAI API key required. Provide via 'api_key' parameter "
                "or set the OPENAI_API_KEY environment variable."
            )
            raise EmbeddingError(msg)

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            msg = "openai package is required: pip install openai"
            raise EmbeddingError(msg) from exc

        self._client = AsyncOpenAI(api_key=resolved_key)
        self._model = model
        self._dimension = self._MODEL_DIMENSIONS.get(model, self.DEFAULT_DIMENSION)
        logger.info(
            "OpenAI embedding provider initialized (model=%s, dim=%d)",
            model,
            self._dimension,
        )

    @property
    def dimension(self) -> int:
        """Return the dimension of the embedding vectors produced."""
        return self._dimension

    @property
    def model(self) -> str:
        """Return the model name."""
        return self._model

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            EmbeddingError: If the API call fails.
        """
        if not text or not text.strip():
            msg = "Cannot embed empty text"
            raise EmbeddingError(msg)

        try:
            response = await self._client.embeddings.create(
                input=[text],
                model=self._model,
            )
            return list(response.data[0].embedding)
        except Exception as exc:
            if isinstance(exc, EmbeddingError):
                raise
            msg = f"OpenAI embedding failed: {exc}"
            raise EmbeddingError(msg) from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts.

        Args:
            texts: A list of input texts to embed.

        Returns:
            A list of embedding vectors, one per input text.

        Raises:
            EmbeddingError: If the API call fails.
        """
        if not texts:
            return []

        for i, text in enumerate(texts):
            if not text or not text.strip():
                msg = f"Cannot embed empty text at index {i}"
                raise EmbeddingError(msg)

        try:
            response = await self._client.embeddings.create(
                input=texts,
                model=self._model,
            )
            # OpenAI returns embeddings in order of input
            sorted_data = sorted(response.data, key=lambda d: d.index)
            return [list(item.embedding) for item in sorted_data]
        except Exception as exc:
            if isinstance(exc, EmbeddingError):
                raise
            msg = f"OpenAI batch embedding failed: {exc}"
            raise EmbeddingError(msg) from exc


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using Sentence Transformers (local).

    Uses ``all-MiniLM-L6-v2`` by default (384 dimensions).
    Runs entirely locally without external API calls.

    Args:
        model_name: The Sentence Transformer model identifier.
    """

    #: Default local model.
    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        """Initialize the Sentence Transformer embedding provider.

        Args:
            model_name: The model to load from HuggingFace hub.

        Raises:
            EmbeddingError: If sentence-transformers is not installed.
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            msg = (
                "sentence-transformers package is required: pip install atlas-mcp[local-embeddings]"
            )
            raise EmbeddingError(msg) from exc

        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        raw_dim = self._model.get_sentence_embedding_dimension()
        if raw_dim is None:
            msg = f"Could not determine embedding dimension for model: {model_name}"
            raise EmbeddingError(msg)
        self._dimension = int(raw_dim)
        logger.info(
            "SentenceTransformer provider initialized (model=%s, dim=%d)",
            model_name,
            self._dimension,
        )

    @property
    def dimension(self) -> int:
        """Return the dimension of the embedding vectors produced."""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model_name

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            EmbeddingError: If encoding fails.
        """
        if not text or not text.strip():
            msg = "Cannot embed empty text"
            raise EmbeddingError(msg)

        try:
            embedding = self._model.encode(text, convert_to_numpy=True)
            return embedding.tolist()  # type: ignore[no-any-return]
        except Exception as exc:
            if isinstance(exc, EmbeddingError):
                raise
            msg = f"SentenceTransformer embedding failed: {exc}"
            raise EmbeddingError(msg) from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts.

        Args:
            texts: A list of input texts to embed.

        Returns:
            A list of embedding vectors, one per input text.

        Raises:
            EmbeddingError: If encoding fails.
        """
        if not texts:
            return []

        for i, text in enumerate(texts):
            if not text or not text.strip():
                msg = f"Cannot embed empty text at index {i}"
                raise EmbeddingError(msg)

        try:
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()  # type: ignore[no-any-return]
        except Exception as exc:
            if isinstance(exc, EmbeddingError):
                raise
            msg = f"SentenceTransformer batch embedding failed: {exc}"
            raise EmbeddingError(msg) from exc


def create_embedding_provider(
    provider_type: str | ProviderType | None = None,
    **kwargs: Any,
) -> EmbeddingProvider:
    """Factory to create an embedding provider by type.

    The provider type can be specified explicitly or read from the
    ``EMBEDDING_PROVIDER`` environment variable. Defaults to ``openai``.

    Args:
        provider_type: One of ``"openai"`` or ``"sentence_transformer"``,
            or a :class:`ProviderType` enum member. If ``None``, reads from
            the ``EMBEDDING_PROVIDER`` env var.
        **kwargs: Extra keyword arguments forwarded to the provider
            constructor (e.g. ``api_key``, ``model``).

    Returns:
        An initialized :class:`EmbeddingProvider` instance.

    Raises:
        ValueError: If the provider type is unknown.
        EmbeddingError: If provider initialization fails.
    """
    if provider_type is None:
        provider_type = os.environ.get("EMBEDDING_PROVIDER", "openai")

    if isinstance(provider_type, ProviderType):
        provider_type = provider_type.value

    provider_type = provider_type.lower().strip()

    if provider_type == ProviderType.OPENAI.value:
        return OpenAIEmbeddingProvider(**kwargs)

    if provider_type == ProviderType.SENTENCE_TRANSFORMER.value:
        return SentenceTransformerEmbeddingProvider(**kwargs)

    msg = (
        f"Unknown embedding provider: '{provider_type}'. "
        f"Supported: {[p.value for p in ProviderType]}"
    )
    raise ValueError(msg)
