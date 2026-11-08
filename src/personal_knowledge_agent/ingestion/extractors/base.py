"""Common contract for native document extractors."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from personal_knowledge_agent.discovery.models import FileRecord
from personal_knowledge_agent.ingestion.models import ExtractedDocument


class DocumentExtractor(Protocol):
    """Extract structured text from a discovered source file."""

    def extract(self, source_path: Path, metadata: FileRecord) -> ExtractedDocument:
        """Return the standardized extraction result for *source_path*."""
        ...
