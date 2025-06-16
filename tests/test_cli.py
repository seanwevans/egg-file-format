import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
import egg_cli  # noqa: E402


def test_build(capsys):
    egg_cli.build(argparse.Namespace())
    captured = capsys.readouterr()
    assert "[build] Building egg... (placeholder)" in captured.out


def test_hatch(capsys):
    egg_cli.hatch(argparse.Namespace())
    captured = capsys.readouterr()
    assert "[hatch] Hatching egg... (placeholder)" in captured.out
