"""UTF-8 text extraction for plain-text and source-code files."""

from __future__ import annotations

from pathlib import Path

from personal_knowledge_agent.discovery.models import FileRecord
from personal_knowledge_agent.ingestion.models import (
    ExtractedDocument,
    ExtractedSection,
)


class TextExtractor:
    """Extract a supported text file as one section without altering its content."""

    def extract(self, source_path: Path, metadata: FileRecord) -> ExtractedDocument:
        """Read *source_path* as UTF-8 and retain its discovery metadata path."""
        try:
            contents = source_path.read_bytes()
        except OSError as error:
            return _failed_result(metadata, f"Could not read text file: {error}")

        if b"\x00" in contents:
            return _failed_result(metadata, "Text file appears to contain binary data")

        try:
            text = contents.decode("utf-8")
        except UnicodeDecodeError as error:
            return _failed_result(
                metadata, f"Could not decode text file as UTF-8: {error}"
            )

        return ExtractedDocument(
            relative_path=metadata.relative_path,
            file_type=metadata.extension.lstrip(".").lower(),
            status="success",
            sections=[
                ExtractedSection(
                    section_id="document",
                    section_type="text",
                    text=text,
                )
            ],
        )


def _failed_result(metadata: FileRecord, message: str) -> ExtractedDocument:
    return ExtractedDocument(
        relative_path=metadata.relative_path,
        file_type=metadata.extension.lstrip(".").lower(),
        status="failed",
        sections=[],
        errors=[message],
    )
