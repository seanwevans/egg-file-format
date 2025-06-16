from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from .utils import _is_relative_to

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    raise ModuleNotFoundError(
        "PyYAML is required to load egg manifests. Install with 'pip install PyYAML'"
    ) from exc


@dataclass
class Cell:
    language: str
    source: str


@dataclass
class Manifest:
    name: str
    description: str
    cells: List[Cell]


def _normalize_source(path: str | Path, manifest_dir: Path) -> str:
    """Normalize a cell source path and ensure it stays within ``manifest_dir``."""
    p = Path(path)
    if p.is_absolute():
        raise ValueError(f"Absolute source paths are not allowed: {path}")
    manifest_dir = manifest_dir.resolve()
    abs_path = (manifest_dir / p).resolve(strict=False)
    if not _is_relative_to(abs_path, manifest_dir):
        raise ValueError(f"Source path escapes manifest directory: {path}")
    return abs_path.relative_to(manifest_dir).as_posix()


def load_manifest(path: Path | str) -> Manifest:
    """Load a manifest from a YAML file.

    Args:
        path: Path to the YAML manifest.

    Returns:
        Parsed :class:`Manifest` instance.

    Raises:
        ValueError: If required fields are missing or malformed.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("Manifest root must be a mapping")

    required_fields = {"name", "description", "cells"}
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    unknown_fields = set(data) - required_fields
    if unknown_fields:
        unknown = ", ".join(sorted(unknown_fields))
        raise ValueError(f"Unknown field(s): {unknown}")

    # Validate simple scalar fields
    if not isinstance(data["name"], str):
        raise ValueError("'name' must be a string")
    if not isinstance(data["description"], str):
        raise ValueError("'description' must be a string")

    cells_data = data["cells"]
    if not isinstance(cells_data, list):
        raise ValueError("'cells' must be a list")

    manifest_dir = Path(path).resolve().parent
    cells: List[Cell] = []
    for i, cell in enumerate(cells_data):
        if not isinstance(cell, dict):
            raise ValueError(f"Cell #{i} must be a mapping")
        if "language" not in cell or "source" not in cell:
            raise ValueError("Each cell requires 'language' and 'source'")
        if not isinstance(cell["language"], str):
            raise ValueError(f"Cell #{i} 'language' must be a string")
        if not isinstance(cell["source"], str):
            raise ValueError(f"Cell #{i} 'source' must be a string")
        normalized = _normalize_source(cell["source"], manifest_dir)
        cells.append(Cell(language=cell["language"], source=normalized))

    return Manifest(name=data["name"], description=data["description"], cells=cells)
