"""Command line interface for building and running egg archives."""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
import platform
from egg.constants import SUPPORTED_PLATFORMS
from pathlib import Path, PurePosixPath

from egg.composer import compose
from egg.hashing import verify_archive, _signing_key
from egg.manifest import load_manifest
from egg.sandboxer import prepare_images
from egg.runtime_fetcher import fetch_runtime_blocks
from egg.precompute import precompute_cells
from egg.utils import DEFAULT_LANG_COMMANDS, get_lang_command, load_plugins


__version__ = "0.1.0"

logger = logging.getLogger(__name__)


def check_platform() -> None:
    """Exit if running on an unsupported platform."""

    current = platform.system()
    if current not in SUPPORTED_PLATFORMS:
        raise SystemExit(f"Unsupported platform: {current}")


def build(args: argparse.Namespace) -> None:
    """Build an egg file from sources."""
    manifest = Path(args.manifest)
    output = Path(args.output)

    if output.exists() and not args.force:
        raise SystemExit(f"{output} exists. Use --force to overwrite.")

    # Fetch any runtime dependencies referenced in the manifest
    deps = fetch_runtime_blocks(manifest)

    if args.precompute:
        precompute_cells(manifest)

    priv: bytes | None = None
    if args.private_key:
        priv = Path(args.private_key).read_bytes()

    pub: bytes | None = None
    if args.public_key:
        pub = Path(args.public_key).read_bytes()
    elif priv is not None:
        pub = _signing_key(priv).verify_key.encode()

    compose(manifest, output, dependencies=deps, private_key=priv)

    if not verify_archive(output, public_key=pub):
        output.unlink(missing_ok=True)
        raise SystemExit("Hash verification failed")

    logger.info("[build] Building egg from %s -> %s", manifest, output)


def hatch(args: argparse.Namespace) -> None:
    """Hatch (run) an egg file by executing each cell."""
    egg_path = Path(args.egg)
    if not egg_path.is_file():
        raise SystemExit(f"Egg file not found: {egg_path}")
    pub: bytes | None = None
    if args.public_key:
        pub = Path(args.public_key).read_bytes()

    if not verify_archive(egg_path, public_key=pub):
        raise SystemExit("Hash verification failed")

    with zipfile.ZipFile(egg_path) as zf, tempfile.TemporaryDirectory() as tmpdir:
        for name in zf.namelist():
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts:
                raise SystemExit(f"Unsafe path in archive: {name}")
        zf.extractall(tmpdir)
        manifest_path = Path(tmpdir) / "manifest.yaml"
        manifest = load_manifest(manifest_path)

        if args.no_sandbox:
            logger.warning("[hatch] Running without sandbox (unsafe)")
        else:
            prepare_images(manifest, Path(tmpdir) / "sandbox")

        for cell in manifest.cells:
            src = Path(tmpdir) / cell.source
            lang = cell.language.lower()
            base_cmd = get_lang_command(lang)
            if base_cmd is None:
                raise SystemExit(f"Unsupported language: {cell.language}")
            cmd = base_cmd[0]
            if shutil.which(cmd) is None:
                raise SystemExit(
                    f"Required runtime '{cmd}' for {cell.language} cells not found"
                )
            subprocess.run(base_cmd + [str(src)], check=True)

    logger.info("[hatch] Completed running %s", egg_path)


def verify(args: argparse.Namespace) -> None:
    """Verify that an egg archive matches its recorded hashes."""
    egg_path = Path(args.egg)
    if not egg_path.is_file():
        raise SystemExit(f"Egg file not found: {egg_path}")

    pub: bytes | None = None
    if args.public_key:
        pub = Path(args.public_key).read_bytes()

    if verify_archive(egg_path, public_key=pub):
        logger.info("[verify] %s verified successfully", egg_path)
    else:
        raise SystemExit("Hash verification failed")


def info(args: argparse.Namespace) -> None:
    """Print a summary of an egg archive's manifest."""
    egg_path = Path(args.egg)
    if not egg_path.is_file():
        raise SystemExit(f"Egg file not found: {egg_path}")

    pub: bytes | None = None
    if args.public_key:
        pub = Path(args.public_key).read_bytes()

    if not verify_archive(egg_path, public_key=pub):
        raise SystemExit("Hash verification failed")

    with zipfile.ZipFile(egg_path) as zf, tempfile.TemporaryDirectory() as tmpdir:
        try:
            zf.extract("manifest.yaml", tmpdir)
        except KeyError:
            raise SystemExit("manifest.yaml not found in archive")
        manifest = load_manifest(Path(tmpdir) / "manifest.yaml")

    print(f"Name: {manifest.name}")
    print(f"Description: {manifest.description}")
    if manifest.author is not None:
        print(f"Author: {manifest.author}")
    if manifest.license is not None:
        print(f"License: {manifest.license}")
    if manifest.created is not None:
        print(f"Created: {manifest.created}")
    print("Cells:")
    for cell in manifest.cells:
        print(f"  - {cell.language}: {cell.source}")
    if manifest.dependencies:
        print("Dependencies:")
        for dep in manifest.dependencies:
            print(f"  - {dep}")
    if manifest.permissions:
        print("Permissions:")
        for perm, val in manifest.permissions.items():
            print(f"  {perm}: {val}")


