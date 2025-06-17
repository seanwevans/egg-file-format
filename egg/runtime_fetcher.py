"""Agent for fetching interpreter/runtime blocks referenced in a manifest.

In addition to loading local files, this module can download container images
from an HTTP registry.  The registry base URL is looked up from the
``EGG_REGISTRY_URL`` environment variable or a ``~/.egg_registry`` file if the
environment variable is unset.
"""

from __future__ import annotations

import logging
import os
import shutil
from urllib.parse import quote
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from pathlib import Path
from typing import List

from .utils import _is_relative_to

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
    image: str, dest: Path, base_url: str, timeout: float = 30.0
) -> Path:
    """Download ``image`` from ``base_url`` to ``dest``.

    Parameters
    ----------
    timeout : float, optional
        Socket timeout passed to ``urlopen``.

    A ``ValueError`` is raised if ``dest`` resolves outside its parent
    directory.  This prevents a malicious symlink from redirecting the
    download to an arbitrary location. If the HTTP request fails, a
    ``RuntimeError`` is raised with the failing URL and original
    exception.
    """

    manifest_dir = dest.parent.resolve()
    dest = dest.resolve(strict=False)
    if not _is_relative_to(dest, manifest_dir):
        raise ValueError(f"Download path escapes manifest directory: {dest}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        logger.debug("[runtime_fetcher] using cached %s", dest)
        return dest

    url = f"{base_url.rstrip('/')}/{quote(image)}.img"
    logger.info("[runtime_fetcher] downloading %s -> %s", url, dest)
    try:
        with urlopen(url, timeout=timeout) as resp, open(dest, "wb") as fh:
            shutil.copyfileobj(resp, fh)
    except (HTTPError, URLError) as exc:  # pragma: no cover - network errors
        raise RuntimeError(f"Failed to download {url}: {exc}") from exc
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
    registry = _get_registry_url()

    for dep in deps:
        if not isinstance(dep, str):
            raise ValueError("dependency entries must be strings")
        if dep in seen:
            raise ValueError(f"Duplicate dependency entry: {dep}")
        seen.add(dep)
        if ":" in dep:
            if "/" in dep or "\\" in dep:
                raise ValueError(f"Invalid container image name: {dep}")
            if registry:
                safe = dep.replace("/", "_").replace("\\", "_").replace(":", "_")
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
