import os
import sys
from pathlib import Path
import logging

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import egg_cli  # noqa: E402
from egg.hashing import verify_archive  # noqa: E402

EXAMPLE_ADV_MANIFEST = (
    Path(__file__).resolve().parent.parent / "examples" / "advanced_manifest.yaml"
)


def test_build_advanced_manifest(monkeypatch, tmp_path, caplog):
    output = tmp_path / "advanced.egg"
    caplog.set_level(logging.INFO)
    for dep in ["python:3.11", "r:4.3", "bash:5"]:
        (EXAMPLE_ADV_MANIFEST.parent / dep).write_text("img")
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
    egg_cli.main()

    assert output.is_file()
    assert verify_archive(output)
