import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from egg.runtime_fetcher import fetch_runtime_blocks  # noqa: E402


def base_manifest(tmpdir: Path, deps: str) -> Path:
    manifest = tmpdir / "manifest.yaml"
    manifest.write_text(
        f"""
name: ex
description: d
cells: []
dependencies:{deps}
"""
    )
    return manifest


def test_fetch_none_deps(tmp_path: Path) -> None:
    manifest = base_manifest(tmp_path, " null")
    assert fetch_runtime_blocks(manifest) == []


def test_fetch_nonlist(tmp_path: Path) -> None:
    manifest = base_manifest(tmp_path, " 'a'")
    with pytest.raises(ValueError):
        fetch_runtime_blocks(manifest)


def test_fetch_nonstring_entry(tmp_path: Path) -> None:
    manifest = base_manifest(tmp_path, "\n  - 1")
    with pytest.raises(ValueError):
        fetch_runtime_blocks(manifest)


def test_fetch_absolute_path(tmp_path: Path) -> None:
    manifest = base_manifest(tmp_path, f"\n  - {Path('/abs.img')}")
    with pytest.raises(ValueError):
        fetch_runtime_blocks(manifest)


def test_fetch_escaped_path(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    manifest = base_manifest(tmp_path, "\n  - ../escape.img")
    with pytest.raises(ValueError):
        fetch_runtime_blocks(manifest)


def test_manifest_root_not_mapping(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("- just a list\n")
    with pytest.raises(ValueError, match="Manifest root must be a mapping"):
        fetch_runtime_blocks(manifest)
