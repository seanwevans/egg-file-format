import os
import sys
import zipfile
import hashlib
import yaml
from nacl.signing import SigningKey
import pytest
import logging
import subprocess
import shutil
from pathlib import Path
import platform
import importlib

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
import egg_cli  # noqa: E402
from egg.hashing import verify_archive, sign_hashes  # noqa: E402


def test_build(monkeypatch, tmp_path, caplog):
    output = tmp_path / "demo.egg"
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "--verbose",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
        ],
    )
    egg_cli.main()

    expected = (
        f"[build] Building egg from {os.path.join('examples', 'manifest.yaml')} "
        f"-> {output}"
    )
    assert expected in caplog.text

    assert output.is_file()
    with zipfile.ZipFile(output) as zf:
        names = zf.namelist()
    assert "hello.py" in names
    assert "hello.R" in names


def test_build_precompute(monkeypatch, tmp_path):
    output = tmp_path / "demo.egg"

    called = []

    def fake_precompute(path, timeout=None):
        called.append(Path(path))

    monkeypatch.setattr(egg_cli, "precompute_cells", fake_precompute)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
            "--precompute",
        ],
    )
    egg_cli.main()

    assert len(called) == 1
    assert output.is_file()


def test_build_force_overwrite(monkeypatch, tmp_path):
    """Building should require --force to overwrite existing output."""
    output = tmp_path / "demo.egg"
    base = [
        "egg_cli.py",
        "build",
        "--manifest",
        os.path.join("examples", "manifest.yaml"),
        "--output",
        str(output),
    ]

    monkeypatch.setattr(sys, "argv", base)
    egg_cli.main()
    assert output.is_file()

    monkeypatch.setattr(sys, "argv", base)
    with pytest.raises(SystemExit):
        egg_cli.main()

    monkeypatch.setattr(sys, "argv", base + ["--force"])
    egg_cli.main()
    assert output.is_file()


@pytest.mark.parametrize(
    "os_name,conf_file",
    [
        ("Linux", "microvm.conf"),
        ("Darwin", "container.conf"),
        ("Windows", "container.conf"),
    ],
)
def test_hatch(monkeypatch, tmp_path, caplog, os_name, conf_file):
    egg_path = tmp_path / "demo.egg"

    # build an egg first
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(egg_path),
        ],
    )
    egg_cli.main()

    calls: list[list[str]] = []
    sb_calls: list[list[str]] = []
    sb_configs: list[bool] = []

    def fake_run(cmd, check=True):
        calls.append(cmd)

    monkeypatch.setattr(platform, "system", lambda: os_name)
    import egg.sandboxer as sandboxer

    importlib.reload(sandboxer)

    def fake_prepare(manifest, dest):
        images = sandboxer.prepare_images(manifest, dest)
        sb_calls.append(sorted(images.keys()))
        sb_configs.append(all((p / conf_file).is_file() for p in images.values()))
        return images

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda cmd: cmd)
    monkeypatch.setattr(egg_cli, "prepare_images", fake_prepare)

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        ["egg_cli.py", "--verbose", "hatch", "--egg", str(egg_path)],
    )
    egg_cli.main()

    assert any(
        cmd[0] == sys.executable and cmd[1].endswith("hello.py") for cmd in calls
    )
    assert any(cmd[0] == "Rscript" and cmd[1].endswith("hello.R") for cmd in calls)
    assert f"[hatch] Completed running {egg_path}" in caplog.text
    assert sb_calls == [["python", "r"]]
    assert sb_configs == [True]


def test_hatch_no_sandbox(monkeypatch, tmp_path, caplog):
    egg_path = tmp_path / "demo.egg"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(egg_path),
        ],
    )
    egg_cli.main()

    called = []

    def fake_prepare(*a, **kw):
        called.append(True)

    # execute once to cover the function body
    fake_prepare(None, None)
    called.clear()

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: None)
    monkeypatch.setattr(shutil, "which", lambda cmd: cmd)
    monkeypatch.setattr(egg_cli, "prepare_images", fake_prepare)

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        ["egg_cli.py", "--verbose", "hatch", "--no-sandbox", "--egg", str(egg_path)],
    )
    egg_cli.main()

    assert not called
    assert "[hatch] Running without sandbox (unsafe)" in caplog.text


