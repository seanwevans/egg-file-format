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

from .hashing import compute_hashes, write_hashes_file, sign_hashes, SIGNING_KEY


def _collect_sources(manifest: dict) -> Iterable[Path]:
    """Yield relative paths referenced in the manifest."""
    for cell in manifest.get("cells", []):
        source = cell.get("source")
        if source:
            yield Path(source)


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
        for rel_src in _collect_sources(manifest):
            src = manifest_path.parent / rel_src
            if not src.is_file():
                raise FileNotFoundError(
                    f"Source file not found: {src} (referenced from {manifest_path})"
                )
            dest = tmpdir_path / rel_src
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append(dest)

        # write hashes file and signature
        hashes = compute_hashes(copied, base_dir=tmpdir_path)
        hashes_path = tmpdir_path / "hashes.yaml"
        write_hashes_file(hashes, hashes_path)
        sig = sign_hashes(hashes_path, key=SIGNING_KEY)
        sig_path = tmpdir_path / "hashes.sig"
        sig_path.write_text(sig, encoding="utf-8")
        copied.extend([hashes_path, sig_path])

        with zipfile.ZipFile(output_path, "w") as zf:
            for file in sorted(copied, key=lambda p: str(p.relative_to(tmpdir_path))):
                rel = file.relative_to(tmpdir_path)
                zi = zipfile.ZipInfo(rel.as_posix())
                zi.date_time = (1980, 1, 1, 0, 0, 0)
                zi.compress_type = zipfile.ZIP_DEFLATED
                with open(file, "rb") as f:
                    zf.writestr(zi, f.read())
