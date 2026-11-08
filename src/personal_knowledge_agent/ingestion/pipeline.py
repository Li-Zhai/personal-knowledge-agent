"""Minimal orchestration for native document ingestion."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from personal_knowledge_agent.discovery.models import FileRecord
from personal_knowledge_agent.ingestion.extractors.base import DocumentExtractor
from personal_knowledge_agent.ingestion.extractors.pdf import PdfTextExtractor
from personal_knowledge_agent.ingestion.models import ExtractedDocument


def ingest_discovered_files(
    inventory_root: str | Path,
    files: Iterable[FileRecord],
    *,
    pdf_extractor: DocumentExtractor | None = None,
) -> list[ExtractedDocument]:
    """Extract supported discovered files in input order.

    ``inventory_root`` is the same directory supplied to the discovery stage;
    each ``FileRecord.relative_path`` is resolved below it.
    """
    root = Path(inventory_root)
    extractor = pdf_extractor or PdfTextExtractor()
    results: list[ExtractedDocument] = []

    for file in files:
        if file.extension.lower() != ".pdf":
            results.append(
                ExtractedDocument(
                    relative_path=file.relative_path,
                    file_type=file.extension.lstrip(".").lower(),
                    status="unsupported",
                    sections=[],
                    warnings=[f"Unsupported file type: {file.extension or '(none)'}"],
                )
            )
            continue

        try:
            results.append(extractor.extract(root / file.relative_path, file))
        except Exception as error:  # noqa: BLE001 - isolate one document's failure
            results.append(
                ExtractedDocument(
                    relative_path=file.relative_path,
                    file_type="pdf",
                    status="failed",
                    sections=[],
                    errors=[f"Extractor failed unexpectedly: {error}"],
                )
            )

    return results