def test_hatch_bash(monkeypatch, tmp_path, caplog):
    """Hatching should invoke bash for bash cells."""
    script = tmp_path / "hello.sh"
    script.write_text("echo hi\n")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: bash
    source: hello.sh
"""
    )
    egg_path = tmp_path / "demo.egg"

    # build the egg
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            str(manifest),
            "--output",
            str(egg_path),
        ],
    )
    egg_cli.main()

    calls: list[list[str]] = []

    def fake_run(cmd, check=True):
        calls.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda cmd: cmd)

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        ["egg_cli.py", "--verbose", "hatch", "--egg", str(egg_path)],
    )
    egg_cli.main()

    assert any(cmd[0] == "bash" and cmd[1].endswith("hello.sh") for cmd in calls)
    assert f"[hatch] Completed running {egg_path}" in caplog.text


def test_hatch_custom_commands(monkeypatch, tmp_path):
    """Environment variables should override runtime command paths."""
    egg_path = tmp_path / "demo.egg"

    # Build the egg first
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(egg_path),
        ],
    )
    egg_cli.main()

    calls: list[list[str]] = []

    def fake_run(cmd, check=True):
        calls.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda cmd: cmd)
    monkeypatch.setenv("EGG_CMD_PYTHON", "/custom/python")
    monkeypatch.setenv("EGG_CMD_R", "/custom/Rscript")

    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "hatch", "--egg", str(egg_path)])
    egg_cli.main()

    assert any(
        cmd[0] == "/custom/python" and cmd[1].endswith("hello.py") for cmd in calls
    )
    assert any(
        cmd[0] == "/custom/Rscript" and cmd[1].endswith("hello.R") for cmd in calls
    )


def test_hatch_custom_commands_with_args(monkeypatch, tmp_path):
    egg_path = tmp_path / "demo.egg"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(egg_path),
        ],
    )
    egg_cli.main()

    calls: list[list[str]] = []

    def fake_run(cmd, check=True):
        calls.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda cmd: cmd)
    monkeypatch.setenv("EGG_CMD_PYTHON", "python -u")

    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "hatch", "--egg", str(egg_path)])
    egg_cli.main()

    assert any(cmd[:2] == ["python", "-u"] for cmd in calls)


def test_hatch_unknown_language(monkeypatch, tmp_path):
    """Unknown cell languages should produce a clear error."""
    src = tmp_path / "hello.foo"
    src.write_text("echo hi\n")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: foo
    source: hello.foo
"""
    )
    egg_path = tmp_path / "demo.egg"
    # build
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            str(manifest),
            "--output",
            str(egg_path),
        ],
    )
    egg_cli.main()

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: None)
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "hatch", "--egg", str(egg_path)])
    with pytest.raises(SystemExit):
        egg_cli.main()


def test_hatch_missing_runtime(monkeypatch, tmp_path):
    """Hatching should fail if the required runtime command is missing."""
    egg_path = tmp_path / "demo.egg"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(egg_path),
        ],
    )
    egg_cli.main()

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: None)

    def fake_which(cmd: str):
        return None if cmd == "Rscript" else cmd

    monkeypatch.setattr(shutil, "which", fake_which)

    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "hatch", "--egg", str(egg_path)])
    with pytest.raises(SystemExit) as exc:
        egg_cli.main()
    assert "Rscript" in str(exc.value)


def test_requires_subcommand(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["egg_cli.py"])
    with pytest.raises(SystemExit) as exc:
        egg_cli.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "the following arguments are required: command" in captured.err


def test_help_without_subcommand(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["egg_cli.py"])
    with pytest.raises(SystemExit):
        egg_cli.main()
    out = capsys.readouterr().err
    assert out.startswith("usage:")


