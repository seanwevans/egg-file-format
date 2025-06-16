import os
import sys
from pathlib import Path
import subprocess
import shutil
import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from egg.utils import get_lang_command  # noqa: E402
from egg.precompute import precompute_cells  # noqa: E402


def test_get_lang_command_env_override(monkeypatch):
    monkeypatch.setenv("EGG_CMD_BASH", "/custom/bash")
    assert get_lang_command("bash") == ["/custom/bash"]
    monkeypatch.delenv("EGG_CMD_BASH")
    assert get_lang_command("python")[0] == sys.executable


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

    def fake_run(cmd, check=True, stdout=None):
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
