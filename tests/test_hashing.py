import hashlib
from pathlib import Path
import zipfile

import pytest

from egg.hashing import (
    sha256_file,
    compute_hashes,
    write_hashes_file,
    load_hashes,
    verify_hashes,
    verify_archive,
)
from egg.composer import compose


def test_sha256_file(tmp_path: Path) -> None:
    f = tmp_path / "foo.txt"
    f.write_text("hello")
    expected = hashlib.sha256(b"hello").hexdigest()
    assert sha256_file(f) == expected


def test_compute_write_load_verify(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("A")
    b.write_text("B")

    hashes = compute_hashes([a, b])
    assert hashes["a.txt"] == sha256_file(a)
    assert hashes["b.txt"] == sha256_file(b)

    hashes_file = tmp_path / "hashes.yaml"
    write_hashes_file(hashes, hashes_file)
    loaded = load_hashes(hashes_file)
    assert loaded == hashes
    assert verify_hashes(tmp_path, loaded)

    # corrupt a file and verification should fail
    b.write_text("X")
    assert not verify_hashes(tmp_path, loaded)


def test_duplicate_basenames(tmp_path: Path) -> None:
    one = tmp_path / "one"
    two = tmp_path / "two"
    one.mkdir()
    two.mkdir()
    f1 = one / "dup.txt"
    f2 = two / "dup.txt"
    f1.write_text("A")
    f2.write_text("B")
    with pytest.raises(ValueError):
        compute_hashes([f1, f2])


def test_verify_archive_with_extra_file(tmp_path: Path) -> None:
    """Archives containing files not listed in hashes.yaml should fail."""
    output = tmp_path / "demo.egg"
    compose(
        Path(__file__).resolve().parent.parent / "examples" / "manifest.yaml", output
    )

    # Append an extra file not recorded in hashes.yaml
    with zipfile.ZipFile(output, "a") as zf:
        info = zipfile.ZipInfo("extra.txt")
        info.date_time = (1980, 1, 1, 0, 0, 0)
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, b"extra")

    assert not verify_archive(output)
