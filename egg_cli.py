import argparse


def build(_args: argparse.Namespace) -> None:
    """Placeholder for building an egg file."""
    print("[build] Building egg... (placeholder)")


def hatch(_args: argparse.Namespace) -> None:
    """Placeholder for hatching an egg file."""
    print("[hatch] Hatching egg... (placeholder)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Egg builder and hatcher CLI")
    subparsers = parser.add_subparsers(dest="command")

    parser_build = subparsers.add_parser("build", help="Build an egg file")
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
