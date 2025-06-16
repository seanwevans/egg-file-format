import argparse
from pathlib import Path

from egg import compose


def build(args: argparse.Namespace) -> None:
    """Build an egg file from sources.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments with ``manifest`` and ``output`` attributes.
    """
    compose(Path(args.manifest), Path(args.output))
    print(f"[build] Egg written to {args.output}")


def hatch(_args: argparse.Namespace) -> None:
    """Hatch (run) an egg file.

    Args:
        _args: Parsed command line arguments for the ``hatch`` subcommand. This
            placeholder function ignores additional options.

    Returns:
        None. Prints a placeholder message indicating an egg would hatch.
    """
    print("[hatch] Hatching egg... (placeholder)")


def main() -> None:
    """Entry point for the ``egg`` command line interface.

    Parses arguments and dispatches to the appropriate subcommand. The function
    exits after running the selected command or printing help information.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Egg builder and hatcher CLI")
    subparsers = parser.add_subparsers(dest="command")

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


if __name__ == "__main__":
    main()
