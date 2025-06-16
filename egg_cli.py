import argparse
from pathlib import Path

from egg import compose

__version__ = "0.1.0"


def build(args: argparse.Namespace) -> None:
    """Build an egg file from sources."""
    compose(Path(args.manifest), Path(args.output))
    print("[build] Building egg from manifest.yaml -> out.egg (placeholder)")


def hatch(_args: argparse.Namespace) -> None:
    """Hatch (run) an egg file."""
    print("[hatch] Hatching egg... (placeholder)")


def main() -> None:
    """Entry point for the ``egg`` command line interface."""
    parser = argparse.ArgumentParser(description="Egg builder and hatcher CLI")
    subparsers = parser.add_subparsers(dest="command")

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit",
    )

    parser_build = subparsers.add_parser("build", help="Build an egg file")
    parser_build.add_argument(
        "--manifest",
        required=True,
        help="Path to manifest.yaml describing notebook contents",
    )
    parser_build.add_argument(
        "--output",
        required=True,
        help="Destination .egg archive path",
    )
    parser_build.set_defaults(func=build)

    parser_hatch = subparsers.add_parser("hatch", help="Hatch an egg file")
    parser_hatch.set_defaults(func=hatch)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        parser.exit(2)


if __name__ == "__main__":
    main()
