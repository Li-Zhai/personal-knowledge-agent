"""Print native text extracted from one PDF for local inspection."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from personal_knowledge_agent.discovery.models import FileRecord
from personal_knowledge_agent.ingestion.extractors.pdf import PdfTextExtractor


def main() -> int:
    """Extract one PDF and print a readable page-level summary."""
    parser = argparse.ArgumentParser(description="Inspect native PDF text extraction")
    parser.add_argument("pdf", type=Path, help="PDF file to extract")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1_000,
        help="Maximum characters to print per page (default: 1000)",
    )
    arguments = parser.parse_args()

    source_path = arguments.pdf.expanduser().resolve()
    metadata = source_path.stat()
    file_record = FileRecord(
        relative_path=source_path.name,
        extension=source_path.suffix,
        size_bytes=metadata.st_size,
        modified_at=datetime.fromtimestamp(metadata.st_mtime, tz=UTC)
        .isoformat()
        .replace("+00:00", "Z"),
    )
    result = PdfTextExtractor().extract(source_path, file_record)

    print(f"{source_path.name}: {result.status}")
    for warning in result.warnings:
        print(f"warning: {warning}")
    for error in result.errors:
        print(f"error: {error}")
    for section in result.sections:
        preview = section.text[: arguments.max_chars]
        truncated = "…" if len(section.text) > arguments.max_chars else ""
        print(f"\n--- Page {section.page_number} (needs_ocr={section.needs_ocr}) ---")
        print(f"{preview}{truncated}")

    return 1 if result.status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
