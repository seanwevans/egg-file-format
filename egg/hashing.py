"""Utility functions for hashing files in an egg archive."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable

import zipfile
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    raise ModuleNotFoundError(
        "PyYAML is required for egg hashing. Install with 'pip install PyYAML'"
    ) from exc


_CHUNK_SIZE = 8192

# Default private key seed for demonstration/testing purposes
DEFAULT_PRIVATE_KEY = os.getenv("EGG_PRIVATE_KEY", "egg-signing-key").encode()


def _signing_key(key: bytes | None = None) -> SigningKey:
    """Return a ``SigningKey`` derived from ``key``."""
    if key is None:
        key = DEFAULT_PRIVATE_KEY
    if len(key) != 32:
        key = hashlib.sha256(key).digest()
    return SigningKey(key)


def _verify_key(key: bytes | None = None) -> VerifyKey:
    """Return a ``VerifyKey`` derived from ``key``."""
    if key is None:
        env = os.getenv("EGG_PUBLIC_KEY")
        if env is not None:
            key = env.encode()
        else:
            return _signing_key().verify_key
    if len(key) == 64:
        try:
            key = bytes.fromhex(key.decode())
        except Exception:  # pragma: no cover - invalid hex
            pass
    if len(key) != 32:
        key = hashlib.sha256(key).digest()
    return VerifyKey(key)


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
        data = yaml.safe_load(f)

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("hashes.yaml must contain a mapping")

    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("hashes.yaml keys and values must be strings")

    return data


def sign_hashes(path: Path, *, private_key: bytes | None = None) -> str:
    """Return an Ed25519 signature of ``path``."""
    sk = _signing_key(private_key)
    signature = sk.sign(path.read_bytes()).signature
    return signature.hex()


def verify_hashes(directory: Path, hashes: Dict[str, str]) -> bool:
    """Verify that files in ``directory`` match expected ``hashes``."""
    for name, expected in hashes.items():
        calc = sha256_file(directory / name)
        if calc != expected:
            return False
    return True


def verify_archive(archive: Path, *, public_key: bytes | None = None) -> bool:
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
    vk = _verify_key(public_key)
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts:
                return False
        try:
            with zf.open("hashes.yaml") as f:
                hashes_bytes = f.read()
            with zf.open("hashes.sig") as f:
                signature = bytes.fromhex(f.read().decode().strip())
        except KeyError:
            return False

        try:
            vk.verify(hashes_bytes, signature)
        except BadSignatureError:
            return False

        hashes = yaml.safe_load(hashes_bytes) or {}
        if not isinstance(hashes, dict):
            raise ValueError("hashes.yaml must contain a mapping")
        for key, value in hashes.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("hashes.yaml keys and values must be strings")

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
