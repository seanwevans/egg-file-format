import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from egg.runtime_fetcher import fetch_runtime_blocks  # noqa: E402


def test_fetch_local_dependencies(tmp_path: Path) -> None:
    dep1 = tmp_path / "python.img"
    dep2 = tmp_path / "r.img"
    dep1.write_text("py")
    dep2.write_text("r")
    (tmp_path / "code.py").write_text("print('hi')\n")

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        f"""
name: Example
description: desc
cells:
  - language: python
    source: code.py
dependencies:
  - {dep1.name}
  - {dep2.name}
"""
    )

    paths = fetch_runtime_blocks(manifest)
    assert paths == [dep1.resolve(), dep2.resolve()]


def test_missing_dependency(tmp_path: Path) -> None:
    (tmp_path / "code.py").write_text("print('hi')\n")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: code.py
dependencies:
  - missing.img
"""
    )

    with pytest.raises(FileNotFoundError):
        fetch_runtime_blocks(manifest)


def test_container_dependencies(tmp_path: Path) -> None:
    """Container-style specs should be returned without file checks."""
    (tmp_path / "code.py").write_text("print('hi')\n")

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: code.py
dependencies:
  - python:3.11
  - r:4.3
"""
    )

    paths = fetch_runtime_blocks(manifest)
    assert paths == ["python:3.11", "r:4.3"]


def _start_server(directory: Path):
    """Return a running HTTP server serving ``directory``."""
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    import threading

    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer(("localhost", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_registry_download_env(monkeypatch, tmp_path: Path) -> None:
    img = tmp_path / "python:3.11.img"
    img.write_text("image")
    (tmp_path / "code.py").write_text("print('hi')\n")
    server, thread = _start_server(tmp_path)
    registry_url = f"http://localhost:{server.server_address[1]}"
    monkeypatch.setenv("EGG_REGISTRY_URL", registry_url)

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: code.py
dependencies:
  - python:3.11
"""
    )

    paths = fetch_runtime_blocks(manifest)
    expected = tmp_path / "python_3.11.img"
    server.shutdown()
    thread.join()
    assert paths == [expected]
    assert expected.read_text() == "image"


def test_registry_download_config(monkeypatch, tmp_path: Path) -> None:
    img_dir = tmp_path / "registry"
    img_dir.mkdir()
    (img_dir / "r:4.3.img").write_text("rimage")
    (tmp_path / "code.py").write_text("print('hi')\n")
    server, thread = _start_server(img_dir)
    registry_url = f"http://localhost:{server.server_address[1]}"

    home = tmp_path / "home"
    home.mkdir()
    (home / ".egg_registry").write_text(registry_url)
    monkeypatch.setenv("HOME", str(home))

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: code.py
dependencies:
  - r:4.3
"""
    )

    paths = fetch_runtime_blocks(manifest)
    expected = tmp_path / "r_4.3.img"
    server.shutdown()
    thread.join()
    assert paths == [expected]
    assert expected.read_text() == "rimage"


def test_registry_traversal_rejected(monkeypatch, tmp_path: Path) -> None:
    """Path traversal in container specs should raise ``ValueError``."""
    (tmp_path / "code.py").write_text("print('hi')\n")
    monkeypatch.setenv("EGG_REGISTRY_URL", "http://example.com")

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: code.py
dependencies:
  - ../evil:1
"""
    )

    with pytest.raises(ValueError):
        fetch_runtime_blocks(manifest)
