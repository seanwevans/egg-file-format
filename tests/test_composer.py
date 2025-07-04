import pytest
from pathlib import Path
from egg.manifest import _normalize_source
from egg.composer import compose


def test_normalize_source_absolute(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _normalize_source("/abs.py", tmp_path)


def test_duplicate_runtime_dependency(tmp_path: Path) -> None:
    dep1 = tmp_path / "a" / "python.img"
    dep2 = tmp_path / "b" / "python.img"
    dep1.parent.mkdir()
    dep2.parent.mkdir()
    dep1.write_text("py")
    dep2.write_text("py")

    src = tmp_path / "code.py"
    src.write_text("print('hi')\n")

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: code.py
dependencies:
  - a/python.img
  - b/python.img
"""
    )

    output = tmp_path / "demo.egg"
    with pytest.raises(ValueError):
        compose(manifest, output, dependencies=[dep1, dep2])


def test_compose_creates_output_dir(tmp_path: Path) -> None:
    src = tmp_path / "code.py"
    src.write_text("print('hi')\n")

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: code.py
"""
    )

    output = tmp_path / "new" / "demo.egg"
    compose(manifest, output)
    assert output.is_file()


def test_normalize_source_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _normalize_source("../evil.py", tmp_path)


def test_normalize_source_valid_relative(tmp_path: Path) -> None:
    normalized = _normalize_source("sub/../good.py", tmp_path)
    assert normalized == "good.py"
