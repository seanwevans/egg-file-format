"""Keep the README's language-support table in sync with the examples.

The README states which example manifests run on a stock install and which
need a runtime plug-in. These tests fail if that table drifts — either because
an example gained a language the built-in runtimes cannot execute, or because
a language listed as unsupported became available without the docs catching up.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from egg.manifest import load_manifest  # noqa: E402
from egg.utils import DEFAULT_LANG_COMMANDS  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

#: Languages the CLI runs with no plug-ins installed.
BUILTIN_LANGUAGES = {"python", "r", "bash"}

#: Manifests the README presents as runnable with a stock install.
STOCK_MANIFESTS = ("quickstart.yaml", "manifest.yaml", "advanced_manifest.yaml")

#: Manifests the README flags as requiring runtime plug-ins.
PLUGIN_MANIFESTS = ("julia_manifest.yaml", "dozen_manifest.yaml")


def _languages(name):
    manifest = load_manifest(EXAMPLES / name)
    return {cell.language.lower() for cell in manifest.cells}


def test_builtin_languages_are_registered():
    """The three languages the README calls built in must really be built in."""
    missing = BUILTIN_LANGUAGES - set(DEFAULT_LANG_COMMANDS)
    assert not missing, f"README claims these are built in: {sorted(missing)}"


def test_stock_manifests_only_use_builtin_languages():
    """A manifest documented as stock-runnable must not need a plug-in."""
    for name in STOCK_MANIFESTS:
        extra = _languages(name) - BUILTIN_LANGUAGES
        assert not extra, f"{name} needs plug-ins for {sorted(extra)}"


def test_plugin_manifests_still_need_plugins():
    """If these ever run unaided, the README table is stale and must change."""
    for name in PLUGIN_MANIFESTS:
        extra = _languages(name) - BUILTIN_LANGUAGES
        assert extra, f"{name} no longer needs plug-ins; update the README"
