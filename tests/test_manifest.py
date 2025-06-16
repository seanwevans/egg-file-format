import os
import sys
from pathlib import Path

import pytest

# Ensure the repository root is on the path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from egg.manifest import Cell, Manifest, load_manifest  # noqa: E402

EXAMPLE_MANIFEST = Path(__file__).resolve().parent.parent / "examples" / "manifest.yaml"


def test_load_manifest_example():
    manifest = load_manifest(EXAMPLE_MANIFEST)
    assert isinstance(manifest, Manifest)
    assert manifest.name == "Demo Notebook"
    assert manifest.description == "Simple two-language example"
    assert manifest.cells == [
        Cell(language="python", source="hello.py"),
        Cell(language="r", source="hello.R"),
    ]


def test_missing_required_field(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        """
name: Example
cells:
  - language: python
    source: hello.py
"""
    )  # description missing
    with pytest.raises(ValueError):
        load_manifest(path)


def test_cell_missing_keys(tmp_path: Path):
    path = tmp_path / "bad_cell.yaml"
    path.write_text(
        """
name: Example
description: desc
cells:
  - language: python
"""
    )  # source missing in cell
    with pytest.raises(ValueError):
        load_manifest(path)


def test_invalid_name_type(tmp_path: Path):
    path = tmp_path / "bad_name.yaml"
    path.write_text(
        """
name:
  - not a string
description: desc
cells:
  - language: python
    source: hello.py
"""
    )
    with pytest.raises(ValueError):
        load_manifest(path)


def test_invalid_description_type(tmp_path: Path):
    path = tmp_path / "bad_desc.yaml"
    path.write_text(
        """
name: Example
description:
  key: value
cells:
  - language: python
    source: hello.py
"""
    )
    with pytest.raises(ValueError):
        load_manifest(path)


def test_invalid_cell_language_type(tmp_path: Path):
    path = tmp_path / "bad_cell_lang.yaml"
    path.write_text(
        """
name: Example
description: desc
cells:
  - language: [python]
    source: hello.py
"""
    )
    with pytest.raises(ValueError):
        load_manifest(path)


def test_invalid_cell_source_type(tmp_path: Path):
    path = tmp_path / "bad_cell_source.yaml"
    path.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source:
      - hello.py
"""
    )
    with pytest.raises(ValueError):
        load_manifest(path)


def test_unknown_root_field(tmp_path: Path) -> None:
    path = tmp_path / "extra.yaml"
    path.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: hello.py
extra: value
"""
    )
    with pytest.raises(ValueError):
        load_manifest(path)
