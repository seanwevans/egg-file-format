"""Common helpers for path validation, command resolution, and plug-in loading.

Provides ``_is_relative_to`` for safe path checks, ``get_lang_command`` for
determining runtime commands, and ``load_plugins`` to discover plug-ins.
"""

from __future__ import annotations

from pathlib import Path
import os
import shlex
import sys
import logging
from importlib.metadata import entry_points

__all__ = [
    "_is_relative_to",
    "validate_lang_command",
    "get_lang_command",
    "DEFAULT_LANG_COMMANDS",
    "load_plugins",
]

logger = logging.getLogger(__name__)

AGENT_PLUGIN_GROUP = "egg.agents"
RUNTIME_PLUGIN_GROUP = "egg.runtimes"

LOADED_RUNTIME_PLUGINS: set[str] = set()
LOADED_AGENT_PLUGINS: set[str] = set()


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


def validate_lang_command(cmd: object, lang: str) -> list[str]:
    """Validate and return a runtime command for ``lang``.

    ``cmd`` must be a non-empty list of non-empty strings, and the executable
    entry (index 0) must not be whitespace-only.
    """

    if not isinstance(cmd, list) or not cmd:
        raise ValueError(
            f"Invalid command for '{lang}': expected a non-empty list of strings"
        )
    if not all(isinstance(part, str) and part != "" for part in cmd):
        raise ValueError(
            f"Invalid command for '{lang}': expected a non-empty list of non-empty strings"
        )
    if cmd[0].strip() == "":
        raise ValueError(
            f"Invalid command for '{lang}': executable entry cannot be whitespace-only"
        )
    return cmd


def get_lang_command(lang: str) -> list[str] | None:
    """Return the command list for ``lang`` respecting environment overrides."""

    override = os.getenv(f"EGG_CMD_{lang.upper()}")
    if override:
        return validate_lang_command(
            shlex.split(override),
            f"{lang} (from EGG_CMD_{lang.upper()})",
        )
    cmd = DEFAULT_LANG_COMMANDS.get(lang)
    if cmd is None:
        return None
    return validate_lang_command(cmd, lang)


def load_plugins() -> None:
    """Discover and register runtime and agent plug-ins.

    Subsequent calls are idempotent; plug-ins are only loaded once.
    """

    eps = entry_points()

    if hasattr(eps, "select"):
        runtime_eps = list(eps.select(group=RUNTIME_PLUGIN_GROUP))
        agent_eps = list(eps.select(group=AGENT_PLUGIN_GROUP))
    else:  # pragma: no cover - compatibility
        runtime_eps = list(eps.get(RUNTIME_PLUGIN_GROUP, []))
        agent_eps = list(eps.get(AGENT_PLUGIN_GROUP, []))

    for ep in runtime_eps:
        if ep.name in LOADED_RUNTIME_PLUGINS:
            logger.debug("[plugins] runtime %s already loaded", ep.name)
            continue
        try:
            handler = ep.load()
            extra = handler()
            if not isinstance(extra, dict):
                logger.warning(
                    "Runtime plug-in %s returned non-mapping %r", ep.name, type(extra)
                )
            else:
                for lang, cmd in extra.items():
                    if not isinstance(lang, str):
                        raise ValueError(
                            f"Runtime plug-in '{ep.name}' returned non-string language key: {lang!r}"
                        )
                    validated = validate_lang_command(
                        cmd,
                        f"{lang} (from runtime plug-in '{ep.name}')",
                    )
                    DEFAULT_LANG_COMMANDS[lang] = validated
            LOADED_RUNTIME_PLUGINS.add(ep.name)
            logger.debug("[plugins] loaded runtime %s", ep.name)
        except ValueError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed loading runtime plug-in %s: %s", ep.name, exc)

    for ep in agent_eps:
        if ep.name in LOADED_AGENT_PLUGINS:
            logger.debug("[plugins] agent %s already loaded", ep.name)
            continue
        try:
            ep.load()()
            LOADED_AGENT_PLUGINS.add(ep.name)
            logger.debug("[plugins] loaded agent %s", ep.name)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed loading agent plug-in %s: %s", ep.name, exc)

    if "ruby" not in DEFAULT_LANG_COMMANDS:
        try:  # pragma: no cover - fallback when package not installed
            from examples import ruby_plugin
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.debug("[plugins] example runtime unavailable: %s", exc)
        else:
            extra = ruby_plugin.register()
            if isinstance(extra, dict):
                for lang, cmd in extra.items():
                    if isinstance(lang, str):
                        DEFAULT_LANG_COMMANDS[lang] = validate_lang_command(
                            cmd,
                            f"{lang} (from examples.ruby_plugin)",
                        )
