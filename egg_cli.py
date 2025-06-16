import argparse

from pathlib import Path
__version__ = "0.1.0"


def build(args: argparse.Namespace) -> None:
    """Build an egg file from sources.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments with ``manifest`` and ``output`` attributes.
    """

    print(f"[build] Building egg from {args.manifest} -> {args.output} (placeholder)")

def hatch(args: argparse.Namespace) -> None:
    """Hatch (run) an egg file.

    Args:
        args: Parsed command line arguments for the ``hatch`` subcommand.
            ``args.egg`` identifies the egg file to hatch.

    Returns:
        None. Prints a placeholder message indicating an egg would hatch.
    """
    print(f"[hatch] Hatching {args.egg} (placeholder)")


def main() -> None:
    """Entry point for the ``egg`` command line interface.

    Parses arguments and dispatches to the appropriate subcommand. The function
    exits after running the selected command or printing help information.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Egg builder and hatcher CLI")

    subparsers = parser.add_subparsers(dest="command", required=True)

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit",
    )

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
        "-e",
        "--egg",
        default="out.egg",
        help="Egg file to hatch",
    )
    parser_hatch.add_argument(
        "--no-sandbox",
        action="store_true",
        help="Run without sandbox (unsafe)",
    )
    parser_hatch.set_defaults(func=hatch)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        parser.exit()



if __name__ == "__main__":
    main()
