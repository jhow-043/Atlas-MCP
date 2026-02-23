"""Tests for the EmbeddingProvider module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from atlas_mcp.vectorization.embeddings import (
    EmbeddingError,
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    ProviderType,
    SentenceTransformerEmbeddingProvider,
    create_embedding_provider,
)

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def _make_openai_embedding_response(
    vectors: list[list[float]],
) -> Any:
    """Build a mock OpenAI embeddings response object."""
    data = []
    for idx, vec in enumerate(vectors):
        item = MagicMock()
        item.index = idx
        item.embedding = vec
        data.append(item)
    response = MagicMock()
    response.data = data
    return response


@pytest.fixture()
def _env_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set a fake OPENAI_API_KEY in the environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-key")


@pytest.fixture()
def _no_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove OPENAI_API_KEY from the environment."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


# ---------------------------------------------------------------------------
# ProviderType enum
# ---------------------------------------------------------------------------


class TestProviderType:
    """Tests for the ProviderType enum."""

    def test_should_have_openai_value(self) -> None:
        assert ProviderType.OPENAI.value == "openai"

    def test_should_have_sentence_transformer_value(self) -> None:
        assert ProviderType.SENTENCE_TRANSFORMER.value == "sentence_transformer"


# ---------------------------------------------------------------------------
# EmbeddingProvider ABC
# ---------------------------------------------------------------------------


class TestEmbeddingProviderABC:
    """Tests for the abstract EmbeddingProvider interface."""

    def test_should_not_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            EmbeddingProvider()  # type: ignore[abstract]

    def test_should_require_dimension(self) -> None:
        """Validate that dimension is an abstract property."""
        assert hasattr(EmbeddingProvider, "dimension")

    def test_should_require_embed(self) -> None:
        """Validate that embed is an abstract method."""
        assert hasattr(EmbeddingProvider, "embed")

    def test_should_require_embed_batch(self) -> None:
        """Validate that embed_batch is an abstract method."""
        assert hasattr(EmbeddingProvider, "embed_batch")


# ---------------------------------------------------------------------------
# OpenAIEmbeddingProvider
# ---------------------------------------------------------------------------


class TestOpenAIEmbeddingProvider:
    """Tests for OpenAIEmbeddingProvider."""

    @pytest.mark.usefixtures("_env_openai_key")
    def test_should_initialize_with_env_key(self) -> None:
        provider = OpenAIEmbeddingProvider()
        assert provider.dimension == 1536
        assert provider.model == "text-embedding-3-small"

    def test_should_initialize_with_explicit_key(self) -> None:
        provider = OpenAIEmbeddingProvider(api_key="sk-explicit")
        assert provider.dimension == 1536

    @pytest.mark.usefixtures("_no_openai_key")
    def test_should_raise_without_api_key(self) -> None:
        with pytest.raises(EmbeddingError, match="API key required"):
            OpenAIEmbeddingProvider()

    @pytest.mark.usefixtures("_env_openai_key")
    def test_should_use_custom_model(self) -> None:
        provider = OpenAIEmbeddingProvider(model="text-embedding-3-large")
        assert provider.dimension == 3072
        assert provider.model == "text-embedding-3-large"

    @pytest.mark.usefixtures("_env_openai_key")
    def test_should_fallback_dimension_for_unknown_model(self) -> None:
        provider = OpenAIEmbeddingProvider(model="custom-model-v1")
        assert provider.dimension == 1536  # DEFAULT_DIMENSION fallback

    @pytest.mark.usefixtures("_env_openai_key")
    async def test_should_embed_single_text(self) -> None:
        provider = OpenAIEmbeddingProvider()
        fake_vector = [0.1, 0.2, 0.3]
        mock_response = _make_openai_embedding_response([fake_vector])
        provider._client.embeddings.create = AsyncMock(return_value=mock_response)

        result = await provider.embed("hello world")

        assert result == fake_vector
        provider._client.embeddings.create.assert_awaited_once_with(
            input=["hello world"],
            model="text-embedding-3-small",
        )

    @pytest.mark.usefixtures("_env_openai_key")
    async def test_should_raise_on_empty_text(self) -> None:
        provider = OpenAIEmbeddingProvider()
        with pytest.raises(EmbeddingError, match="Cannot embed empty text"):
            await provider.embed("")

    @pytest.mark.usefixtures("_env_openai_key")
    async def test_should_raise_on_whitespace_only_text(self) -> None:
        provider = OpenAIEmbeddingProvider()
        with pytest.raises(EmbeddingError, match="Cannot embed empty text"):
            await provider.embed("   ")

    @pytest.mark.usefixtures("_env_openai_key")
    async def test_should_embed_batch(self) -> None:
        provider = OpenAIEmbeddingProvider()
        vectors = [[0.1, 0.2], [0.3, 0.4]]
        mock_response = _make_openai_embedding_response(vectors)
        provider._client.embeddings.create = AsyncMock(return_value=mock_response)

        result = await provider.embed_batch(["text1", "text2"])

        assert result == vectors
        provider._client.embeddings.create.assert_awaited_once_with(
            input=["text1", "text2"],
            model="text-embedding-3-small",
        )

    @pytest.mark.usefixtures("_env_openai_key")
    async def test_should_return_empty_for_empty_batch(self) -> None:
        provider = OpenAIEmbeddingProvider()
        result = await provider.embed_batch([])
        assert result == []

    @pytest.mark.usefixtures("_env_openai_key")
    async def test_should_raise_on_empty_text_in_batch(self) -> None:
        provider = OpenAIEmbeddingProvider()
        with pytest.raises(EmbeddingError, match="Cannot embed empty text at index 1"):
            await provider.embed_batch(["valid", ""])

    @pytest.mark.usefixtures("_env_openai_key")
    async def test_should_wrap_api_error(self) -> None:
        provider = OpenAIEmbeddingProvider()
        provider._client.embeddings.create = AsyncMock(
            side_effect=RuntimeError("API timeout"),
        )
        with pytest.raises(EmbeddingError, match="OpenAI embedding failed"):
            await provider.embed("test")

    @pytest.mark.usefixtures("_env_openai_key")
    async def test_should_wrap_batch_api_error(self) -> None:
        provider = OpenAIEmbeddingProvider()
        provider._client.embeddings.create = AsyncMock(
            side_effect=RuntimeError("rate limited"),
        )
        with pytest.raises(EmbeddingError, match="OpenAI batch embedding failed"):
            await provider.embed_batch(["a", "b"])

    @pytest.mark.usefixtures("_env_openai_key")
    async def test_should_sort_batch_by_index(self) -> None:
        """Validate that batch results are sorted by index even if API returns unordered."""
        provider = OpenAIEmbeddingProvider()
        # Simulate out-of-order response data
        item0 = MagicMock()
        item0.index = 1
        item0.embedding = [0.3, 0.4]
        item1 = MagicMock()
        item1.index = 0
        item1.embedding = [0.1, 0.2]
        response = MagicMock()
        response.data = [item0, item1]
        provider._client.embeddings.create = AsyncMock(return_value=response)

        result = await provider.embed_batch(["first", "second"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]


# ---------------------------------------------------------------------------
# SentenceTransformerEmbeddingProvider
# ---------------------------------------------------------------------------


class TestSentenceTransformerEmbeddingProvider:
    """Tests for SentenceTransformerEmbeddingProvider."""

    def test_should_initialize_with_mock_model(self) -> None:
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384

        with patch(
            "atlas_mcp.vectorization.embeddings.SentenceTransformerEmbeddingProvider.__init__",
            return_value=None,
        ):
            provider = SentenceTransformerEmbeddingProvider.__new__(
                SentenceTransformerEmbeddingProvider,
            )
            provider._model_name = "all-MiniLM-L6-v2"
            provider._model = mock_model
            provider._dimension = 384

        assert provider.dimension == 384
        assert provider.model_name == "all-MiniLM-L6-v2"

    def test_should_raise_when_package_not_installed(self) -> None:
        with (
            patch.dict("sys.modules", {"sentence_transformers": None}),
            pytest.raises(EmbeddingError, match="sentence-transformers package is required"),
        ):
            SentenceTransformerEmbeddingProvider()

    async def test_should_embed_single_text(self) -> None:
        import numpy as np

        mock_model = MagicMock()
        fake_embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        mock_model.encode.return_value = fake_embedding

        provider = SentenceTransformerEmbeddingProvider.__new__(
            SentenceTransformerEmbeddingProvider,
        )
        provider._model_name = "test-model"
        provider._model = mock_model
        provider._dimension = 3

        result = await provider.embed("hello")

        assert len(result) == 3
        assert abs(result[0] - 0.1) < 1e-5
        mock_model.encode.assert_called_once_with("hello", convert_to_numpy=True)

    async def test_should_raise_on_empty_text(self) -> None:
        provider = SentenceTransformerEmbeddingProvider.__new__(
            SentenceTransformerEmbeddingProvider,
        )
        provider._model_name = "test"
        provider._model = MagicMock()
        provider._dimension = 3

        with pytest.raises(EmbeddingError, match="Cannot embed empty text"):
            await provider.embed("")

    async def test_should_embed_batch(self) -> None:
        import numpy as np

        mock_model = MagicMock()
        fake_embeddings = np.array(
            [[0.1, 0.2], [0.3, 0.4]],
            dtype=np.float32,
        )
        mock_model.encode.return_value = fake_embeddings

        provider = SentenceTransformerEmbeddingProvider.__new__(
            SentenceTransformerEmbeddingProvider,
        )
        provider._model_name = "test"
        provider._model = mock_model
        provider._dimension = 2

        result = await provider.embed_batch(["a", "b"])

        assert len(result) == 2
        assert len(result[0]) == 2
        mock_model.encode.assert_called_once_with(["a", "b"], convert_to_numpy=True)

    async def test_should_return_empty_for_empty_batch(self) -> None:
        provider = SentenceTransformerEmbeddingProvider.__new__(
            SentenceTransformerEmbeddingProvider,
        )
        provider._model_name = "test"
        provider._model = MagicMock()
        provider._dimension = 2

        result = await provider.embed_batch([])
        assert result == []

    async def test_should_raise_on_empty_text_in_batch(self) -> None:
        provider = SentenceTransformerEmbeddingProvider.__new__(
            SentenceTransformerEmbeddingProvider,
        )
        provider._model_name = "test"
        provider._model = MagicMock()
        provider._dimension = 2

        with pytest.raises(EmbeddingError, match="Cannot embed empty text at index 0"):
            await provider.embed_batch(["", "valid"])

    async def test_should_wrap_encode_error(self) -> None:
        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("GPU out of memory")

        provider = SentenceTransformerEmbeddingProvider.__new__(
            SentenceTransformerEmbeddingProvider,
        )
        provider._model_name = "test"
        provider._model = mock_model
        provider._dimension = 2

        with pytest.raises(EmbeddingError, match="SentenceTransformer embedding failed"):
            await provider.embed("test")


# ---------------------------------------------------------------------------
# create_embedding_provider factory
# ---------------------------------------------------------------------------


class TestCreateEmbeddingProvider:
    """Tests for the create_embedding_provider factory."""

    @pytest.mark.usefixtures("_env_openai_key")
    def test_should_create_openai_provider_by_string(self) -> None:
        provider = create_embedding_provider("openai")
        assert isinstance(provider, OpenAIEmbeddingProvider)

    @pytest.mark.usefixtures("_env_openai_key")
    def test_should_create_openai_provider_by_enum(self) -> None:
        provider = create_embedding_provider(ProviderType.OPENAI)
        assert isinstance(provider, OpenAIEmbeddingProvider)

    @pytest.mark.usefixtures("_env_openai_key")
    def test_should_pass_kwargs_to_openai(self) -> None:
        provider = create_embedding_provider(
            "openai",
            model="text-embedding-3-large",
        )
        assert isinstance(provider, OpenAIEmbeddingProvider)
        assert provider.model == "text-embedding-3-large"

    def test_should_create_sentence_transformer_provider(self) -> None:
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384

        with patch(
            "atlas_mcp.vectorization.embeddings.SentenceTransformerEmbeddingProvider.__init__",
            return_value=None,
        ) as mock_init:
            provider = create_embedding_provider("sentence_transformer")
            mock_init.assert_called_once()
            assert isinstance(provider, SentenceTransformerEmbeddingProvider)

    @pytest.mark.usefixtures("_env_openai_key")
    def test_should_default_to_openai_from_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
        provider = create_embedding_provider()
        assert isinstance(provider, OpenAIEmbeddingProvider)

    @pytest.mark.usefixtures("_env_openai_key")
    def test_should_read_provider_from_env_var(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
        provider = create_embedding_provider()
        assert isinstance(provider, OpenAIEmbeddingProvider)

    def test_should_raise_on_unknown_provider(self) -> None:
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            create_embedding_provider("cohere")

    @pytest.mark.usefixtures("_env_openai_key")
    def test_should_be_case_insensitive(self) -> None:
        provider = create_embedding_provider("OPENAI")
        assert isinstance(provider, OpenAIEmbeddingProvider)

    @pytest.mark.usefixtures("_env_openai_key")
    def test_should_strip_whitespace(self) -> None:
        provider = create_embedding_provider("  openai  ")
        assert isinstance(provider, OpenAIEmbeddingProvider)
