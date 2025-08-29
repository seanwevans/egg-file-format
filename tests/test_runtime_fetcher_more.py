import hashlib
import io
import urllib.error
from pathlib import Path

import pytest

import egg.runtime_fetcher as rf


def test_download_container_cached(monkeypatch, tmp_path: Path) -> None:
    dest = tmp_path / "python.img"
    data = b"cached"
    dest.write_bytes(data)
    called = []

    def fail(*args, **kwargs):
        called.append(True)
        raise AssertionError("urlopen should not be called")

    try:
        fail(None)
    except AssertionError:
        pass
    called.clear()

    monkeypatch.setattr(rf, "urlopen", fail)
    digest = hashlib.sha256(data).hexdigest()
    result = rf._download_container(
        "python:3.11", dest, "http://example.com", expected_digest=digest
    )
    assert result == dest
    assert not called


def test_download_container_refresh_if_no_digest(monkeypatch, tmp_path: Path) -> None:
    dest = tmp_path / "python.img"
    dest.write_text("old")

    class Dummy(io.BytesIO):
        def __init__(self, data: bytes) -> None:  # noqa: D401 - simple init
            super().__init__(data)
            self.headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

    called = []

    def fake_urlopen(url, *, timeout=None):
        called.append(url)
        return Dummy(b"new")

    monkeypatch.setattr(rf, "urlopen", fake_urlopen)
    rf._download_container("python:3.11", dest, "http://example.com")
    assert dest.read_bytes() == b"new"
    assert called


def test_download_container_refresh_on_mismatch(monkeypatch, tmp_path: Path) -> None:
    dest = tmp_path / "python.img"
    dest.write_text("old")
    data = b"new"

    class Dummy(io.BytesIO):
        def __init__(self, data: bytes) -> None:  # noqa: D401 - simple init
            super().__init__(data)
            self.headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

    called = []

    def fake_urlopen(url, *, timeout=None):
        called.append(url)
        return Dummy(data)

    monkeypatch.setattr(rf, "urlopen", fake_urlopen)
    digest = hashlib.sha256(data).hexdigest()
    rf._download_container(
        "python:3.11", dest, "http://example.com", expected_digest=digest
    )
    assert dest.read_bytes() == data
    assert called


def test_download_container_timeout(monkeypatch, tmp_path: Path) -> None:
    dest = tmp_path / "python.img"

    class Dummy(io.BytesIO):
        def __init__(self, data: bytes) -> None:  # noqa: D401 - simple init
            super().__init__(data)
            self.headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

    def fake_urlopen(url, *, timeout=None):
        assert timeout == 5
        return Dummy(b"data")

    monkeypatch.setattr(rf, "urlopen", fake_urlopen)
    result = rf._download_container(
        "python:3.11", dest, "http://example.com", timeout=5
    )
    assert dest.read_bytes() == b"data"
    assert result == dest


def test_download_container_repo(monkeypatch, tmp_path: Path) -> None:
    dest = tmp_path / "library_python_3.11.img"

    class Dummy(io.BytesIO):
        def __init__(self, data: bytes) -> None:
            super().__init__(data)
            self.headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

    called = []

    def fake_urlopen(url, *, timeout=None):
        called.append(url)
        return Dummy(b"data")

    monkeypatch.setattr(rf, "urlopen", fake_urlopen)
    result = rf._download_container("library/python:3.11", dest, "http://example.com")
    assert called == ["http://example.com/library/python%3A3.11.img"]
    assert dest.read_bytes() == b"data"
    assert result == dest


def test_fetch_empty_manifest(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    path.write_text("")
    assert rf.fetch_runtime_blocks(path) == []


def test_fetch_container_escape(monkeypatch, tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: ex
description: d
cells: []
dependencies:
  - python:3.11
"""
    )

    monkeypatch.setenv("EGG_REGISTRY_URL", "http://example.com")
    monkeypatch.setattr(rf, "_is_relative_to", lambda *a: False)
    with pytest.raises(ValueError, match="escapes manifest directory"):
        rf.fetch_runtime_blocks(manifest)


def test_download_container_escape(monkeypatch, tmp_path: Path) -> None:
    dest = tmp_path / "link" / "evil.img"
    monkeypatch.setattr(rf, "_is_relative_to", lambda *a: False)
    with pytest.raises(ValueError):
        rf._download_container("python:3.11", dest, "http://example.com")


def test_download_container_interrupted(monkeypatch, tmp_path: Path) -> None:
    dest = tmp_path / "python.img"
    tmp = dest.with_suffix(".tmp")

    class Failing(io.BytesIO):
        def __init__(self) -> None:  # noqa: D401 - simple init
            super().__init__(b"partial")
            self._sent = False
            self.headers = {}

        def read(self, *args, **kwargs):  # noqa: D401 - match signature
            if not self._sent:
                self._sent = True
                return super().read(*args, **kwargs)
            raise urllib.error.URLError("boom")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

    monkeypatch.setattr(rf, "urlopen", lambda *a, **kw: Failing())
    with pytest.raises(RuntimeError):
        rf._download_container("python:3.11", dest, "http://example.com")

    assert not dest.exists()
    assert not tmp.exists()


def test_download_container_truncated(monkeypatch, tmp_path: Path) -> None:
    dest = tmp_path / "python.img"
    tmp = dest.with_suffix(".tmp")

    class Truncated:
        def __init__(self) -> None:  # noqa: D401 - simple init
            self._io = io.BytesIO(b"data")
            self.headers = {"Content-Length": "8"}

        def read(self, *args, **kwargs):  # noqa: D401 - match signature
            return self._io.read(*args, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

    monkeypatch.setattr(rf, "urlopen", lambda *a, **kw: Truncated())
    with pytest.raises(RuntimeError, match="expected 8 bytes"):
        rf._download_container("python:3.11", dest, "http://example.com")

    assert not dest.exists()
    assert not tmp.exists()


def test_download_container_hash_failure(monkeypatch, tmp_path: Path) -> None:
    dest = tmp_path / "python.img"
    tmp = dest.with_suffix(".tmp")
    data = b"data"
    wrong = hashlib.sha256(b"other").hexdigest()

    class Dummy:
        def __init__(self) -> None:  # noqa: D401 - simple init
            self._io = io.BytesIO(data)
            self.headers = {"Content-Length": str(len(data))}

        def read(self, *args, **kwargs):  # noqa: D401 - match signature
            return self._io.read(*args, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

    monkeypatch.setattr(rf, "urlopen", lambda *a, **kw: Dummy())
    with pytest.raises(RuntimeError, match="Checksum mismatch"):
        rf._download_container(
            "python:3.11",
            dest,
            "http://example.com",
            expected_digest=wrong,
        )

    assert not dest.exists()
    assert not tmp.exists()
