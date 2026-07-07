"""Command-line interface for geoengine-utils."""

from __future__ import annotations

import argparse
import sys
from typing import Any, Sequence

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(prog="geoengine-utils")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(args: Sequence[str] | None = None, *, stdout: Any | None = None) -> int:
    """Run the CLI entry point.

    Parameters
    ----------
    args : Sequence[str] | None
        Optional CLI arguments. When omitted, ``sys.argv[1:]`` is used.
    stdout : Any | None
        Optional output stream used for CLI messages.

    Returns
    -------
    int
        Exit code for the CLI.
    """

    parser = build_parser()
    if stdout is not None:
        parser._print_message = lambda message, file=None: print(message, file=stdout)

    try:
        parser.parse_args(args if args is not None else sys.argv[1:])
    except SystemExit as exc:
        return int(exc.code)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
