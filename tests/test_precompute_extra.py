import os
import sys
from pathlib import Path
import subprocess
import shutil
import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from egg.utils import get_lang_command  # noqa: E402
from egg.precompute import precompute_cells  # noqa: E402
from egg.hashing import load_hashes, sha256_file  # noqa: E402
import egg_cli  # noqa: E402


def test_get_lang_command_env_override(monkeypatch):
    monkeypatch.setenv("EGG_CMD_BASH", "/custom/bash")
    assert get_lang_command("bash") == ["/custom/bash"]
    monkeypatch.delenv("EGG_CMD_BASH")
    assert get_lang_command("python")[0] == sys.executable


def test_get_lang_command_split(monkeypatch):
    monkeypatch.setenv("EGG_CMD_PYTHON", "python -u")
    assert get_lang_command("python") == ["python", "-u"]


def test_precompute_cells_success(monkeypatch, tmp_path: Path):
    src = tmp_path / "hello.py"
    src.write_text("print('hi')\n")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: hello.py
"""
    )

    calls = []

    def fake_run(cmd, stdout=None, **kwargs):
        calls.append(cmd)
        if stdout:
            stdout.write("output\n")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(shutil, "which", lambda c: c)
    monkeypatch.setattr(subprocess, "run", fake_run)

    outputs = precompute_cells(manifest)
    out_file = tmp_path / "hello.py.out"
    assert outputs == [out_file]
    assert out_file.read_text() == "output\n"
    assert calls[0][0] == sys.executable
    assert calls[0][1] == str(src)


def test_precompute_cells_errors(monkeypatch, tmp_path: Path):
    src = tmp_path / "hello.foo"
    src.write_text("hi\n")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: foo
    source: hello.foo
"""
    )
    monkeypatch.setattr(shutil, "which", lambda c: c)
    with pytest.raises(ValueError):
        precompute_cells(manifest)

    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: hello.foo
"""
    )
    monkeypatch.setattr(shutil, "which", lambda c: None)
    with pytest.raises(FileNotFoundError):
        precompute_cells(manifest)


def test_precompute_cells_subprocess_failure(monkeypatch, tmp_path: Path) -> None:
    src = tmp_path / "hello.py"
    src.write_text("print('hi')\n")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: hello.py
"""
    )

    def fake_run(cmd, stdout=None, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stderr="boom")

    monkeypatch.setattr(shutil, "which", lambda c: c)
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as exc:
        precompute_cells(manifest)
    msg = str(exc.value)
    assert str(src) in msg
    assert "boom" in msg


def _write_manifest(path: Path) -> Path:
    path.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: hello.py
"""
    )
    return path


def test_precompute_caches_results(monkeypatch, tmp_path: Path) -> None:
    src = tmp_path / "hello.py"
    src.write_text("print('hi')\n")
    manifest = _write_manifest(tmp_path / "manifest.yaml")

    calls: list[list[str]] = []

    def fake_run(cmd, stdout=None, **kwargs):
        calls.append(cmd)
        if stdout:
            stdout.write("out1\n")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(shutil, "which", lambda c: c)
    monkeypatch.setattr(subprocess, "run", fake_run)

    out_file = src.with_suffix(".py.out")
    cache = tmp_path / "precompute_hashes.yaml"

    precompute_cells(manifest)
    assert cache.is_file()
    first_hash = load_hashes(cache)["hello.py"]
    assert sha256_file(src) == first_hash
    calls.clear()

    precompute_cells(manifest)
    assert calls == []
    assert out_file.is_file()
    assert load_hashes(cache)["hello.py"] == first_hash


def test_precompute_cache_invalidated(monkeypatch, tmp_path: Path) -> None:
    src = tmp_path / "hello.py"
    src.write_text("print('hi')\n")
    manifest = _write_manifest(tmp_path / "manifest.yaml")

    monkeypatch.setattr(shutil, "which", lambda c: c)

    calls: list[list[str]] = []

    def fake_run(cmd, stdout=None, **kwargs):
        calls.append(cmd)
        if stdout:
            stdout.write("out\n")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    precompute_cells(manifest)
    calls.clear()

    src.write_text("print('changed')\n")
    precompute_cells(manifest)
    assert len(calls) == 1


def test_precompute_cells_passes_timeout(monkeypatch, tmp_path: Path) -> None:
    src = tmp_path / "hello.py"
    src.write_text("print('hi')\n")
    manifest = _write_manifest(tmp_path / "manifest.yaml")

    monkeypatch.setattr(shutil, "which", lambda c: c)

    def fake_run(cmd, stdout=None, **kwargs):
        assert kwargs.get("timeout") == 5.0
        if stdout:
            stdout.write("out\n")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    precompute_cells(manifest, timeout=5.0)


def test_precompute_cells_timeout_cleanup(monkeypatch, tmp_path: Path) -> None:
    src = tmp_path / "hello.py"
    src.write_text("print('hi')\n")
    manifest = _write_manifest(tmp_path / "manifest.yaml")

    monkeypatch.setattr(shutil, "which", lambda c: c)

    def fake_run(cmd, stdout=None, **kwargs):
        if stdout:
            stdout.write("partial")
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", fake_run)

    out_file = src.with_name(src.name + ".out")
    with pytest.raises(RuntimeError) as exc:
        precompute_cells(manifest, timeout=0.1)
    assert str(src) in str(exc.value)
    assert not out_file.exists()


def test_cli_precompute_timeout(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "demo.egg"
    called: list[float | None] = []

    def fake_precompute(path, timeout=None):
        called.append(timeout)

    monkeypatch.setattr(egg_cli, "precompute_cells", fake_precompute)
    monkeypatch.setattr(egg_cli, "verify_archive", lambda *a, **kw: True)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
            "--precompute",
            "--precompute-timeout",
            "7",
        ],
    )
    egg_cli.main()

    assert called == [7.0]
    assert output.is_file()
