"""Chunker agent for splitting files into deterministic segments."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List


def chunk(path: Path | str, *, chunk_size: int = 1_048_576) -> List[Dict[str, int]]:
    """Divide ``path`` into ``chunk_size`` byte blocks.

    Parameters
    ----------
    path : Path | str
        File to chunk.
    chunk_size : int, optional
        Size of each chunk in bytes. Defaults to ``1_048_576`` (1 MiB).

    Returns
    -------
    List[Dict[str, int]]
        List of ``{"offset": int, "size": int}`` metadata for each chunk in the
        order they appear in the file.
    """

    file_path = Path(path)
    metadata: List[Dict[str, int]] = []
    offset = 0
    with open(file_path, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            size = len(data)
            metadata.append({"offset": offset, "size": size})
            offset += size
    return metadata
