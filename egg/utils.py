from __future__ import annotations

"""Utility helpers used across the egg codebase."""

from pathlib import Path
import os
import shlex
import sys
import logging
from importlib.metadata import entry_points

__all__ = [
    "_is_relative_to",
    "get_lang_command",
    "DEFAULT_LANG_COMMANDS",
    "load_plugins",
]

logger = logging.getLogger(__name__)

AGENT_PLUGIN_GROUP = "egg.agents"
RUNTIME_PLUGIN_GROUP = "egg.runtimes"


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
        return shlex.split(override)
    return DEFAULT_LANG_COMMANDS.get(lang)


def load_plugins() -> None:
    """Discover and register runtime and agent plug-ins."""

    eps = entry_points()

    if hasattr(eps, "select"):
        runtime_eps = eps.select(group=RUNTIME_PLUGIN_GROUP)
        agent_eps = eps.select(group=AGENT_PLUGIN_GROUP)
    else:  # pragma: no cover - compatibility
        runtime_eps = eps.get(RUNTIME_PLUGIN_GROUP, [])
        agent_eps = eps.get(AGENT_PLUGIN_GROUP, [])

    for ep in runtime_eps:
        try:
            handler = ep.load()
            extra = handler()
            if isinstance(extra, dict):
                DEFAULT_LANG_COMMANDS.update(extra)
            logger.debug("[plugins] loaded runtime %s", ep.name)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed loading runtime plug-in %s: %s", ep.name, exc)

    for ep in agent_eps:
        try:
            ep.load()()
            logger.debug("[plugins] loaded agent %s", ep.name)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed loading agent plug-in %s: %s", ep.name, exc)
