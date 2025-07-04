import os
import urllib.error
from pathlib import Path
import importlib
import io

import pytest

import egg.runtime_fetcher as rf


def test_download_container_cached(monkeypatch, tmp_path: Path) -> None:
    dest = tmp_path / "python.img"
    dest.write_text("cached")
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
    result = rf._download_container("python:3.11", dest, "http://example.com")
    assert result == dest
    assert not called


def test_download_container_timeout(monkeypatch, tmp_path: Path) -> None:
    dest = tmp_path / "python.img"

    class Dummy(io.BytesIO):
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
