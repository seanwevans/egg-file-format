from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

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

    for field in ("name", "description", "cells"):
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    cells_data = data["cells"]
    if not isinstance(cells_data, list):
        raise ValueError("'cells' must be a list")

    cells: List[Cell] = []
    for i, cell in enumerate(cells_data):
        if not isinstance(cell, dict):
            raise ValueError(f"Cell #{i} must be a mapping")
        if "language" not in cell or "source" not in cell:
            raise ValueError("Each cell requires 'language' and 'source'")
        cells.append(Cell(language=cell["language"], source=cell["source"]))

    return Manifest(name=data["name"], description=data["description"], cells=cells)