def test_build_missing_source(monkeypatch, tmp_path):
    """Building should fail with a clear error when a source file is missing."""
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: missing.py
"""
    )
    output = tmp_path / "demo.egg"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
    )
    with pytest.raises(FileNotFoundError) as exc:
        egg_cli.main()
    msg = str(exc.value)
    assert "missing.py" in msg
    assert str(manifest) in msg


def test_build_missing_manifest(monkeypatch, tmp_path):
    """Building should raise FileNotFoundError when manifest is missing."""
    manifest = tmp_path / "does_not_exist.yaml"
    output = tmp_path / "demo.egg"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
    )
    with pytest.raises(FileNotFoundError) as exc:
        egg_cli.main()
    assert str(manifest) in str(exc.value)


def test_build_rejects_unsafe_path(monkeypatch, tmp_path):
    manifest_dir = tmp_path / "sub"
    manifest_dir.mkdir()
    manifest = manifest_dir / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: ../evil.py
"""
    )
    output = tmp_path / "demo.egg"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
    )
    with pytest.raises(ValueError):
        egg_cli.main()


def test_build_invalid_manifest(monkeypatch, tmp_path):
    """Invalid manifests should raise ``ValueError`` during build."""
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
cells:
  - language: python
    source: hello.py
"""
    )  # description missing
    output = tmp_path / "demo.egg"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
    )
    with pytest.raises(ValueError):
        egg_cli.main()


def test_version_option(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "--version"])
    with pytest.raises(SystemExit):
        egg_cli.main()
    captured = capsys.readouterr()
    assert egg_cli.__version__ in captured.out


def test_verbose_after_subcommand(monkeypatch, tmp_path, caplog):
    """Global options like ``--verbose`` should work after subcommands."""
    output = tmp_path / "demo.egg"
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
            "--verbose",
        ],
    )
    egg_cli.main()
    assert output.is_file()


def test_hashes_in_archive(monkeypatch, tmp_path):
    output = tmp_path / "demo.egg"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
        ],
    )
    egg_cli.main()

    with zipfile.ZipFile(output) as zf:
        names = zf.namelist()
        assert "hashes.yaml" in names
        assert "hashes.sig" in names
        with zf.open("hashes.yaml") as f:
            hashes = yaml.safe_load(f)
        for name, digest in hashes.items():
            with zf.open(name) as fh:
                data = fh.read()
            assert hashlib.sha256(data).hexdigest() == digest


def test_build_includes_dependency_files(monkeypatch, tmp_path):
    dep = tmp_path / "python.img"
    dep.write_text("py")
    src = tmp_path / "hello.py"
    src.write_text("print('hi')\n")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
dependencies:
  - python.img
cells:
  - language: python
    source: hello.py
"""
    )
    output = tmp_path / "demo.egg"
    monkeypatch.setattr(
        sys,
        "argv",
        ["egg_cli.py", "build", "--manifest", str(manifest), "--output", str(output)],
    )
    egg_cli.main()

    assert verify_archive(output)
    with zipfile.ZipFile(output) as zf:
        names = set(zf.namelist())
    assert "runtime/python.img" in names


def test_deterministic_build(monkeypatch, tmp_path):
    base_args = [
        "egg_cli.py",
        "build",
        "--manifest",
        os.path.join("examples", "manifest.yaml"),
    ]

    out1 = tmp_path / "one.egg"
    out2 = tmp_path / "two.egg"

    monkeypatch.setattr(sys, "argv", base_args + ["--output", str(out1)])
    egg_cli.main()

    monkeypatch.setattr(sys, "argv", base_args + ["--output", str(out2)])
    egg_cli.main()

    assert out1.read_bytes() == out2.read_bytes()


def test_verify_subcommand(monkeypatch, tmp_path, caplog):
    output = tmp_path / "demo.egg"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
        ],
    )
    egg_cli.main()

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        ["egg_cli.py", "--verbose", "verify", "--egg", str(output)],
    )
    egg_cli.main()
    assert f"[verify] {output} verified successfully" in caplog.text


