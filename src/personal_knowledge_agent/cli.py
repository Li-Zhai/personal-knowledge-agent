"""Command-line interface for the personal knowledge agent."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from personal_knowledge_agent.discovery.scanner import scan_directory


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface and return a process exit code."""
    parser = _build_parser()
    arguments = parser.parse_args(argv)

    if arguments.command == "scan":
        if _is_within(arguments.output, arguments.root):
            parser.error("--output must be outside the directory being scanned")
        result = scan_directory(arguments.root)
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            json.dumps(result.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
        return 0

    parser.error("a command is required")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal knowledge agent tools")
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="Create a read-only file inventory")
    scan.add_argument("root", type=Path, help="Directory to scan")
    scan.add_argument("--output", required=True, type=Path, help="Inventory JSON path")
    return parser


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True
