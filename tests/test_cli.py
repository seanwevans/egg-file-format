import os
import sys
import zipfile
import hashlib
import yaml
import pytest
import logging

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


def test_hatch(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "--verbose", "hatch"])
    egg_cli.main()
    assert "[hatch] Hatching egg... (placeholder)" in caplog.text


def test_requires_subcommand(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["egg_cli.py"])
    with pytest.raises(SystemExit) as exc:
        egg_cli.main()
    assert exc.value.code == 2


def test_help_without_subcommand(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["egg_cli.py"])
    with pytest.raises(SystemExit):
        egg_cli.main()
    captured = capsys.readouterr()
    assert "usage:" in captured.err


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
