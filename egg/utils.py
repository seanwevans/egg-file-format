from __future__ import annotations

"""Utility helpers used across the egg codebase."""

from pathlib import Path
import os
import sys

__all__ = ["_is_relative_to", "get_lang_command", "DEFAULT_LANG_COMMANDS"]


def _is_relative_to(path: Path, base: Path) -> bool:
    """Return True if *path* is relative to *base*.

    This provides a backport of ``Path.is_relative_to`` for Python 3.8.
    """
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


DEFAULT_LANG_COMMANDS = {
    "python": [sys.executable],
    "r": ["Rscript"],
    "bash": ["bash"],
}


def get_lang_command(lang: str) -> list[str] | None:
    """Return the command list for ``lang`` respecting environment overrides."""

    override = os.getenv(f"EGG_CMD_{lang.upper()}")
    if override:
        return [override]
    return DEFAULT_LANG_COMMANDS.get(lang)
