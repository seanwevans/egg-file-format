"""Chunker agent for splitting files into deterministic segments.

This module exposes the :class:`Chunk` dataclass which captures metadata about
each file segment produced by :func:`chunk`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class Chunk:
    """Metadata describing a portion of a file.

    Attributes
    ----------
    offset:
        Byte offset from the start of the file where the chunk begins.
    size:
        Size of the chunk in bytes.
    """

    offset: int
    size: int


def chunk(path: Path | str, *, chunk_size: int = 1_048_576) -> List[Chunk]:
    """Divide ``path`` into ``chunk_size`` byte blocks.

    Parameters
    ----------
    path : Path | str
        File to chunk.
    chunk_size : int, optional
        Size of each chunk in bytes. Defaults to ``1_048_576`` (1 MiB).

    Returns
    -------
    List[Chunk]
        ``Chunk`` metadata for each segment in the order they appear in the
        file.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    file_path = Path(path)
    metadata: List[Chunk] = []
    offset = 0
    with open(file_path, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            size = len(data)
            metadata.append(Chunk(offset=offset, size=size))
            offset += size
    return metadata


__all__ = ["Chunk", "chunk"]
