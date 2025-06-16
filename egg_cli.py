import argparse
import os

import yaml


def parse_manifest(path: str) -> list[str]:
    """Parse a manifest file and return resolved source paths."""
    with open(path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    base_dir = os.path.dirname(os.path.abspath(path))
    resolved = []
    for cell in manifest.get("cells", []):
        source = cell.get("source")
        if source:
            resolved.append(os.path.abspath(os.path.join(base_dir, source)))
    return resolved


def build(args: argparse.Namespace) -> None:
    """Build an egg file from sources.

    Args:
        args: Parsed command line arguments for the ``build`` subcommand.

    Returns:
        None. Prints a placeholder message to indicate the command ran.
    """
    resolved = []
    if args.manifest:
        resolved = parse_manifest(args.manifest)

    print("[build] Building egg... (placeholder)")
    for path in resolved:
        print(path)


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
        type=str,
        help="Path to the manifest YAML",
    )
    parser_build.add_argument(
        "--output",
        type=str,
        help="Output egg file path",
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
