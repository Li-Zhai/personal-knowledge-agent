"""Command-line interface for the personal knowledge agent."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from personal_knowledge_agent.discovery.models import ScanError
from personal_knowledge_agent.discovery.scanner import scan_directory
from personal_knowledge_agent.ingestion.io import (
    InventoryError,
    load_inventory_with_errors,
    validate_paths_within_root,
    write_extraction_output,
    write_inventory_output,
)
from personal_knowledge_agent.ingestion.models import ExtractedDocument
from personal_knowledge_agent.ingestion.pipeline import ingest_discovered_files


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface and return a process exit code."""
    parser = _build_parser()
    arguments = parser.parse_args(argv)

    if arguments.command == "scan":
        if _is_within(arguments.output, arguments.root):
            parser.error("--output must be outside the directory being scanned")
        result = scan_directory(arguments.root)
        try:
            write_inventory_output(arguments.output, result)
        except OSError as error:
            print(f"scan: {error}", file=sys.stderr)
            return 1
        return 0

    if arguments.command == "ingest":
        try:
            inventory = load_inventory_with_errors(arguments.inventory)
            root = validate_paths_within_root(arguments.root, inventory.files)
            _validate_ingest_output(arguments.output, arguments.inventory, root)
            documents = ingest_discovered_files(root, inventory.files)
            write_extraction_output(
                arguments.output,
                documents,
                discovery_errors=inventory.errors,
            )
        except (InventoryError, OSError) as error:
            print(f"ingest: {error}", file=sys.stderr)
            return 1

        _print_ingestion_summary(documents, arguments.output, inventory.errors)
        return 0

    parser.error("a command is required")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal knowledge agent tools")
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="Create a read-only file inventory")
    scan.add_argument("root", type=Path, help="Directory to scan")
    scan.add_argument("--output", required=True, type=Path, help="Inventory JSON path")
    ingest = commands.add_parser("ingest", help="Extract documents from an inventory")
    ingest.add_argument(
        "--inventory", required=True, type=Path, help="Stage 1 inventory JSON path"
    )
    ingest.add_argument(
        "--root", required=True, type=Path, help="Archive root used for discovery"
    )
    ingest.add_argument(
        "--output", required=True, type=Path, help="Extraction JSON path"
    )
    return parser


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(directory.resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _validate_ingest_output(output: Path, inventory: Path, root: Path) -> None:
    """Reject destinations that could overwrite an archive source or inventory."""
    try:
        resolved_output = output.resolve(strict=False)
        resolved_inventory = inventory.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise InventoryError(
            f"Could not resolve output destination: {error}"
        ) from error

    if _is_within(resolved_output, root):
        raise InventoryError("Output path must be outside the archive root")
    if resolved_output == resolved_inventory:
        raise InventoryError("Output path must not be the input inventory file")


def _print_ingestion_summary(
    documents: list[ExtractedDocument], output: Path, discovery_errors: list[ScanError]
) -> None:
    statuses = Counter(document.status for document in documents)
    ocr_documents = sum(
        any(section.needs_ocr for section in document.sections)
        for document in documents
    )
    ocr_pages = sum(
        section.needs_ocr for document in documents for section in document.sections
    )
    status_summary = (
        ", ".join(f"{status}={count}" for status, count in sorted(statuses.items()))
        or "none"
    )
    print(f"Processed {len(documents)} documents ({status_summary}).")
    if discovery_errors:
        print(f"Discovery errors: {len(discovery_errors)} (see output for details).")
    print(f"OCR candidates: {ocr_documents} documents, {ocr_pages} pages.")
    print(f"Output: {output}")