def test_verify_failure(monkeypatch, tmp_path):
    output = tmp_path / "demo.egg"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
        ],
    )
    egg_cli.main()

    # Corrupt the archive
    with zipfile.ZipFile(output, "r") as zf:
        contents = {name: zf.read(name) for name in zf.namelist()}
    contents["hello.py"] = b"print('tampered')\n"
    with zipfile.ZipFile(output, "w") as zf:
        for name, data in contents.items():
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)

    monkeypatch.setattr(
        sys,
        "argv",
        ["egg_cli.py", "verify", "--egg", str(output)],
    )
    with pytest.raises(SystemExit):
        egg_cli.main()


def test_verify_bad_signature(monkeypatch, tmp_path):
    output = tmp_path / "demo.egg"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
        ],
    )
    egg_cli.main()

    with zipfile.ZipFile(output, "a") as zf:
        zf.writestr("hashes.sig", "0" * 128)

    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "verify", "--egg", str(output)])
    with pytest.raises(SystemExit):
        egg_cli.main()


def test_build_verification_success(monkeypatch, tmp_path):
    output = tmp_path / "demo.egg"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
        ],
    )
    egg_cli.main()

    assert output.is_file()
    assert verify_archive(output)


def test_build_with_signing_key(monkeypatch, tmp_path):
    output = tmp_path / "demo.egg"
    key = tmp_path / "key.txt"
    key.write_text("secret")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
            "--private-key",
            str(key),
        ],
    )
    egg_cli.main()

    assert output.is_file()
    assert not verify_archive(output)
    pub = SigningKey(hashlib.sha256(key.read_bytes()).digest()).verify_key.encode()
    assert verify_archive(output, public_key=pub)


def test_verify_subcommand_signing_key(monkeypatch, tmp_path, caplog):
    output = tmp_path / "demo.egg"
    key = tmp_path / "key.txt"
    key.write_text("secret")
    pub = SigningKey(hashlib.sha256(key.read_bytes()).digest()).verify_key.encode()
    pub_path = tmp_path / "pub.key"
    pub_path.write_bytes(pub)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
            "--private-key",
            str(key),
        ],
    )
    egg_cli.main()

    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "verify", "--egg", str(output)])
    with pytest.raises(SystemExit):
        egg_cli.main()

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "--verbose",
            "verify",
            "--egg",
            str(output),
            "--public-key",
            str(pub_path),
        ],
    )
    egg_cli.main()
    assert f"[verify] {output} verified successfully" in caplog.text


def test_build_detects_tampering(monkeypatch, tmp_path):
    output = tmp_path / "demo.egg"

    original = egg_cli.compose

    def tamper(manifest, out, *, dependencies=None, private_key=None):
        original(manifest, out, dependencies=dependencies, private_key=private_key)
        with zipfile.ZipFile(out, "r") as zf:
            contents = {name: zf.read(name) for name in zf.namelist()}
        contents["hello.py"] = b"print('tampered')\n"
        with zipfile.ZipFile(out, "w") as zf:
            for name, data in contents.items():
                info = zipfile.ZipInfo(name)
                info.date_time = (1980, 1, 1, 0, 0, 0)
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, data)

    monkeypatch.setattr(egg_cli, "compose", tamper)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        egg_cli.main()
    assert "Hash verification failed" in str(exc.value)
    assert not output.exists()


def test_preserve_relative_paths(monkeypatch, tmp_path):
    """Files in subdirectories should retain their paths inside the archive."""
    a = tmp_path / "a" / "hello.py"
    b = tmp_path / "b" / "hello.py"
    a.parent.mkdir()
    b.parent.mkdir()
    a.write_text("print('a')\n")
    b.write_text("print('b')\n")

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
cells:
  - language: python
    source: a/hello.py
  - language: python
    source: b/hello.py
