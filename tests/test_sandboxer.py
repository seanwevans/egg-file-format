import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from egg.manifest import Manifest, Cell  # noqa: E402
from egg.sandboxer import prepare_images  # noqa: E402



def test_prepare_images_writes_config(tmp_path: Path) -> None:

    manifest = Manifest(
        name="Example",
        description="desc",
        cells=[
            Cell(language="python", source="hello.py"),
            Cell(language="r", source="hello.R"),
        ],
    )

    images = prepare_images(manifest, tmp_path)

    assert set(images.keys()) == {"python", "r"}
    for lang, path in images.items():
        assert path.is_dir()
        config = path / "microvm.json"
        assert config.is_file()
        assert config.read_text()

