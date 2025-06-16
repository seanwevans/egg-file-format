import os
import sys
import zipfile
import hashlib
import yaml
import pytest
import logging
import subprocess

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
import egg_cli  # noqa: E402


def test_build(monkeypatch, tmp_path, caplog):
    output = tmp_path / "demo.egg"
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "--verbose",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
        ],
    )
    egg_cli.main()

    expected = (
        f"[build] Building egg from {os.path.join('examples', 'manifest.yaml')} "
        f"-> {output} (placeholder)"
    )
    assert expected in caplog.text

    assert output.is_file()
    with zipfile.ZipFile(output) as zf:
        names = zf.namelist()
    assert "hello.py" in names
    assert "hello.R" in names


def test_hatch(monkeypatch, tmp_path, caplog):
    egg_path = tmp_path / "demo.egg"

    # build an egg first
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(egg_path),
        ],
    )
    egg_cli.main()

    calls: list[list[str]] = []

    def fake_run(cmd, check=True):
        calls.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)

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
    assert any(cmd[0] == "Rscript" and cmd[1].endswith("hello.R") for cmd in calls)
    assert f"[hatch] Completed running {egg_path}" in caplog.text


def test_hatch_bash(monkeypatch, tmp_path, caplog):
    """Hatching should invoke bash for bash cells."""
    script = tmp_path / "hello.sh"
    script.write_text("echo hi\n")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: bash
    source: hello.sh
"""
    )
    egg_path = tmp_path / "demo.egg"

    # build the egg
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

    calls: list[list[str]] = []

    def fake_run(cmd, check=True):
        calls.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        ["egg_cli.py", "--verbose", "hatch", "--egg", str(egg_path)],
    )
    egg_cli.main()

    assert any(cmd[0] == "bash" and cmd[1].endswith("hello.sh") for cmd in calls)
    assert f"[hatch] Completed running {egg_path}" in caplog.text


def test_hatch_unknown_language(monkeypatch, tmp_path):
    """Unknown cell languages should produce a clear error."""
    src = tmp_path / "hello.foo"
    src.write_text("echo hi\n")
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
    egg_path = tmp_path / "demo.egg"
    # build
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

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: None)
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "hatch", "--egg", str(egg_path)])
    with pytest.raises(SystemExit):
        egg_cli.main()


def test_requires_subcommand(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["egg_cli.py"])
    with pytest.raises(SystemExit) as exc:
        egg_cli.main()
    assert exc.value.code == 2


def test_help_without_subcommand(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["egg_cli.py"])
    with pytest.raises(SystemExit):
        egg_cli.main()


def test_build_missing_source(monkeypatch, tmp_path):
    """Building should fail with a clear error when a source file is missing."""
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: missing.py
"""
    )
    output = tmp_path / "demo.egg"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
    )
    with pytest.raises(FileNotFoundError) as exc:
        egg_cli.main()
    msg = str(exc.value)
    assert "missing.py" in msg
    assert str(manifest) in msg


def test_version_option(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "--version"])
    with pytest.raises(SystemExit):
        egg_cli.main()
    captured = capsys.readouterr()
    assert egg_cli.__version__ in captured.out


def test_verbose_after_subcommand(monkeypatch, tmp_path, caplog):
    """Global options like ``--verbose`` should work after subcommands."""
    output = tmp_path / "demo.egg"
    caplog.set_level(logging.INFO)
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
            "--verbose",
        ],
    )
    egg_cli.main()
    assert output.is_file()


def test_hashes_in_archive(monkeypatch, tmp_path):
    output = tmp_path / "demo.egg"
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
        ],
    )
    egg_cli.main()

    with zipfile.ZipFile(output) as zf:
        names = zf.namelist()
        assert "hashes.yaml" in names
        with zf.open("hashes.yaml") as f:
            hashes = yaml.safe_load(f)
        for name, digest in hashes.items():
            with zf.open(name) as fh:
                data = fh.read()
            assert hashlib.sha256(data).hexdigest() == digest


def test_deterministic_build(monkeypatch, tmp_path):
    base_args = [
        "egg_cli.py",
        "build",
        "--manifest",
        os.path.join("examples", "manifest.yaml"),
    ]

    out1 = tmp_path / "one.egg"
    out2 = tmp_path / "two.egg"

    monkeypatch.setattr(sys, "argv", base_args + ["--output", str(out1)])
    egg_cli.main()

    monkeypatch.setattr(sys, "argv", base_args + ["--output", str(out2)])
    egg_cli.main()

    assert out1.read_bytes() == out2.read_bytes()


def test_verify_subcommand(monkeypatch, tmp_path, caplog):
    output = tmp_path / "demo.egg"
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
        ],
    )
    egg_cli.main()

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        ["egg_cli.py", "--verbose", "verify", "--egg", str(output)],
    )
    egg_cli.main()
    assert f"[verify] {output} verified successfully" in caplog.text


def test_verify_failure(monkeypatch, tmp_path):
    output = tmp_path / "demo.egg"
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
        ],
    )
    egg_cli.main()

    # Corrupt the archive
    with zipfile.ZipFile(output, "r") as zf:
        contents = {name: zf.read(name) for name in zf.namelist()}
    contents["hello.py"] = b"print('tampered')\n"
    with zipfile.ZipFile(output, "w") as zf:
        for name, data in contents.items():
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)

    monkeypatch.setattr(
        sys,
        "argv",
        ["egg_cli.py", "verify", "--egg", str(output)],
    )
    with pytest.raises(SystemExit):
        egg_cli.main()
