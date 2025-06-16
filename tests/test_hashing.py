import hashlib
from pathlib import Path

import pytest

from egg.hashing import sha256_file, compute_hashes, write_hashes_file, load_hashes, verify_hashes


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
