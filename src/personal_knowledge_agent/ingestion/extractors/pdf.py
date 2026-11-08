"""Native, page-level PDF text extraction using PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from personal_knowledge_agent.discovery.models import FileRecord
from personal_knowledge_agent.ingestion.models import (
    ExtractedDocument,
    ExtractedSection,
)

# This deliberately small threshold is only a signal for later OCR processing.
# Short pages can still be intentionally sparse (for example, a title page).
MIN_NATIVE_TEXT_CHARACTERS = 20


class PdfTextExtractor:
    """Extract native text from each PDF page without performing OCR."""

    def extract(self, source_path: Path, metadata: FileRecord) -> ExtractedDocument:
        """Extract page sections from *source_path* and retain its inventory path."""
        try:
            with pymupdf.open(source_path) as document:
                if document.needs_pass:
                    return _failed_result(
                        metadata, "PDF is encrypted or password-protected"
                    )

                return self._extract_document(document, metadata)
        except Exception as error:  # noqa: BLE001 - extraction must not abort ingestion
            return _failed_result(metadata, f"Could not read PDF: {error}")

    def _extract_document(
        self, document: pymupdf.Document, metadata: FileRecord
    ) -> ExtractedDocument:
        sections: list[ExtractedSection] = []
        errors: list[str] = []
        warnings: list[str] = []
        page_failures = 0

        for page_index in range(document.page_count):
            page_number = page_index + 1
            try:
                page = document.load_page(page_index)
                extracted_text = page.get_text("text")
                if not isinstance(extracted_text, str):
                    raise TypeError(
                        "PyMuPDF returned non-text content for a text request"
                    )
                text = extracted_text
            except Exception as error:  # noqa: BLE001 - retain a failed page section
                text = ""
                page_failures += 1
                errors.append(f"Could not extract page {page_number}: {error}")

            needs_ocr = len(text.strip()) < MIN_NATIVE_TEXT_CHARACTERS
            if needs_ocr:
                warnings.append(
                    f"Page {page_number} has little or no native text and may need OCR"
                )

            sections.append(
                ExtractedSection(
                    section_id=f"page-{page_number}",
                    section_type="page",
                    text=text,
                    page_number=page_number,
                    needs_ocr=needs_ocr,
                )
            )

        if sections and page_failures == len(sections):
            status = "failed"
        elif not any(not section.needs_ocr for section in sections):
            status = "needs_ocr"
        elif any(section.needs_ocr for section in sections) or page_failures:
            status = "partial"
        else:
            status = "success"

        return ExtractedDocument(
            relative_path=metadata.relative_path,
            file_type="pdf",
            status=status,
            sections=sections,
            errors=errors,
            warnings=warnings,
        )


def _failed_result(metadata: FileRecord, message: str) -> ExtractedDocument:
    return ExtractedDocument(
        relative_path=metadata.relative_path,
        file_type="pdf",
        status="failed",
        sections=[],
        errors=[message],
    )
