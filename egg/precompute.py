"""Agent for precomputing cell outputs."""

from __future__ import annotations

import os
import subprocess
import shutil
import sys
from pathlib import Path
from typing import List

from .manifest import load_manifest
from .utils import get_lang_command


def precompute_cells(manifest_path: Path | str) -> List[Path]:
    """Execute each cell listed in ``manifest_path`` and capture stdout.

    For every cell in the manifest a new file ``<source>.out`` is written
    containing the program output. The path of each created file is returned.
    """
    manifest_path = Path(manifest_path)
    manifest = load_manifest(manifest_path)
    manifest_dir = manifest_path.parent.resolve()

    outputs: List[Path] = []
    for cell in manifest.cells:
        lang = cell.language.lower()
        cmd = get_lang_command(lang)
        if cmd is None:
            raise ValueError(f"Unsupported language: {cell.language}")
        if shutil.which(cmd[0]) is None:
            raise FileNotFoundError(
                f"Required runtime '{cmd[0]}' for {cell.language} cells not found"
            )
        src = manifest_dir / cell.source
        out_file = src.with_name(src.name + ".out")
        with open(out_file, "w", encoding="utf-8") as out:
            subprocess.run(cmd + [str(src)], check=True, stdout=out)
        outputs.append(out_file)
    return outputs
