import os
import sys
from pathlib import Path
import logging
import zipfile
import subprocess
import shutil
import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import egg_cli  # noqa: E402
from egg.hashing import verify_archive  # noqa: E402

EXAMPLE_ADV_MANIFEST = (
    Path(__file__).resolve().parent.parent / "examples" / "advanced_manifest.yaml"
)

EXAMPLE_JULIA_MANIFEST = (
    Path(__file__).resolve().parent.parent / "examples" / "julia_manifest.yaml"
)


def test_build_advanced_manifest(monkeypatch, tmp_path, caplog):
    output = tmp_path / "advanced.egg"
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "--verbose",
            "build",
            "--manifest",
            str(EXAMPLE_ADV_MANIFEST),
            "--output",
            str(output),
        ],
    )
    monkeypatch.setattr(egg_cli, "fetch_runtime_blocks", lambda m: [])
    with pytest.raises(ValueError):
        egg_cli.main()

    assert output.is_file()
    assert verify_archive(output)
    with zipfile.ZipFile(output) as zf:
        names = zf.namelist()
    assert "manifest.yaml" in names
    assert "advanced_manifest.yaml" not in names


def test_build_julia_manifest(monkeypatch, tmp_path, caplog):
    output = tmp_path / "julia.egg"
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "--verbose",
            "build",
            "--manifest",
            str(EXAMPLE_JULIA_MANIFEST),
            "--output",
            str(output),
        ],
    )
    egg_cli.main()

    assert output.is_file()
    assert verify_archive(output)


def test_hatch_custom_manifest_name(monkeypatch, tmp_path, caplog):
    script = tmp_path / "hello.py"
    script.write_text("print('hi')\n")

    manifest = tmp_path / "custom.yaml"
    manifest.write_text(
        """
name: Demo
description: desc
cells:
  - language: python
    source: hello.py
"""
    )
    egg_path = tmp_path / "demo.egg"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            str(manifest),
            "--output",
            str(egg_path),
        ],
    )
    egg_cli.main()

    with zipfile.ZipFile(egg_path) as zf:
        assert "manifest.yaml" in zf.namelist()
        assert "custom.yaml" not in zf.namelist()

    calls: list[list[str]] = []

    def fake_run(cmd, check=True):
        calls.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda cmd: cmd)
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        ["egg_cli.py", "--verbose", "hatch", "--egg", str(egg_path)],
    )
    egg_cli.main()

    assert any(
        cmd[0] == sys.executable and cmd[1].endswith("hello.py") for cmd in calls
    )
    assert f"[hatch] Completed running {egg_path}" in caplog.text
