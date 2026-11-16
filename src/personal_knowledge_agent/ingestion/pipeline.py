"""Minimal orchestration for native document ingestion."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from personal_knowledge_agent.discovery.models import FileRecord
from personal_knowledge_agent.ingestion.extractors.base import DocumentExtractor
from personal_knowledge_agent.ingestion.extractors.notebook import NotebookExtractor
from personal_knowledge_agent.ingestion.extractors.pdf import PdfTextExtractor
from personal_knowledge_agent.ingestion.extractors.text import TextExtractor
from personal_knowledge_agent.ingestion.models import ExtractedDocument

TEXT_EXTENSIONS = {".txt", ".md", ".py"}


def ingest_discovered_files(
    inventory_root: str | Path,
    files: Iterable[FileRecord],
    *,
    pdf_extractor: DocumentExtractor | None = None,
    text_extractor: DocumentExtractor | None = None,
    notebook_extractor: DocumentExtractor | None = None,
) -> list[ExtractedDocument]:
    """Extract supported discovered files in input order.

    ``inventory_root`` is the same directory supplied to the discovery stage;
    each ``FileRecord.relative_path`` is resolved below it.
    """
    root = Path(inventory_root)
    pdf = pdf_extractor or PdfTextExtractor()
    text = text_extractor or TextExtractor()
    notebook = notebook_extractor or NotebookExtractor()
    results: list[ExtractedDocument] = []

    for file in files:
        extension = file.extension.lower()
        if extension == ".pdf":
            extractor = pdf
        elif extension in TEXT_EXTENSIONS:
            extractor = text
        elif extension == ".ipynb":
            extractor = notebook
        else:
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
                    file_type=extension.lstrip("."),
                    status="failed",
                    sections=[],
                    errors=[f"Extractor failed unexpectedly: {error}"],
                )
            )

    return results
