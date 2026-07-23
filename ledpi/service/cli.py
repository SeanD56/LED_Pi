"""Command-line interface for the LED Pi appliance."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from ledpi import __version__


COMMANDS = ("scan", "run", "test-pattern", "doctor")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ledpi",
        description="Raspberry Pi 5 LED matrix appliance.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="command")
    for command in COMMANDS:
        subparser = subparsers.add_parser(command, help=f"{command} command")
        subparser.set_defaults(handler=_not_implemented)

    return parser


def _not_implemented(args: argparse.Namespace) -> int:
    command = args.command or "command"
    print(f"ledpi {command}: not implemented yet")
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    return args.handler(args)
