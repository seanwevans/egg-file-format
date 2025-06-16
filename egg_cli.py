import argparse
import logging
import sys
from pathlib import Path

from egg.composer import compose

__version__ = "0.1.0"

logger = logging.getLogger(__name__)


def build(args: argparse.Namespace) -> None:
    """Build an egg file from sources."""
    manifest = Path(args.manifest)
    output = Path(args.output)

    if output.exists() and not args.force:
        raise SystemExit(f"{output} exists. Use --force to overwrite.")

    compose(manifest, output)

    logger.info("[build] Building egg from %s -> %s (placeholder)", manifest, output)


def hatch(_args: argparse.Namespace) -> None:
    """Hatch (run) an egg file."""
    logger.info("[hatch] Hatching egg... (placeholder)")


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``egg`` command line interface."""
    if argv is None:  # pragma: no cover - convenience for __main__
        argv = sys.argv[1:]

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
    subparsers = parser.add_subparsers(dest="command")

    parser_build = subparsers.add_parser("build", help="Build an egg file")

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
    parser_build.set_defaults(func=build)

    parser_hatch = subparsers.add_parser("hatch", help="Hatch an egg file")
    parser_hatch.add_argument(
        "-e", "--egg", default="out.egg", help="Egg file to hatch"
    )
    parser_hatch.add_argument(
        "--no-sandbox", action="store_true", help="Run without sandbox (unsafe)"
    )
    parser_hatch.set_defaults(func=hatch)

    args, remaining = parser.parse_known_args(argv)
    if remaining:
        extras = global_parser.parse_args(remaining)
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

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help(sys.stderr)
        parser.exit(2)


if __name__ == "__main__":
    main()
