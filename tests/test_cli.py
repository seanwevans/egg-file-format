import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
import egg_cli  # noqa: E402


def test_build(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "build"])
    egg_cli.main()
    captured = capsys.readouterr()
    assert "[build] Building egg... (placeholder)" in captured.out


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
