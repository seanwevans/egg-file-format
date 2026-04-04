import pytest
import zipfile
from pathlib import Path
from egg.manifest import _normalize_source
from egg.composer import compose


def test_normalize_source_absolute(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _normalize_source("/abs.py", tmp_path)


def test_duplicate_runtime_dependency(tmp_path: Path) -> None:
    dep = tmp_path / "runtime" / "python.img"
    dep.parent.mkdir()
    dep.write_text("py")

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
  - runtime/python.img
  - runtime/python.img
"""
    )

    output = tmp_path / "demo.egg"
    with pytest.raises(ValueError):
        compose(manifest, output, dependencies=[dep, dep])


def test_runtime_dependency_preserves_relative_path(tmp_path: Path) -> None:
    nested = tmp_path / "runtimes" / "python" / "python.img"
    nested.parent.mkdir(parents=True)
    nested.write_text("py")

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
  - runtimes/python/python.img
"""
    )

    output = tmp_path / "demo.egg"
    compose(manifest, output, dependencies=[nested])

    with zipfile.ZipFile(output) as zf:
        assert "runtime/runtimes/python/python.img" in zf.namelist()


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


def test_string_runtime_dependency_included(tmp_path: Path) -> None:
    dep = tmp_path / "python.img"
    dep.write_text("py")

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
  - python.img
"""
    )

    output = tmp_path / "demo.egg"
    compose(manifest, output, dependencies=[str(dep)])

    with zipfile.ZipFile(output) as zf:
        assert "runtime/python.img" in zf.namelist()


def test_normalize_source_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _normalize_source("../evil.py", tmp_path)


def test_normalize_source_valid_relative(tmp_path: Path) -> None:
    normalized = _normalize_source("sub/../good.py", tmp_path)
    assert normalized == "good.py"


def test_compose_cleans_temp_archive_on_failure(tmp_path: Path, monkeypatch) -> None:
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

    output = tmp_path / "demo.egg"
    output.write_bytes(b"old archive bytes")

    original_writestr = zipfile.ZipFile.writestr

    def failing_writestr(self, *args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(zipfile.ZipFile, "writestr", failing_writestr)
    with pytest.raises(RuntimeError, match="boom"):
        compose(manifest, output)
    monkeypatch.setattr(zipfile.ZipFile, "writestr", original_writestr)

    assert output.read_bytes() == b"old archive bytes"
    assert not list(tmp_path.glob("*.tmp"))
