"""Simplified composer agent for the egg build pipeline."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, List

from .manifest import load_manifest, Manifest


from .hashing import (
    compute_hashes,
    write_hashes_file,
    sign_hashes,
    SIGNING_KEY,
)


def _collect_sources(manifest: Manifest) -> Iterable[Path]:
    """Yield normalized cell source paths from ``manifest``."""
    for cell in manifest.cells:
        yield Path(cell.source)


def compose(
    manifest_path: Path | str,
    output_path: Path | str,
    *,
    dependencies: Iterable[Path] | None = None,
    signing_key: bytes | None = None,
) -> None:
    """Compose an egg archive by zipping manifest, sources, and dependencies.

    Parameters
    ----------
    manifest_path : Path | str
        Path to the manifest YAML file describing sources.
    output_path : Path | str
        Destination ``.egg`` archive path.
    dependencies : Iterable[Path] | None, optional
        Additional files to include under ``runtime/``.
    signing_key : bytes | None, optional
        Key used to sign ``hashes.yaml``. Defaults to ``SIGNING_KEY``.
    """
    manifest_path = Path(manifest_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(manifest_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        copied: List[Path] = []
        # copy manifest under a fixed name inside the archive
        manifest_copy = tmpdir_path / "manifest.yaml"
        shutil.copy2(manifest_path, manifest_copy)
        copied.append(manifest_copy)

        manifest_dir = manifest_path.parent
        # copy referenced sources
        for rel_src in _collect_sources(manifest):
            src = manifest_dir / rel_src
            if not src.is_file():
                raise FileNotFoundError(
                    f"Source file not found: {src} (referenced from {manifest_path})"
                )
            dest = tmpdir_path / rel_src
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append(dest)

        # copy runtime dependencies under runtime/
        runtime_dir = tmpdir_path / "runtime"
        seen_runtime: set[str] = set()
        if dependencies:
            for dep in dependencies:
                if isinstance(dep, Path):
                    dest_name = dep.name
                    if dest_name in seen_runtime:
                        raise ValueError(f"Duplicate dependency filename: {dest_name}")
                    seen_runtime.add(dest_name)
                    dest = runtime_dir / dest_name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dep, dest)
                    copied.append(dest)

        # write hashes file and signature
        hashes = compute_hashes(copied, base_dir=tmpdir_path)
        hashes_path = tmpdir_path / "hashes.yaml"
        write_hashes_file(hashes, hashes_path)
        key = SIGNING_KEY if signing_key is None else signing_key
        sig = sign_hashes(hashes_path, key=key)
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
