"""Agent for fetching interpreter/runtime blocks referenced in a manifest.

In addition to loading local files, this module can download container images
from an HTTP registry.  The registry base URL is looked up from the
``EGG_REGISTRY_URL`` environment variable or a ``~/.egg_registry`` file if the
environment variable is unset.
"""

from __future__ import annotations

import hashlib
import logging
import os
from urllib.parse import quote
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import socket
from pathlib import Path, PurePosixPath
from typing import List

from .utils import _is_relative_to


_CHUNK_SIZE = 8192
_PROGRESS_INTERVAL = 1 << 20  # 1 MiB

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    raise ModuleNotFoundError(
        "PyYAML is required to use the runtime fetcher. Install with 'pip install PyYAML'"
    ) from exc

logger = logging.getLogger(__name__)


def _get_registry_url() -> str | None:
    """Return the container registry base URL from env or config file."""
    url = os.getenv("EGG_REGISTRY_URL")
    if url:
        return url
    conf = Path.home() / ".egg_registry"
    if conf.is_file():
        return conf.read_text().strip()
    return None


def _download_container(
    image: str,
    dest: Path,
    base_url: str,
    timeout: float | None = None,
    *,
    expected_digest: str | None = None,
) -> Path:
    """Download ``image`` from ``base_url`` to ``dest``.

    Parameters
    ----------
    timeout : float, optional
        Socket timeout passed to ``urlopen``. Defaults to the value of
        ``EGG_DOWNLOAD_TIMEOUT`` if set, otherwise ``30.0``. Invalid
        environment values raise ``ValueError``.
    expected_digest : str, optional
        Expected SHA256 hex digest of the image. Existing files with a matching
        digest are trusted; missing or mismatched digests trigger a
        re-download. After downloading, if the checksum does not match,
        ``RuntimeError`` is raised.

    A ``ValueError`` is raised if ``dest`` resolves outside its parent
    directory.  This prevents a malicious symlink from redirecting the
    download to an arbitrary location. If the HTTP request fails, a
    ``RuntimeError`` is raised with the failing URL and original
    exception.
    """

    if timeout is None:
        env_timeout = os.getenv("EGG_DOWNLOAD_TIMEOUT")
        if env_timeout:
            try:
                timeout = float(env_timeout)
            except ValueError as exc:  # pragma: no cover - invalid env
                raise ValueError("EGG_DOWNLOAD_TIMEOUT must be a number") from exc
        else:
            timeout = 30.0

    manifest_dir = dest.parent.resolve()
    dest = dest.resolve(strict=False)
    if not _is_relative_to(dest, manifest_dir):
        raise ValueError(f"Download path escapes manifest directory: {dest}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        if expected_digest is not None:
            h = hashlib.sha256()
            with open(dest, "rb") as fh:
                for chunk in iter(lambda: fh.read(_CHUNK_SIZE), b""):
                    h.update(chunk)
            digest = h.hexdigest()
            if digest == expected_digest:
                logger.debug(
                    "[runtime_fetcher] using cached %s (digest verified)", dest
                )
                return dest
            logger.info("[runtime_fetcher] cached %s digest mismatch; refreshing", dest)
        else:
            logger.info("[runtime_fetcher] refreshing %s (no expected digest)", dest)

    url = f"{base_url.rstrip('/')}/{quote(image)}.img"
    logger.info("[runtime_fetcher] downloading %s -> %s", url, dest)
    tmp = dest.with_suffix(".tmp")
    try:
        with urlopen(url, timeout=timeout) as resp, open(tmp, "wb") as fh:
            # ``urlopen`` responses provide a ``headers`` mapping. Test
            # doubles used in this project may omit the attribute, so fall back
            # to an empty mapping to avoid ``AttributeError``.
            content_length = getattr(resp, "headers", {}).get("Content-Length")
            try:
                total = int(content_length) if content_length is not None else None
            except (ValueError, TypeError):
                total = None

            h = hashlib.sha256()
            transferred = 0
            next_log = _PROGRESS_INTERVAL

            while True:
                chunk = resp.read(_CHUNK_SIZE)
                if not chunk:
                    break
                fh.write(chunk)
                h.update(chunk)
                transferred += len(chunk)
                if transferred >= next_log:
                    if total is not None:
                        logger.info(
                            "[runtime_fetcher] downloaded %d/%d bytes of %s",
                            transferred,
                            total,
                            image,
                        )
                    else:
                        logger.info(
                            "[runtime_fetcher] downloaded %d bytes of %s",
                            transferred,
                            image,
                        )
                    while transferred >= next_log:
                        next_log += _PROGRESS_INTERVAL

        if total is not None and transferred != total:
            raise RuntimeError(
                f"Incomplete download for {image}: expected {total} bytes, got {transferred}"
            )
        digest = h.hexdigest()
        if expected_digest is not None and digest != expected_digest:
            raise RuntimeError(
                f"Checksum mismatch for {image}: expected {expected_digest} but got {digest}"
            )
    except (
        HTTPError,
        URLError,
        socket.timeout,
    ) as exc:  # pragma: no cover - network errors
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to download {url}: {exc}") from exc
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    else:
        tmp.replace(dest)
    return dest


def fetch_runtime_blocks(manifest_path: Path | str) -> List[Path | str]:
    """Return absolute paths to runtime dependencies listed in ``manifest_path``.

    Dependencies can either be local file paths or container-style image
    identifiers like ``python:3.11``. Paths must be relative to the manifest
    directory and must exist on disk. Entries containing a colon are returned
    verbatim without any file-system checks.

    Parameters
    ----------
    manifest_path : Path | str
        Path to the manifest YAML file.

    Returns
    -------
    List[Path | str]
        Absolute paths to dependency files or container image strings.

    Raises
    ------
    FileNotFoundError
        If a dependency path does not exist.
    ValueError
        If dependency paths are absolute or escape the manifest directory.
    """

    manifest_path = Path(manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    if manifest is None:
        manifest = {}
    if not isinstance(manifest, dict):
        raise ValueError("Manifest root must be a mapping")

    deps = manifest.get("dependencies", [])
    if deps is None:
        return []
    if not isinstance(deps, list):
        raise ValueError("'dependencies' must be a list")

    manifest_dir = manifest_path.parent.resolve()
    resolved: List[Path | str] = []
    seen: set[str] = set()
    # Track sanitized container filenames to avoid collisions when
    # downloading multiple images that differ only by characters replaced
    # during sanitization. Mapping allows us to report the original conflicting
    # dependency strings when a clash occurs.
    safe_names: dict[str, str] = {}
    registry = _get_registry_url()

    for dep in deps:
        if not isinstance(dep, str):
            raise ValueError("dependency entries must be strings")
        if dep in seen:
            raise ValueError(f"Duplicate dependency entry: {dep}")
        seen.add(dep)
        if ":" in dep:
            if "\\" in dep:
                raise ValueError(f"Invalid container image name: {dep}")

            image_name = dep.split(":", 1)[0]
            posix = PurePosixPath(image_name)
            if (
                posix.is_absolute()
                or posix.as_posix() != image_name
                or any(part == ".." for part in posix.parts)
            ):
                raise ValueError(f"Invalid container image name: {dep}")

            if registry:
                safe = dep.replace("/", "_").replace("\\", "_").replace(":", "_")
                if safe in safe_names:
                    other = safe_names[safe]
                    raise ValueError(
                        "Sanitized dependency name conflict: "
                        f"{dep!r} and {other!r} both map to {safe!r}"
                    )
                safe_names[safe] = dep
                dest = (manifest_dir / f"{safe}.img").resolve(strict=False)
                if not _is_relative_to(dest, manifest_dir):
                    raise ValueError(
                        f"Dependency path escapes manifest directory: {dep}"
                    )
                resolved.append(_download_container(dep, dest, registry))
            else:
                resolved.append(dep)
                logger.debug("[runtime_fetcher] Recorded container spec %s", dep)
            continue
        p = Path(dep)
        if p.is_absolute():
            raise ValueError(f"Absolute dependency paths are not allowed: {dep}")
        abs_path = (manifest_dir / p).resolve(strict=False)
        if not _is_relative_to(abs_path, manifest_dir):
            raise ValueError(f"Dependency path escapes manifest directory: {dep}")
        if not abs_path.is_file():
            raise FileNotFoundError(f"Dependency file not found: {abs_path}")
        resolved.append(abs_path)
        logger.debug("[runtime_fetcher] Fetched %s", abs_path)

    return resolved
