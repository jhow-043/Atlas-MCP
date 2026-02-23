"""Tests for the vector_codec module."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from atlas_mcp.persistence.vector_codec import (
    _decode_vector_text,
    _encode_vector_text,
    register_vector_codec,
)


class TestEncodeVectorText:
    """Tests for _encode_vector_text."""

    def test_should_encode_simple_vector(self) -> None:
        """Validate encoding of a simple float list."""
        result = _encode_vector_text([1.0, 2.0, 3.0])
        assert result == "[1.0,2.0,3.0]"

    def test_should_encode_empty_vector(self) -> None:
        """Validate encoding of an empty list."""
        result = _encode_vector_text([])
        assert result == "[]"

    def test_should_encode_single_element(self) -> None:
        """Validate encoding of a single element."""
        result = _encode_vector_text([0.5])
        assert result == "[0.5]"

    def test_should_encode_negative_values(self) -> None:
        """Validate encoding of negative floats."""
        result = _encode_vector_text([-1.0, 0.0, 1.0])
        assert result == "[-1.0,0.0,1.0]"

    def test_should_encode_high_precision(self) -> None:
        """Validate encoding preserves precision."""
        result = _encode_vector_text([0.123456789])
        assert "0.123456789" in result


class TestDecodeVectorText:
    """Tests for _decode_vector_text."""

    def test_should_decode_simple_vector(self) -> None:
        """Validate decoding of a simple vector string."""
        result = _decode_vector_text("[1.0,2.0,3.0]")
        assert result == [1.0, 2.0, 3.0]

    def test_should_decode_single_element(self) -> None:
        """Validate decoding of a single element."""
        result = _decode_vector_text("[0.5]")
        assert result == [0.5]

    def test_should_decode_negative_values(self) -> None:
        """Validate decoding of negative floats."""
        result = _decode_vector_text("[-1.0,0.0,1.0]")
        assert result == [-1.0, 0.0, 1.0]

    def test_should_handle_whitespace(self) -> None:
        """Validate decoding handles surrounding whitespace."""
        result = _decode_vector_text(" [1.0,2.0] ")
        assert result == [1.0, 2.0]


class TestRoundTrip:
    """Tests for encode/decode round trip."""

    def test_should_roundtrip_simple(self) -> None:
        """Validate encode then decode produces original values."""
        original = [0.1, 0.2, 0.3, 0.4, 0.5]
        encoded = _encode_vector_text(original)
        decoded = _decode_vector_text(encoded)
        assert len(decoded) == len(original)
        for orig, dec in zip(original, decoded, strict=True):
            assert abs(orig - dec) < 1e-9

    def test_should_roundtrip_large_vector(self) -> None:
        """Validate round trip with a larger vector."""
        original = [float(i) / 100.0 for i in range(384)]
        encoded = _encode_vector_text(original)
        decoded = _decode_vector_text(encoded)
        assert len(decoded) == 384


class TestRegisterVectorCodec:
    """Tests for register_vector_codec."""

    async def test_should_call_set_type_codec(self) -> None:
        """Validate that set_type_codec is called with correct args."""
        mock_conn = AsyncMock()
        await register_vector_codec(mock_conn)
        mock_conn.set_type_codec.assert_awaited_once_with(
            "vector",
            encoder=_encode_vector_text,
            decoder=_decode_vector_text,
            schema="public",
            format="text",
        )

    async def test_should_not_raise_on_success(self) -> None:
        """Validate no exception on successful registration."""
        mock_conn = AsyncMock()
        await register_vector_codec(mock_conn)

    async def test_should_propagate_error(self) -> None:
        """Validate that errors from set_type_codec propagate."""
        mock_conn = AsyncMock()
        mock_conn.set_type_codec.side_effect = RuntimeError("codec error")
        with pytest.raises(RuntimeError, match="codec error"):
            await register_vector_codec(mock_conn)
