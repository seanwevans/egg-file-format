"""Utility functions for hashing files in an egg archive."""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import Dict, Iterable

import zipfile

import yaml


_CHUNK_SIZE = 8192

# Simplified signing key for demonstration/testing purposes
SIGNING_KEY = b"egg-signing-key"


def sha256_file(path: Path) -> str:
    """Return SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_hashes(
    files: Iterable[Path], *, base_dir: Path | None = None
) -> Dict[str, str]:
    """Compute SHA256 hashes for ``files``.

    Parameters
    ----------
    files : Iterable[Path]
        Files to hash.
    base_dir : Path | None, optional
        If given, keys in the returned mapping are paths relative to this
        directory.  Otherwise each file's basename is used.

    Returns
    -------
    Dict[str, str]
        Mapping of file path (relative or basename) to SHA256 digest.

    Raises
    ------
    ValueError
        If duplicate keys are encountered.
    """

    hashes: Dict[str, str] = {}
    for f in files:
        path = Path(f)
        name = str(path.relative_to(base_dir)) if base_dir else path.name
        if name in hashes:
            raise ValueError(f"Duplicate file basename: {name}")
        hashes[name] = sha256_file(path)
    return hashes


def write_hashes_file(hashes: Dict[str, str], path: Path) -> None:
    """Write a mapping of file hashes to ``path`` as YAML."""
    # ``yaml.safe_dump`` does not guarantee deterministic key order unless
    # ``sort_keys`` is explicitly set.  Relying on the default can result in
    # nondeterministic builds across PyYAML versions.  Explicitly enable key
    # sorting so the output is stable regardless of environment.
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(hashes, f, sort_keys=True)


def load_hashes(path: Path) -> Dict[str, str]:
    """Load a YAML file of hashes."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def sign_hashes(path: Path, *, key: bytes = SIGNING_KEY) -> str:
    """Return an HMAC-SHA256 signature of ``path``."""
    data = path.read_bytes()
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def verify_hashes(directory: Path, hashes: Dict[str, str]) -> bool:
    """Verify that files in ``directory`` match expected ``hashes``."""
    for name, expected in hashes.items():
        calc = sha256_file(directory / name)
        if calc != expected:
            return False
    return True


def verify_archive(archive: Path) -> bool:
    """Verify that files inside a ZIP ``archive`` match ``hashes.yaml``.

    Parameters
    ----------
    archive : Path
        Path to the ``.egg`` archive to verify.

    Returns
    -------
    bool
        ``True`` if all files match their recorded digests, ``False`` otherwise.
    """
    with zipfile.ZipFile(archive) as zf:
        try:
            with zf.open("hashes.yaml") as f:
                hashes_bytes = f.read()
            with zf.open("hashes.sig") as f:
                signature = f.read().decode().strip()
        except KeyError:
            return False

        expected_sig = hmac.new(SIGNING_KEY, hashes_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return False

        hashes = yaml.safe_load(hashes_bytes) or {}

        for name, expected in hashes.items():
            try:
                with zf.open(name) as fh:
                    data = fh.read()
            except KeyError:
                return False
            if hashlib.sha256(data).hexdigest() != expected:
                return False

        # Ensure no unverified files are present in the archive
        names = set(zf.namelist())
        names.discard("hashes.yaml")
        names.discard("hashes.sig")
        if names != set(hashes.keys()):
            return False

    return True
