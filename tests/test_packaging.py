"""Guard that the plug-in entry points declared in pyproject.toml can install.

``pyproject.toml`` advertises ``examples.ruby_plugin`` and
``examples.hello_agent`` as entry points, but ``examples/`` was neither a
package nor listed under ``[tool.setuptools] packages``. Importing from the
repository root papered over it via namespace packages; the installed console
script, whose ``sys.path`` does not include the checkout, failed with
``No module named 'examples'`` on every invocation.
"""

from importlib.metadata import entry_points
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTRY_POINT_GROUPS = ("egg.runtimes", "egg.agents")


def _declared_entry_points():
    """Return the installed distribution's egg entry points."""
    eps = entry_points()
    found = []
    for group in ENTRY_POINT_GROUPS:
        if hasattr(eps, "select"):
            found.extend(eps.select(group=group))
        else:  # pragma: no cover - compatibility
            found.extend(eps.get(group, []))
    return found


def test_examples_is_a_real_package():
    """Namespace packages do not install; ``examples`` needs an __init__."""
    assert (REPO_ROOT / "examples" / "__init__.py").is_file()


def test_pyproject_ships_the_examples_package():
    """An entry point pointing at an unshipped package cannot resolve."""
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
        assert '"examples"' in pyproject
        return

    config = tomllib.loads(pyproject)
    packages = config["tool"]["setuptools"]["packages"]
    declared = set(config["project"].get("entry-points", {}).get("egg.runtimes", {}))
    assert declared, "expected at least one runtime entry point"
    assert "examples" in packages


def test_declared_entry_points_load():
    """Every advertised entry point must import and expose a callable."""
    eps = _declared_entry_points()
    if not eps:
        pytest.skip("egg-file-format is not installed; no entry points to check")
    for ep in eps:
        handler = ep.load()
        assert callable(handler), f"entry point {ep.name} is not callable"
