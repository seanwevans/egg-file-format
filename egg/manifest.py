"""Manifest parsing utilities and data structures.

Defines dataclasses for cells and the top-level manifest and validates
``manifest.yaml`` files when loading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
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
    """A single code cell entry in the manifest."""

    language: str
    source: str


@dataclass
class Manifest:
    """Top-level manifest describing the notebook cells."""

    name: str
    description: str
    cells: List[Cell]
    permissions: dict[str, bool] | None = None
    dependencies: List[str] | None = None
    author: str | None = None
    created: str | None = None
    license: str | None = None


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


def _load_manifest_yaml(path: Path | str) -> dict:
    """Load raw manifest YAML data and ensure the root is a mapping."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Manifest root must be a mapping")
    return data


def _validate_dependencies(deps_data: object) -> List[str] | None:
    """Validate and normalize ``dependencies`` data from a manifest."""
    dependencies: List[str] | None
    if deps_data is None:
        dependencies = None
    else:
        if not isinstance(deps_data, list):
            raise ValueError("'dependencies' must be a list")
        dep_set: set[str] = set()
        dependencies = []
        for dep in deps_data:
            if not isinstance(dep, str):
                raise ValueError("dependency entries must be strings")
            if dep in dep_set:
                raise ValueError(f"Duplicate dependency: {dep}")
            dep_set.add(dep)
            dependencies.append(dep)
    return dependencies


def load_manifest_dependencies(path: Path | str) -> List[str] | None:
    """Load and validate only the ``dependencies`` section of a manifest."""
    data = _load_manifest_yaml(path)
    return _validate_dependencies(data.get("dependencies"))
_SPDX_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*\+?$")


def _validate_created(value: str) -> None:
    """Validate the ``created`` field as an ISO-8601 date/datetime string."""
    examples = "'2026-04-04', '2026-04-04T12:30:00Z'"
    try:
        # Accept plain calendar dates, e.g. YYYY-MM-DD.
        date.fromisoformat(value)
        return
    except ValueError:
        pass

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        # Accept full datetime timestamps.
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            f"'created' must be an ISO-8601 date or datetime string (examples: "
            f"{examples}). Got: {value!r}"
        ) from exc


def _validate_license(value: str) -> None:
    """Validate ``license`` as a basic SPDX token/expression."""
    examples = "'MIT', 'Apache-2.0', '(MIT OR Apache-2.0)'"
    allowed = re.fullmatch(r"[A-Za-z0-9().+\- ]+", value)
    if not allowed:
        raise ValueError(
            f"'license' must look like a basic SPDX expression (examples: {examples}). "
            f"Got: {value!r}"
        )

    token = ""
    saw_identifier = False
    i = 0
    while i < len(value):
        ch = value[i]
        if ch in {"(", ")", " "}:
            if token:
                if token in {"AND", "OR", "WITH"}:
                    pass
                elif _SPDX_TOKEN_RE.match(token):
                    saw_identifier = True
                else:
                    raise ValueError(
                        f"'license' must look like a basic SPDX expression "
                        f"(examples: {examples}). Got: {value!r}"
                    )
                token = ""
            i += 1
            continue
        token += ch
        i += 1

    if token:
        if token in {"AND", "OR", "WITH"}:
            pass
        elif _SPDX_TOKEN_RE.match(token):
            saw_identifier = True
        else:
            raise ValueError(
                f"'license' must look like a basic SPDX expression "
                f"(examples: {examples}). Got: {value!r}"
            )

    if not saw_identifier:
        raise ValueError(
            f"'license' must look like a basic SPDX expression (examples: {examples}). "
            f"Got: {value!r}"
        )


def load_manifest(path: Path | str) -> Manifest:
    """Load a manifest from a YAML file.

    Args:
        path: Path to the YAML manifest.

    Returns:
        Parsed :class:`Manifest` instance.

    Raises:
        ValueError: If required fields are missing or malformed.
    """
    data = _load_manifest_yaml(path)

    required_fields = {"name", "description", "cells"}
    optional_fields = {"permissions", "dependencies", "author", "created", "license"}
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    unknown_fields = set(data) - required_fields - optional_fields
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

    permissions_data = data.get("permissions")
    permissions: dict[str, bool] | None
    if permissions_data is None:
        permissions = None
    else:
        if not isinstance(permissions_data, dict):
            raise ValueError("'permissions' must be a mapping")
        permissions = {}
        for perm, val in permissions_data.items():
            if not isinstance(perm, str):
                raise ValueError(f"Permission key {perm!r} must be a string")
            if not isinstance(val, bool):
                raise ValueError(f"Permission '{perm}' must be a boolean")
            permissions[perm] = val

    dependencies = _validate_dependencies(data.get("dependencies"))

    author_data = data.get("author")
    if author_data is not None and not isinstance(author_data, str):
        raise ValueError("'author' must be a string")

    created_data = data.get("created")
    if created_data is not None and not isinstance(created_data, str):
        raise ValueError("'created' must be a string")
    if isinstance(created_data, str):
        _validate_created(created_data)

    license_data = data.get("license")
    if license_data is not None and not isinstance(license_data, str):
        raise ValueError("'license' must be a string")
    if isinstance(license_data, str):
        _validate_license(license_data)

    manifest_dir = Path(path).resolve().parent
    cells: List[Cell] = []
    cell_sources: set[str] = set()
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
        if normalized in cell_sources:
            raise ValueError(f"Duplicate cell source: {normalized}")
        cell_sources.add(normalized)
        cells.append(Cell(language=cell["language"], source=normalized))

    return Manifest(
        name=data["name"],
        description=data["description"],
        cells=cells,
        permissions=permissions,
        dependencies=dependencies,
        author=author_data,
        created=created_data,
        license=license_data,
    )
