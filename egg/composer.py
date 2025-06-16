"""Simplified composer agent for the egg build pipeline."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, List

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    raise ModuleNotFoundError(
        "PyYAML is required to use egg composer. Install with 'pip install PyYAML'"
    ) from exc

from .hashing import compute_hashes, write_hashes_file


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
        copied: List[Path] = []
        # copy manifest
        manifest_copy = tmpdir_path / manifest_path.name
        shutil.copy2(manifest_path, manifest_copy)
        copied.append(manifest_copy)

        # copy referenced sources
        for src in _collect_sources(manifest, manifest_path.parent):
            dest = tmpdir_path / src.name
            shutil.copy2(src, dest)
            copied.append(dest)

        # write hashes file
        hashes = compute_hashes(copied)
        hashes_path = tmpdir_path / "hashes.yaml"
        write_hashes_file(hashes, hashes_path)
        copied.append(hashes_path)

        with zipfile.ZipFile(output_path, "w") as zf:
            for file in sorted(copied, key=lambda p: p.name):
                zi = zipfile.ZipInfo(file.name)
                zi.date_time = (1980, 1, 1, 0, 0, 0)
                zi.compress_type = zipfile.ZIP_DEFLATED
                with open(file, "rb") as f:
                    zf.writestr(zi, f.read())
