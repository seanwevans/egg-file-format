"""Agent for fetching interpreter/runtime blocks referenced in a manifest."""

from __future__ import annotations

import logging
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


def fetch_runtime_blocks(manifest_path: Path | str) -> List[Path]:
    """Return absolute paths to runtime dependencies listed in ``manifest_path``.

    Currently only local file paths listed under a ``dependencies`` field are
    supported. Each path must be relative to the manifest directory and must
    exist on disk.

    Parameters
    ----------
    manifest_path : Path | str
        Path to the manifest YAML file.

    Returns
    -------
    List[Path]
        Absolute paths to the dependency files.

    Raises
    ------
    FileNotFoundError
        If a dependency path does not exist.
    ValueError
        If dependency paths are absolute or escape the manifest directory.
    """

    manifest_path = Path(manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f) or {}

    deps = manifest.get("dependencies", [])
    if deps is None:
        return []
    if not isinstance(deps, list):
        raise ValueError("'dependencies' must be a list")

    manifest_dir = manifest_path.parent.resolve()
    resolved: List[Path] = []

    for dep in deps:
        if not isinstance(dep, str):
            raise ValueError("dependency entries must be strings")
        p = Path(dep)
        if p.is_absolute():
            raise ValueError(f"Absolute dependency paths are not allowed: {dep}")
        abs_path = (manifest_dir / p).resolve(strict=False)
        if not _is_relative_to(abs_path, manifest_dir):
            raise ValueError(f"Dependency path escapes manifest directory: {dep}")
        if not abs_path.is_file():
            if ":" in dep:
                logger.debug("[runtime_fetcher] Skipping remote dependency %s", dep)
                continue
            raise FileNotFoundError(f"Dependency file not found: {abs_path}")
        resolved.append(abs_path)
        logger.debug("[runtime_fetcher] Fetched %s", abs_path)

    return resolved
