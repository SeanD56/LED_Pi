"""Command-line interface for the LED Pi appliance."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from ledpi import __version__
from ledpi.config import ConfigError, load_config
from ledpi.media import ScanReport, process_inbox


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

    config_parent = argparse.ArgumentParser(add_help=False)
    config_parent.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a TOML config file.",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="command")

    scan_parser = subparsers.add_parser(
        "scan",
        parents=[config_parent],
        help="scan command",
    )
    scan_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be processed without writing output files.",
    )
    scan_parser.set_defaults(handler=_scan)

    for command in ("run", "test-pattern", "doctor"):
        subparser = subparsers.add_parser(
            command,
            parents=[config_parent],
            help=f"{command} command",
        )
        subparser.set_defaults(handler=_not_implemented)

    return parser


def _scan(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 1

    report = process_inbox(config, dry_run=args.dry_run or config.runtime.dry_run)
    _print_scan_report(report)
    return 1 if report.has_errors else 0


def _not_implemented(args: argparse.Namespace) -> int:
    command = args.command or "command"
    print(f"ledpi {command}: not implemented yet")
    return 2


def _print_scan_report(report: ScanReport) -> None:
    if not report.items:
        print("No media found.")
        return

    for item in report.items:
        print(f"{item.status.value}: {item.path} - {item.message}")

    summary = ", ".join(
        f"{status.value}={count}"
        for status, count in sorted(
            report.counts.items(),
            key=lambda count_item: count_item[0].value,
        )
    )
    print(f"Summary: {summary}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    return args.handler(args)
