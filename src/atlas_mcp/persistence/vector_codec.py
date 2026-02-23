"""Custom asyncpg type codec for pgvector ``vector`` columns.

Registers encoder/decoder so asyncpg transparently converts between
Python ``list[float]`` and PostgreSQL ``vector`` values.

Usage::

    from atlas_mcp.persistence.vector_codec import register_vector_codec

    async with pool.acquire() as conn:
        await register_vector_codec(conn)
"""

from __future__ import annotations

import logging
import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)


def _encode_vector(vector: list[float]) -> bytes:
    """Encode a Python list of floats into pgvector binary format.

    The pgvector binary format is:
    - 2 bytes: dimension count (uint16)
    - 2 bytes: unused flags (uint16, always 0)
    - N * 4 bytes: float32 values

    Args:
        vector: A list of float values.

    Returns:
        The binary-encoded vector.
    """
    dim = len(vector)
    return struct.pack(f"<HH{dim}f", dim, 0, *vector)


def _decode_vector(data: bytes) -> list[float]:
    """Decode pgvector binary format into a Python list of floats.

    Args:
        data: The binary-encoded vector from PostgreSQL.

    Returns:
        A list of float values.
    """
    dim = struct.unpack_from("<H", data, 0)[0]
    return list(struct.unpack_from(f"<{dim}f", data, 4))


def _encode_vector_text(vector: list[float]) -> str:
    """Encode a Python list of floats into pgvector text format.

    Args:
        vector: A list of float values.

    Returns:
        The text-encoded vector (e.g. ``'[1.0,2.0,3.0]'``).
    """
    inner = ",".join(str(v) for v in vector)
    return f"[{inner}]"


def _decode_vector_text(data: str) -> list[float]:
    """Decode pgvector text format into a Python list of floats.

    Args:
        data: The text-encoded vector (e.g. ``'[1.0,2.0,3.0]'``).

    Returns:
        A list of float values.
    """
    return [float(v) for v in data.strip().strip("[]").split(",")]


async def register_vector_codec(conn: asyncpg.Connection[asyncpg.Record]) -> None:
    """Register the ``vector`` type codec on an asyncpg connection.

    This must be called once per connection (or once after pool creation)
    so that asyncpg can transparently convert between ``list[float]``
    and PostgreSQL ``vector`` columns.

    Args:
        conn: An active asyncpg connection.
    """
    await conn.set_type_codec(
        "vector",
        encoder=_encode_vector_text,
        decoder=_decode_vector_text,
        schema="public",
        format="text",
    )
    logger.debug("Registered pgvector text codec on connection.")