def clean(args: argparse.Namespace) -> None:
    """Remove build artifacts under a path."""
    root = Path(args.path)
    if not root.exists():
        raise SystemExit(f"Path not found: {root}")

    targets: set[Path] = set()
    targets.update(root.rglob("precompute_hashes.yaml"))
    targets.update(root.rglob("*.out"))
    targets.update(p for p in root.rglob("sandbox") if p.is_dir())

    for path in sorted(targets):
        if args.dry_run:
            logger.info("[clean] Would remove %s", path)
        else:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            logger.info("[clean] Removed %s", path)


def languages(args: argparse.Namespace) -> None:
    """Print supported language identifiers."""
    load_plugins()
    for lang in sorted(DEFAULT_LANG_COMMANDS):
        print(lang)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``egg`` command line interface."""
    if argv is None:  # pragma: no cover - convenience for __main__
        argv = sys.argv[1:]

    check_platform()
    load_plugins()

    global_parser = argparse.ArgumentParser(add_help=False)
    global_parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit",
    )
    global_parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity. Use -vv for debug output",
    )

    parser = argparse.ArgumentParser(
        description="Egg builder and hatcher CLI",
        parents=[global_parser],
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_build = subparsers.add_parser(
        "build", help="Build an egg file", parents=[global_parser]
    )

    parser_build.add_argument(
        "-m",
        "--manifest",
        default="manifest.yaml",
        help="Path to manifest YAML file",
    )
    parser_build.add_argument(
        "-o",
        "--output",
        default="out.egg",
        help="Path for output egg file",
    )
    parser_build.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite output if it exists",
    )
    parser_build.add_argument(
        "--precompute",
        action="store_true",
        help="Execute cells and store outputs before composing",
    )
    parser_build.add_argument(
        "--private-key",
        help="Path to Ed25519 private key file",
    )
    parser_build.add_argument(
        "--public-key",
        help="Public key file used for verification",
    )
    parser_build.set_defaults(func=build)

    parser_hatch = subparsers.add_parser(
        "hatch", help="Hatch an egg file", parents=[global_parser]
    )
    parser_hatch.add_argument(
        "-e", "--egg", default="out.egg", help="Egg file to hatch"
    )
    parser_hatch.add_argument(
        "--no-sandbox", action="store_true", help="Run without sandbox (unsafe)"
    )
    parser_hatch.add_argument(
        "--public-key", help="Public key file for signature verification"
    )
    parser_hatch.set_defaults(func=hatch)

    parser_verify = subparsers.add_parser(
        "verify", help="Verify an egg archive", parents=[global_parser]
    )
    parser_verify.add_argument(
        "-e",
        "--egg",
        default="out.egg",
        help="Egg file to verify",
    )
    parser_verify.add_argument(
        "--public-key",
        help="Public key file for signature verification",
    )
    parser_verify.set_defaults(func=verify)

    parser_info = subparsers.add_parser(
        "info", help="Show manifest summary", parents=[global_parser]
    )
    parser_info.add_argument(
        "-e",
        "--egg",
        default="out.egg",
        help="Egg file to inspect",
    )
    parser_info.add_argument(
        "--public-key",
        help="Public key file for signature verification",
    )
    parser_info.set_defaults(func=info)

    parser_langs = subparsers.add_parser(
        "languages", help="List supported languages", parents=[global_parser]
    )
    parser_langs.set_defaults(func=languages)

    parser_clean = subparsers.add_parser(
        "clean", help="Remove build artifacts", parents=[global_parser]
    )
    parser_clean.add_argument(
        "path", nargs="?", default=".", help="Path to scan for artifacts"
    )
    parser_clean.add_argument(
        "--dry-run", action="store_true", help="List files without removing"
    )
    parser_clean.set_defaults(func=clean)

    args, _ = parser.parse_known_args(argv)
    extras, _ = global_parser.parse_known_args(argv)
    for key, value in vars(extras).items():
        setattr(args, key, value)
    if args.verbose >= 2:
        level = logging.DEBUG
    elif args.verbose == 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(level=level, format="%(message)s")
    logging.getLogger().setLevel(level)

    args.func(args)


if __name__ == "__main__":  # pragma: no cover - script entry point
    main()
