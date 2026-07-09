"""Command-line interface for geoengine-utils."""

from __future__ import annotations

import argparse
import sys
from typing import Any, Sequence

from . import __version__
from .crs import estimate_crs
from .raster import validate_raster


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(prog="geoengine-utils")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")
    validate_parser = subparsers.add_parser("validate", help="Validate a raster dataset")
    validate_parser.add_argument("path", help="Path to the raster file to validate")

    estimate_parser = subparsers.add_parser(
        "estimate-crs",
        help="Estimate a suitable projected CRS for a dataset",
    )
    estimate_parser.add_argument("path", help="Path to a vector or raster dataset")

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
        parsed_args = parser.parse_args(args if args is not None else sys.argv[1:])
    except SystemExit as exc:
        return int(exc.code)

    if parsed_args.command == "validate":
        report = validate_raster(parsed_args.path)
        output = report.format_report()
        if stdout is None:
            print(output)
        else:
            print(output, file=stdout)
        return 0 if report.passed else 1

    if parsed_args.command == "estimate-crs":
        recommendation = estimate_crs(parsed_args.path)
        output = f"recommended_crs={recommendation.recommended.auth_name}:{recommendation.recommended.code}"
        if stdout is None:
            print(output)
        else:
            print(output, file=stdout)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
