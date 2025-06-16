"""Agent for precomputing cell outputs."""

from __future__ import annotations

import subprocess
import shutil
import sys
from pathlib import Path
from typing import List

from .manifest import load_manifest
from .utils import get_lang_command
from .hashing import sha256_file, write_hashes_file, load_hashes


def precompute_cells(manifest_path: Path | str) -> List[Path]:
    """Execute each cell listed in ``manifest_path`` and capture stdout.

    For every cell in the manifest a new file ``<source>.out`` is written
    containing the program output. The path of each created file is returned.
    """
    manifest_path = Path(manifest_path)
    manifest = load_manifest(manifest_path)
    manifest_dir = manifest_path.parent.resolve()

    cache_path = manifest_dir / "precompute_hashes.yaml"
    prev_hashes = load_hashes(cache_path) if cache_path.exists() else {}
    new_hashes: dict[str, str] = {}

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
        src_rel = Path(cell.source)
        src = manifest_dir / src_rel
        digest = sha256_file(src)
        new_hashes[src_rel.as_posix()] = digest
        out_file = src.with_name(src.name + ".out")
        if prev_hashes.get(src_rel.as_posix()) == digest and out_file.exists():
            outputs.append(out_file)
            continue
        with open(out_file, "w", encoding="utf-8") as out:
            subprocess.run(cmd + [str(src)], check=True, stdout=out)
        outputs.append(out_file)

    write_hashes_file(new_hashes, cache_path)
    return outputs
