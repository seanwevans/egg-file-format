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
from typing import Dict, Callable

from .manifest import Manifest

logger = logging.getLogger(__name__)


def check_platform() -> None:
    """Raise ``RuntimeError`` if running on an unsupported platform."""
    current = platform.system()
    if current not in SUPPORTED_PLATFORMS:
        raise RuntimeError(f"Unsupported platform: {current}")


def build_microvm_image(language: str, dest: Path) -> None:
    """Create a minimal Firecracker micro-VM image for ``language``.

    This writes a ``microvm.json`` configuration plus placeholder ``vmlinux``
    and ``rootfs.ext4`` files.  The resulting directory can be booted via
    :func:`launch_microvm`.

    Parameters
    ----------
    language:
        Name of the runtime language.
    dest:
        Directory where the image should be created.
    """

    dest.mkdir(parents=True, exist_ok=True)

    kernel = dest / "vmlinux"
    kernel.touch()
    rootfs = dest / "rootfs.ext4"
    with open(rootfs, "wb") as f:
        f.truncate(1 * 1024 * 1024)  # 1MiB placeholder

    config = {
        "boot-source": {
            "kernel_image_path": str(kernel),
            "boot_args": f"console=ttyS0 init=/usr/bin/{language}",
        },
        "drives": [
            {
                "drive_id": "rootfs",
                "path_on_host": str(rootfs),
                "is_root_device": True,
                "is_read_only": False,
            }
        ],
    }

    conf_json = dest / "microvm.json"
    conf_json.write_text(json.dumps(config), encoding="utf-8")
    conf_yaml = dest / "microvm.conf"
    conf_yaml.write_text(
        f"language: {language}\nkernel: {kernel.name}\nrootfs: {rootfs.name}\n",
        encoding="utf-8",
    )
    logger.debug("[sandboxer] wrote %s, %s and %s", conf_json, kernel, rootfs)


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
) -> tuple[Dict[str, Path], Callable[[], None]]:
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
    Tuple[Dict[str, Path], Callable[[], None]]
        Mapping of language name to created image directory path and a cleanup
        function that removes any temporary directories created by this
        function. Call the cleanup once the images are no longer needed.
    """
    check_platform()
    system = platform.system()

    def _noop() -> None:
        pass

    cleanup: Callable[[], None] = _noop
    if base_dir is None:
        tmp = tempfile.TemporaryDirectory()
        base = Path(tmp.name)

        def _cleanup() -> None:
            tmp.cleanup()

        cleanup = _cleanup
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
    return images, cleanup


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
    cmd = ["firecracker", "--no-api", "--config-file", str(config)]
    logger.info("[sandboxer] launching Firecracker: %s", " ".join(cmd))
    return subprocess.run(cmd, check=True)


def launch_container(image_dir: Path) -> subprocess.CompletedProcess:
    """Launch a container using ``image_dir/container.json``.

    On Linux this uses ``runc`` directly.  Other platforms fall back to Docker
    since Firecracker and OCI runtimes are typically unavailable.
    """

    config = image_dir / "container.json"
    if not config.is_file():
        raise ValueError(f"missing container.json in {image_dir}")
    try:
        data = json.loads(config.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid container.json in {image_dir}") from exc
    if "language" not in data:
        raise ValueError(f"container.json missing 'language' key in {image_dir}")
    language = data["language"]

    if platform.system() == "Linux":
        cmd = ["runc", "run", language]
    else:
        cmd = ["docker", "run", language]

    logger.info("[sandboxer] launching container: %s", " ".join(cmd))
    return subprocess.run(cmd, check=True)
