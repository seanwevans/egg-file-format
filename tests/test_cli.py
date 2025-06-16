import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
import zipfile

import egg_cli  # noqa: E402


def test_build(monkeypatch, tmp_path, capsys):
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

    captured = capsys.readouterr()
    assert (
        "[build] Created"
        in captured.out
    )


    assert output.is_file()
    with zipfile.ZipFile(output) as zf:
        names = zf.namelist()
    assert "hello.py" in names
    assert "hello.R" in names


def test_hatch(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "hatch"])
    egg_cli.main()
    captured = capsys.readouterr()
    assert "[hatch] Hatching egg... (placeholder)" in captured.out


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
    assert "usage:" in captured.out


def test_version_option(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "--version"])
    with pytest.raises(SystemExit):
        egg_cli.main()
    captured = capsys.readouterr()
    assert egg_cli.__version__ in captured.out
