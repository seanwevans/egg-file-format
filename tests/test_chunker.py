import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
import pytest  # noqa: E402
from egg.chunker import chunk  # noqa: E402


def test_chunk_deterministic(tmp_path: Path) -> None:
    data = b"abcdefghij"  # 10 bytes
    f = tmp_path / "data.bin"
    f.write_bytes(data)

    expected = [
        {"offset": 0, "size": 4},
        {"offset": 4, "size": 4},
        {"offset": 8, "size": 2},
    ]

    first = chunk(f, chunk_size=4)
    second = chunk(f, chunk_size=4)
    assert first == expected
    assert second == expected


def test_chunk_invalid_size_zero(tmp_path: Path) -> None:
    f = tmp_path / "data.bin"
    f.write_bytes(b"hi")
    with pytest.raises(ValueError):
        chunk(f, chunk_size=0)


def test_chunk_invalid_size_negative(tmp_path: Path) -> None:
    f = tmp_path / "data.bin"
    f.write_bytes(b"hi")
    with pytest.raises(ValueError):
        chunk(f, chunk_size=-1)
