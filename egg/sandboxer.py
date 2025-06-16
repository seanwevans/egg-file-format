"""Minimal sandbox preparation utilities."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Dict

from .manifest import Manifest

logger = logging.getLogger(__name__)


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
        img_dir.mkdir(parents=True, exist_ok=True)
        config_path = img_dir / "microvm.json"
        config_path.write_text(json.dumps({"language": lang}))
        logger.info("[sandboxer] prepared %s image at %s", lang, img_dir)
        images[lang] = img_dir
    return images
