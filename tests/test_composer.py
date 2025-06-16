import pytest
from pathlib import Path
from egg.composer import _normalize_source


def test_normalize_source_absolute(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _normalize_source("/abs.py", tmp_path)
