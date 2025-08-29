import os
import sys
from pathlib import Path
import subprocess
import tempfile
import platform
import shutil
import pytest  # noqa: F401

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from egg.sandboxer import (
    build_microvm_image,
    launch_microvm,
    build_container_image,
    launch_container,
    prepare_images,
)  # noqa: E402
from egg.manifest import Manifest, Cell  # noqa: E402


def test_build_microvm_image(tmp_path: Path) -> None:
    build_microvm_image("python", tmp_path)
    assert (tmp_path / "microvm.json").is_file()
    conf = (tmp_path / "microvm.conf").read_text()
    assert conf.startswith("language: python")
    assert (tmp_path / "vmlinux").is_file()
    assert (tmp_path / "rootfs.ext4").is_file()


def test_launch_microvm(monkeypatch, tmp_path: Path):
    (tmp_path / "microvm.json").write_text("{}")
    called = []

    def fake_run(cmd, check=True):
        called.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = launch_microvm(tmp_path)
    assert called and "firecracker" in called[0][0]
    assert result.returncode == 0


def test_build_container_image(tmp_path: Path) -> None:
    build_container_image("python", tmp_path)
    assert (tmp_path / "container.json").is_file()
    assert (tmp_path / "container.conf").read_text().startswith("language: python")


def test_launch_container(monkeypatch, tmp_path: Path):
    (tmp_path / "container.json").write_text('{"language": "python"}')
    called = []

    def fake_run(cmd, check=True):
        called.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/runc")
    result = launch_container(tmp_path)
    assert called and "runc" in called[0][0]
    assert result.returncode == 0


def test_prepare_images_uses_tempdir(monkeypatch, tmp_path: Path):
    manifest = Manifest(
        name="ex",
        description="d",
        cells=[Cell(language="python", source="a.py")],
    )

    class DummyTempDir:
        def __init__(self):
            self.name = str(tmp_path / "tmp")
            Path(self.name).mkdir()
            self.cleaned = False

        def cleanup(self):
            self.cleaned = True

    dummy = DummyTempDir()
    monkeypatch.setattr(tempfile, "TemporaryDirectory", lambda: dummy)

    images, cleanup = prepare_images(manifest, None)
    assert images["python"].parent == Path(dummy.name)
    cleanup()
    assert dummy.cleaned


def test_prepare_images_skips_duplicate(tmp_path: Path):
    manifest = Manifest(
        name="ex",
        description="d",
        cells=[
            Cell(language="python", source="a.py"),
            Cell(language="python", source="b.py"),
        ],
    )
    images, cleanup = prepare_images(manifest, tmp_path)
    assert list(images.keys()) == ["python"]
    cleanup()


def test_prepare_images_tempdir_cleanup(tmp_path: Path):
    manifest = Manifest(
        name="ex",
        description="d",
        cells=[Cell(language="python", source="a.py")],
    )
    images, cleanup = prepare_images(manifest)
    base = images["python"].parent
    assert base.exists()
    cleanup()
    assert not base.exists()


def test_check_platform_unsupported(monkeypatch):
    import importlib
    import egg.sandboxer as sb

    monkeypatch.setattr(sb.platform, "system", lambda: "Unknown")
    sb = importlib.reload(sb)
    with pytest.raises(RuntimeError, match="Unsupported platform"):
        sb.check_platform()
