import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from egg.manifest import Manifest, Cell  # noqa: E402
from egg.sandboxer import launch_container  # noqa: E402
import importlib
import platform


import pytest


@pytest.mark.parametrize(
    "os_name,conf_file",
    [
        ("Linux", "microvm.conf"),
        ("Darwin", "container.conf"),
        ("Windows", "container.conf"),
    ],
)
def test_prepare_images_writes_config(
    monkeypatch, tmp_path: Path, os_name: str, conf_file: str
) -> None:

    monkeypatch.setattr(platform, "system", lambda: os_name)
    import egg.sandboxer as sb

    importlib.reload(sb)

    manifest = Manifest(
        name="Example",
        description="desc",
        cells=[
            Cell(language="python", source="hello.py"),
            Cell(language="r", source="hello.R"),
        ],
    )

    images, cleanup = sb.prepare_images(manifest, tmp_path)
    cleanup()

    assert set(images.keys()) == {"python", "r"}
    for path in images.values():
        assert path.is_dir()
        config = path / conf_file
        assert config.is_file()
        assert config.read_text()


def test_launch_container_missing_config(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="container.json"):
        launch_container(tmp_path)


@pytest.mark.parametrize(
    "content, message", [("not json", "invalid"), ("{}", "language")]
)
def test_launch_container_corrupt_config(
    tmp_path: Path, content: str, message: str
) -> None:
    (tmp_path / "container.json").write_text(content)
    with pytest.raises(ValueError, match=message):
        launch_container(tmp_path)
