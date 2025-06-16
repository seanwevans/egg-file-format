"""Utility functions for hashing files in an egg archive."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Iterable

import yaml


_CHUNK_SIZE = 8192


def sha256_file(path: Path) -> str:
    """Return SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_hashes(files: Iterable[Path]) -> Dict[str, str]:
    """Compute SHA256 hashes for an iterable of files.

    The resulting mapping uses each file's name as the key.

    Raises:
        ValueError: If duplicate basenames are encountered.
    """
    hashes: Dict[str, str] = {}
    for f in files:
        path = Path(f)
        name = path.name
        if name in hashes:
            raise ValueError(f"Duplicate file basename: {name}")
        hashes[name] = sha256_file(path)
    return hashes


def write_hashes_file(hashes: Dict[str, str], path: Path) -> None:
    """Write a mapping of file hashes to ``path`` as YAML."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(hashes, f)


def load_hashes(path: Path) -> Dict[str, str]:
    """Load a YAML file of hashes."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def verify_hashes(directory: Path, hashes: Dict[str, str]) -> bool:
    """Verify that files in ``directory`` match expected ``hashes``."""
    for name, expected in hashes.items():
        calc = sha256_file(directory / name)
        if calc != expected:
            return False
    return True
