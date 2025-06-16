from __future__ import annotations

"""Utility helpers used across the egg codebase."""

from pathlib import Path


def _is_relative_to(path: Path, base: Path) -> bool:
    """Return True if *path* is relative to *base*.

    This provides a backport of ``Path.is_relative_to`` for Python 3.8.
    """
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False