"""
    )

    output = tmp_path / "demo.egg"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
    )
    egg_cli.main()

    with zipfile.ZipFile(output) as zf:
        names = set(zf.namelist())
    assert "a/hello.py" in names
    assert "b/hello.py" in names


def test_info_subcommand(monkeypatch, tmp_path, capsys):
    """The info command should print manifest details."""
    egg_path = tmp_path / "demo.egg"

    # build an egg
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(egg_path),
        ],
    )
    egg_cli.main()
    capsys.readouterr()  # clear build output

    # run info
    monkeypatch.setattr(
        sys,
        "argv",
        ["egg_cli.py", "info", "--egg", str(egg_path)],
    )
    egg_cli.main()
    out = capsys.readouterr().out
    assert "Demo Notebook" in out
    assert "hello.py" in out
    assert "hello.R" in out


def test_info_dependencies_permissions(monkeypatch, tmp_path, capsys):
    """Advanced manifest fields should be listed by info."""
    egg_path = tmp_path / "adv.egg"

    # build using advanced manifest with deps and permissions
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "advanced_manifest.yaml"),
            "--output",
            str(egg_path),
        ],
    )
    egg_cli.main()
    capsys.readouterr()

    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "info", "--egg", str(egg_path)])
    egg_cli.main()
    out = capsys.readouterr().out
    assert "Dependencies:" in out
    assert "python:3.11" in out
    assert "Permissions:" in out
    assert "network: True" in out


def test_hatch_missing_egg(monkeypatch):
    missing = Path("nope.egg")
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "hatch", "--egg", str(missing)])
    with pytest.raises(SystemExit) as exc:
        egg_cli.main()
    assert str(missing) in str(exc.value)


def test_hatch_bad_signature(monkeypatch, tmp_path):
    egg_path = tmp_path / "demo.egg"
    # build
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(egg_path),
        ],
    )
    egg_cli.main()

    # tamper signature
    with zipfile.ZipFile(egg_path, "a") as zf:
        zf.writestr("hashes.sig", "0" * 128)

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: None)
    monkeypatch.setattr(shutil, "which", lambda cmd: cmd)
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "hatch", "--egg", str(egg_path)])
    with pytest.raises(SystemExit):
        egg_cli.main()


def test_verify_missing_egg(monkeypatch):
    missing = Path("nope.egg")
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "verify", "--egg", str(missing)])
    with pytest.raises(SystemExit) as exc:
        egg_cli.main()
    assert str(missing) in str(exc.value)


def test_info_missing_egg(monkeypatch):
    missing = Path("nope.egg")
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "info", "--egg", str(missing)])
    with pytest.raises(SystemExit) as exc:
        egg_cli.main()
    assert str(missing) in str(exc.value)


def test_info_missing_manifest(monkeypatch, tmp_path):
    egg_path = tmp_path / "demo.egg"
    with zipfile.ZipFile(egg_path, "w") as zf:
        info = zipfile.ZipInfo("foo.txt")
        info.date_time = (1980, 1, 1, 0, 0, 0)
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, b"foo")

    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "info", "--egg", str(egg_path)])
    with pytest.raises(SystemExit):
        egg_cli.main()


def test_info_bad_signature(monkeypatch, tmp_path):
    """'egg info' should fail when the archive is tampered."""
    egg_path = tmp_path / "demo.egg"

    # build an egg
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(egg_path),
        ],
    )
    egg_cli.main()

    # tamper with signature
    with zipfile.ZipFile(egg_path, "a") as zf:
        zf.writestr("hashes.sig", "0" * 128)

    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "info", "--egg", str(egg_path)])
    with pytest.raises(SystemExit):
        egg_cli.main()


def test_verbose_debug(monkeypatch, tmp_path):
    output = tmp_path / "demo.egg"
    root_logger = logging.getLogger()
    prev = root_logger.level
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "egg_cli.py",
            "build",
            "--manifest",
            os.path.join("examples", "manifest.yaml"),
            "--output",
            str(output),
            "-vv",
        ],
    )
    try:
        egg_cli.main()
        assert root_logger.level == logging.DEBUG
    finally:
        root_logger.setLevel(prev)
    assert output.is_file()


def test_check_platform_error(monkeypatch):
    monkeypatch.setattr(egg_cli.platform, "system", lambda: "Solaris")
    with pytest.raises(SystemExit):
        egg_cli.check_platform()


def test_info_manifest_missing_after_verify(monkeypatch, tmp_path):
    foo = tmp_path / "foo.txt"
    foo.write_text("x")
    hashes = {"foo.txt": hashlib.sha256(b"x").hexdigest()}
    hashes_path = tmp_path / "hashes.yaml"
    hashes_path.write_text(yaml.safe_dump(hashes, sort_keys=True))
    sig_path = tmp_path / "hashes.sig"
    sig_path.write_text(sign_hashes(hashes_path))
    egg_path = tmp_path / "demo.egg"
    with zipfile.ZipFile(egg_path, "w") as zf:
        for path in [foo, hashes_path, sig_path]:
            zi = zipfile.ZipInfo(path.name)
            zi.date_time = (1980, 1, 1, 0, 0, 0)
            zi.compress_type = zipfile.ZIP_DEFLATED
            with open(path, "rb") as f:
                zf.writestr(zi, f.read())
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "info", "--egg", str(egg_path)])
    with pytest.raises(SystemExit, match="manifest.yaml not found"):
        egg_cli.main()


def test_info_shows_optional_fields(monkeypatch, tmp_path, capsys):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
name: Example
description: desc
author: Bob
created: '2024-01-01'
license: MIT
cells:
  - language: python
    source: hello.py
"""
    )
    (tmp_path / "hello.py").write_text("print('hi')\n")
    egg_path = tmp_path / "demo.egg"
    monkeypatch.setattr(
        sys,
        "argv",
        ["egg_cli.py", "build", "--manifest", str(manifest), "--output", str(egg_path)],
    )
    egg_cli.main()
    capsys.readouterr()

    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "info", "--egg", str(egg_path)])
    egg_cli.main()
    out = capsys.readouterr().out
    assert "Author: Bob" in out
    assert "License: MIT" in out
    assert "Created: 2024-01-01" in out


