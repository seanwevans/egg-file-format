"""Minimal sandbox preparation utilities."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Dict

from .manifest import Manifest

logger = logging.getLogger(__name__)


def build_microvm_image(language: str, dest: Path) -> None:
    """Create a placeholder micro-VM image for ``language`` in ``dest``.

    A small ``microvm.conf`` file is written inside ``dest`` identifying the
    runtime. Future versions will build an actual VM image.

    Parameters
    ----------
    language:
        Name of the runtime language.
    dest:
        Directory where the image should be created.
    """

    dest.mkdir(parents=True, exist_ok=True)
    config = dest / "microvm.conf"
    config.write_text(f"language: {language}\n", encoding="utf-8")
    logger.debug("[sandboxer] wrote %s", config)


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
    if base_dir is None:
        base = Path(tempfile.mkdtemp())
    else:
        base = Path(base_dir)
    images: Dict[str, Path] = {}
    for cell in manifest.cells:
        lang = cell.language.lower()
        if lang in images:
            continue
        img_dir = base / f"{lang}-image"

        build_microvm_image(lang, img_dir)

        logger.info("[sandboxer] prepared %s image at %s", lang, img_dir)
        images[lang] = img_dir
    return images
