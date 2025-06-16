import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
import egg_cli  # noqa: E402
import pytest

def test_build(monkeypatch, capsys, tmp_path):
    manifest = tmp_path / "manifest.yaml"
    (tmp_path / "script.py").write_text("print('hi')")
    manifest.write_text(
        "name: t\ncells:\n- language: python\n  source: script.py\n"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            str(manifest),
            "--output",
            "out.egg",
        ],
    )
    egg_cli.main()
    captured = capsys.readouterr()
    assert "[build] Building egg... (placeholder)" in captured.out
    assert str((tmp_path / "script.py").resolve()) in captured.out

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