def test_languages_command(monkeypatch, capsys):
    """The languages command should list plug-in languages."""
    monkeypatch.setattr(sys, "argv", ["egg_cli.py", "languages"])
    egg_cli.main()
    out = set(capsys.readouterr().out.splitlines())
    assert {"python", "r", "bash", "ruby"} <= out


@pytest.mark.parametrize("system,expected", [("Linux", "runc"), ("Darwin", "docker")])
def test_sandbox_launch_helpers(monkeypatch, tmp_path, system, expected):
    from egg import sandboxer

    (tmp_path / "microvm.json").write_text("{}")
    (tmp_path / "container.json").write_text('{"language": "python"}')
    calls = []

    def fake_run(cmd, check=True):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(platform, "system", lambda: system)

    sandboxer.launch_microvm(tmp_path)
    sandboxer.launch_container(tmp_path)

    assert any("firecracker" in c[0] for c in calls)
    assert any(expected in c[0] for c in calls)


def test_clean_removes_artifacts(monkeypatch, tmp_path, caplog):
    target_dir = tmp_path / "work"
    target_dir.mkdir()
    (target_dir / "precompute_hashes.yaml").write_text("{}")
    (target_dir / "result.out").write_text("hi")
    sb = target_dir / "sandbox"
    sb.mkdir()

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys, "argv", ["egg_cli.py", "--verbose", "clean", str(target_dir)]
    )
    egg_cli.main()

    assert not (target_dir / "precompute_hashes.yaml").exists()
    assert not (target_dir / "result.out").exists()
    assert not sb.exists()
    assert "[clean] Removed" in caplog.text


def test_clean_dry_run(monkeypatch, tmp_path, caplog):
    target_dir = tmp_path / "work"
    target_dir.mkdir()
    (target_dir / "precompute_hashes.yaml").write_text("{}")
    (target_dir / "result.out").write_text("hi")
    sb = target_dir / "sandbox"
    sb.mkdir()

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        ["egg_cli.py", "--verbose", "clean", "--dry-run", str(target_dir)],
    )
    egg_cli.main()

    assert (target_dir / "precompute_hashes.yaml").exists()
    assert (target_dir / "result.out").exists()
    assert sb.exists()
    assert "Would remove" in caplog.text
