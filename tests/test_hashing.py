import hashlib
from nacl.signing import SigningKey
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
    sign_hashes,
    DEFAULT_PRIVATE_KEY,
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


def test_compute_hashes_base_dir_not_parent(tmp_path: Path) -> None:
    """Non-parent ``base_dir`` should raise ``ValueError``."""
    foo = tmp_path / "foo.txt"
    foo.write_text("A")
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(ValueError):
        compute_hashes([foo], base_dir=other)


def test_load_hashes_requires_mapping(tmp_path: Path) -> None:
    """Non-mapping YAML content should raise ValueError."""
    path = tmp_path / "hashes.yaml"
    path.write_text("- a\n- b\n")
    with pytest.raises(ValueError):
        load_hashes(path)


def test_load_hashes_non_string_value(tmp_path: Path) -> None:
    """Non-string hash values should raise ValueError."""
    path = tmp_path / "hashes.yaml"
    path.write_text("foo: 1\n")
    with pytest.raises(ValueError):
        load_hashes(path)


def test_verify_archive_with_extra_file(tmp_path: Path) -> None:
    """Archives containing files not listed in hashes.yaml should fail."""
    output = tmp_path / "demo.egg"
    compose(
        Path(__file__).resolve().parent.parent / "examples" / "manifest.yaml",
        output,
        dependencies=[],
    )

    # Append an extra file not recorded in hashes.yaml
    with zipfile.ZipFile(output, "a") as zf:
        info = zipfile.ZipInfo("extra.txt")
        info.date_time = (1980, 1, 1, 0, 0, 0)
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, b"extra")

    assert not verify_archive(output)


def test_sign_hashes_and_verify_signature(tmp_path: Path) -> None:
    data = tmp_path / "hashes.yaml"
    data.write_text("a: 1\n")
    sig = sign_hashes(data, private_key=DEFAULT_PRIVATE_KEY)
    sk = SigningKey(hashlib.sha256(DEFAULT_PRIVATE_KEY).digest())
    expected = sk.sign(data.read_bytes()).signature.hex()
    assert sig == expected


def test_verify_archive_bad_signature(tmp_path: Path) -> None:
    output = tmp_path / "demo.egg"
    compose(
        Path(__file__).resolve().parent.parent / "examples" / "manifest.yaml",
        output,
        dependencies=[],
    )

    # Tamper signature
    with zipfile.ZipFile(output, "a") as zf:
        zf.writestr("hashes.sig", "0" * 128)

    assert not verify_archive(output)


def test_verify_archive_missing_hashes(tmp_path: Path) -> None:
    foo = tmp_path / "foo.txt"
    foo.write_text("data")
    archive = tmp_path / "demo.egg"
    with zipfile.ZipFile(archive, "w") as zf:
        zi = zipfile.ZipInfo(foo.name)
        zi.date_time = (1980, 1, 1, 0, 0, 0)
        zi.compress_type = zipfile.ZIP_DEFLATED
        with open(foo, "rb") as f:
            zf.writestr(zi, f.read())
    assert not verify_archive(archive)


def test_verify_archive_missing_file(tmp_path: Path) -> None:
    foo = tmp_path / "foo.txt"
    bar = tmp_path / "bar.txt"
    foo.write_text("A")
    bar.write_text("B")
    hashes = compute_hashes([foo, bar], base_dir=tmp_path)
    hashes_path = tmp_path / "hashes.yaml"
    write_hashes_file(hashes, hashes_path)
    sig_path = tmp_path / "hashes.sig"
    sig_path.write_text(sign_hashes(hashes_path, private_key=DEFAULT_PRIVATE_KEY))
    archive = tmp_path / "demo.egg"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in [foo, hashes_path, sig_path]:
            zi = zipfile.ZipInfo(path.name)
            zi.date_time = (1980, 1, 1, 0, 0, 0)
            zi.compress_type = zipfile.ZIP_DEFLATED
            with open(path, "rb") as f:
                zf.writestr(zi, f.read())
    assert not verify_archive(archive)


def test_hashing_import_guard(monkeypatch):
    """Missing PyYAML should raise a helpful error when importing hashing."""
    import builtins
    import importlib
    import sys

    import egg.hashing as hashing

    monkeypatch.delitem(sys.modules, "yaml", raising=False)

    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "yaml":
            raise ModuleNotFoundError
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ModuleNotFoundError) as exc:
        importlib.reload(hashing)
    assert str(exc.value) == (
        "PyYAML is required for egg hashing. Install with 'pip install PyYAML'"
    )


def test_sign_hashes_env_override(monkeypatch, tmp_path):
    """Setting EGG_PRIVATE_KEY changes the produced signature."""
    import importlib
    import egg.hashing as hashing

    data = tmp_path / "hashes.yaml"
    data.write_text("a: 1\n")

    default_sig = hashing.sign_hashes(data)

    monkeypatch.setenv("EGG_PRIVATE_KEY", "new-key")
    hashing = importlib.reload(hashing)

    sig = hashing.sign_hashes(data)
    sk = SigningKey(hashlib.sha256(b"new-key").digest())
    expected = sk.sign(data.read_bytes()).signature.hex()

    assert sig == expected
    assert sig != default_sig


def test_verify_archive_env_key(monkeypatch, tmp_path):
    """Verification should honor EGG_PUBLIC_KEY."""
    import importlib
    import egg.hashing as hashing

    sk = SigningKey(hashlib.sha256(b"secret").digest())
    monkeypatch.setenv("EGG_PRIVATE_KEY", "secret")
    monkeypatch.setenv("EGG_PUBLIC_KEY", sk.verify_key.encode().hex())
    hashing = importlib.reload(hashing)

    foo = tmp_path / "foo.txt"
    foo.write_text("data")
    hashes = hashing.compute_hashes([foo], base_dir=tmp_path)
    hashes_path = tmp_path / "hashes.yaml"
    hashing.write_hashes_file(hashes, hashes_path)
    sig = hashing.sign_hashes(hashes_path)
    sig_path = tmp_path / "hashes.sig"
    sig_path.write_text(sig)

    archive = tmp_path / "demo.egg"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in [foo, hashes_path, sig_path]:
            zi = zipfile.ZipInfo(path.name)
            zi.date_time = (1980, 1, 1, 0, 0, 0)
            zi.compress_type = zipfile.ZIP_DEFLATED
            with open(path, "rb") as f:
                zf.writestr(zi, f.read())

    assert hashing.verify_archive(archive)

    # Wrong key should fail verification
    other_vk = SigningKey(hashlib.sha256(b"other").digest()).verify_key.encode().hex()
    monkeypatch.setenv("EGG_PUBLIC_KEY", other_vk)
    hashing = importlib.reload(hashing)
    assert not hashing.verify_archive(archive)


def test_load_hashes_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "hashes.yaml"
    path.write_text("")
    assert load_hashes(path) == {}
