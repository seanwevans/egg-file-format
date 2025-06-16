import argparse

__version__ = "0.1.0"


def build(_args: argparse.Namespace) -> None:
    """Build an egg file from sources.

    Args:
        _args: Parsed command line arguments for the ``build`` subcommand. The
            current placeholder does not expect any specific options.

    Returns:
        None. Prints a placeholder message to indicate the command ran.
    """
    print("[build] Building egg... (placeholder)")


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

    subparsers = parser.add_subparsers(dest="command", required=True)

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit",
    )

    parser_build = subparsers.add_parser("build", help="Build an egg file")
    parser_build.set_defaults(func=build)

    parser_hatch = subparsers.add_parser("hatch", help="Hatch an egg file")
    parser_hatch.set_defaults(func=hatch)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        parser.exit()



if __name__ == "__main__":
    main()
