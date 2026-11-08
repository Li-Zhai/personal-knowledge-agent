"""Standardized representations for document text extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ExtractionStatus = Literal["success", "partial", "needs_ocr", "unsupported", "failed"]


@dataclass(frozen=True, slots=True)
class ExtractedSection:
    """Text extracted from one addressable portion of a document."""

    section_id: str
    section_type: str
    text: str
    page_number: int | None = None
    needs_ocr: bool = False


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """The result of extracting native text from one source document."""

    relative_path: str
    file_type: str
    status: ExtractionStatus
    sections: list[ExtractedSection]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
