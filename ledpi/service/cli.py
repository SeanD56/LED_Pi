"""Command-line interface for the LED Pi appliance."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from ledpi import __version__
from ledpi.config import ConfigError, load_config
from ledpi.media import ScanReport, process_inbox
from ledpi.playback import PlaybackSummary, play_playlist
from ledpi.render import FakeRenderer


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

    run_parser = subparsers.add_parser(
        "run",
        parents=[config_parent],
        help="run command",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use an in-memory renderer instead of hardware.",
    )
    run_parser.add_argument(
        "--once",
        action="store_true",
        help="Play one loop and exit.",
    )
    run_parser.set_defaults(handler=_run)

    for command in ("test-pattern", "doctor"):
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


def _run(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 1

    dry_run = args.dry_run or config.runtime.dry_run
    if not dry_run:
        print(
            "hardware renderer is not implemented yet; use --dry-run",
            file=sys.stderr,
        )
        return 2

    renderer = FakeRenderer()
    summary = play_playlist(
        config,
        renderer,
        once=args.once,
        sleep=lambda _seconds: None,
    )
    _print_playback_summary(summary)
    return 0


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


def _print_playback_summary(summary: PlaybackSummary) -> None:
    fallback = str(summary.used_fallback).lower()
    print(
        "Playback complete: "
        f"items={summary.items_played} "
        f"frames={summary.frames_shown} "
        f"fallback={fallback}",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    return args.handler(args)
