"""Minimal sandbox preparation utilities.

This module provides helper functions for constructing placeholder micro-VM
images and launching them via `Firecracker <https://firecracker-microvm.github.io/>`_.
The actual VM image creation is heavily simplified and merely writes a
``microvm.json`` configuration file describing the runtime language.  Future
implementations will build real VM disk images and kernels.  ``launch_microvm``
is a thin wrapper around the ``firecracker`` binary which expects the
configuration file produced by :func:`build_microvm_image`.
"""

from __future__ import annotations

import json
import logging
import tempfile
import subprocess
import platform
from .constants import SUPPORTED_PLATFORMS
from pathlib import Path
from typing import Dict

from .manifest import Manifest

logger = logging.getLogger(__name__)


def check_platform() -> None:
    """Raise ``RuntimeError`` if running on an unsupported platform."""
    current = platform.system()
    if current not in SUPPORTED_PLATFORMS:
        raise RuntimeError(f"Unsupported platform: {current}")


def build_microvm_image(language: str, dest: Path) -> None:
    """Create a placeholder Firecracker micro-VM image for ``language``.

    A ``microvm.json`` configuration file identifying the runtime is written
    inside ``dest``.  Future versions will build an actual VM image with a
    kernel and root filesystem.

    Parameters
    ----------
    language:
        Name of the runtime language.
    dest:
        Directory where the image should be created.
    """

    dest.mkdir(parents=True, exist_ok=True)
    config = {
        "language": language,
        "vm_type": "firecracker",
    }
    conf_json = dest / "microvm.json"
    conf_json.write_text(json.dumps(config), encoding="utf-8")
    conf_yaml = dest / "microvm.conf"
    conf_yaml.write_text(f"language: {language}\n", encoding="utf-8")
    logger.debug("[sandboxer] wrote %s and %s", conf_json, conf_yaml)


def build_container_image(language: str, dest: Path) -> None:
    """Create a placeholder container image configuration for ``language``."""

    dest.mkdir(parents=True, exist_ok=True)
    config = {
        "language": language,
        "runtime": "container",
    }
    conf_json = dest / "container.json"
    conf_json.write_text(json.dumps(config), encoding="utf-8")
    conf_yaml = dest / "container.conf"
    conf_yaml.write_text(f"language: {language}\n", encoding="utf-8")
    logger.debug("[sandboxer] wrote %s and %s", conf_json, conf_yaml)


def prepare_images(
    manifest: Manifest, base_dir: Path | str | None = None
) -> Dict[str, Path]:
    """Prepare container images for each runtime referenced in ``manifest``.

    Parameters
    ----------
    manifest:
        Parsed :class:`~egg.manifest.Manifest` describing the notebook.
    base_dir:
        Optional directory in which to create sandbox images. A temporary
        directory is created if not provided.

    Returns
    -------
    Dict[str, Path]
        Mapping of language name to created image directory path.
    """
    check_platform()
    system = platform.system()
    if base_dir is None:
        base = Path(tempfile.mkdtemp())
    else:
        base = Path(base_dir)
    images: Dict[str, Path] = {}
    for cell in manifest.cells:
        lang = cell.language.lower()
        if lang in images:
            continue  # pragma: no cover
        img_dir = base / f"{lang}-image"
        if system == "Linux":
            build_microvm_image(lang, img_dir)
        else:
            build_container_image(lang, img_dir)

        logger.info("[sandboxer] prepared %s image at %s", lang, img_dir)
        images[lang] = img_dir
    return images


def launch_microvm(image_dir: Path) -> subprocess.CompletedProcess:
    """Launch a Firecracker micro-VM using ``image_dir/microvm.json``.

    Parameters
    ----------
    image_dir:
        Directory containing the ``microvm.json`` configuration file.

    Returns
    -------
    subprocess.CompletedProcess
        The result object from :func:`subprocess.run`.
    """
    config = image_dir / "microvm.json"
    cmd = ["firecracker", "--config-file", str(config)]
    logger.info("[sandboxer] launching Firecracker: %s", " ".join(cmd))
    return subprocess.run(cmd, check=True)


def launch_container(image_dir: Path) -> subprocess.CompletedProcess:
    """Launch a container using ``image_dir/container.json``."""

    config = image_dir / "container.json"
    cmd = ["docker", "run", json.loads(config.read_text())["language"]]
    logger.info("[sandboxer] launching container: %s", " ".join(cmd))
    return subprocess.run(cmd, check=True)
