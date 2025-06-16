"""Simplified composer agent for the egg build pipeline."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

import yaml


def _collect_sources(manifest: dict, base_dir: Path) -> Iterable[Path]:
    """Yield file paths referenced in the manifest."""
    for cell in manifest.get("cells", []):
        source = cell.get("source")
        if source:
            yield base_dir / source


def compose(manifest_path: Path | str, output_path: Path | str) -> None:
    """Compose an egg archive by zipping manifest and sources.

    Parameters
    ----------
    manifest_path : Path | str
        Path to the manifest YAML file describing sources.
    output_path : Path | str
        Destination ``.egg`` archive path.
    """
    manifest_path = Path(manifest_path)
    output_path = Path(output_path)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        # copy manifest
        shutil.copy2(manifest_path, tmpdir_path / manifest_path.name)
        # copy referenced sources
        for src in _collect_sources(manifest, manifest_path.parent):
            shutil.copy2(src, tmpdir_path / src.name)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in tmpdir_path.iterdir():
                zf.write(file, arcname=file.name)
