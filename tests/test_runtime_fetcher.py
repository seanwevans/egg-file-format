import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from egg.runtime_fetcher import fetch_runtime_blocks  # noqa: E402


def test_fetch_local_dependencies(tmp_path: Path) -> None:
    dep1 = tmp_path / "python.img"
    dep2 = tmp_path / "r.img"
    dep1.write_text("py")
    dep2.write_text("r")
    (tmp_path / "code.py").write_text("print('hi')\n")

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        f"""
name: Example
description: desc
cells:
  - language: python
    source: code.py
dependencies:
  - {dep1.name}
  - {dep2.name}
"""
    )

    paths = fetch_runtime_blocks(manifest)
    assert paths == [dep1.resolve(), dep2.resolve()]


def test_missing_dependency(tmp_path: Path) -> None:
    (tmp_path / "code.py").write_text("print('hi')\n")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: code.py
dependencies:
  - missing.img
"""
    )

    with pytest.raises(FileNotFoundError):
        fetch_runtime_blocks(manifest)


def test_container_dependencies(tmp_path: Path) -> None:
    """Container-style specs should be returned without file checks."""
    (tmp_path / "code.py").write_text("print('hi')\n")

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: code.py
dependencies:
  - python:3.11
  - r:4.3
"""
    )

    paths = fetch_runtime_blocks(manifest)
    assert paths == ["python:3.11", "r:4.3"]
