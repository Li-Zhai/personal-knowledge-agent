"""Jupyter notebook extraction without executing cells or reading outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from personal_knowledge_agent.discovery.models import FileRecord
from personal_knowledge_agent.ingestion.models import (
    ExtractedDocument,
    ExtractedSection,
)


class NotebookExtractor:
    """Extract markdown and code cells from a Jupyter notebook."""

    def extract(self, source_path: Path, metadata: FileRecord) -> ExtractedDocument:
        """Parse *source_path* and retain source cell order and boundaries."""
        try:
            with source_path.open(encoding="utf-8") as notebook_file:
                notebook = json.load(notebook_file)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            return _failed_result(metadata, f"Could not read notebook: {error}")

        if not isinstance(notebook, dict) or not isinstance(
            notebook.get("cells"), list
        ):
            return _failed_result(metadata, "Notebook has no valid cells list")

        sections: list[ExtractedSection] = []
        warnings: list[str] = []
        invalid_cells = 0
        for cell_index, cell in enumerate(notebook["cells"], start=1):
            if not isinstance(cell, dict):
                invalid_cells += 1
                warnings.append(f"Cell {cell_index} is not an object and was skipped")
                continue

            cell_type = cell.get("cell_type")
            if cell_type not in {"markdown", "code"}:
                warnings.append(
                    f"Cell {cell_index} has unsupported type {cell_type!r} and was skipped"
                )
                continue

            source = cell.get("source", "")
            text = _source_text(source)
            if text is None:
                invalid_cells += 1
                warnings.append(f"Cell {cell_index} has invalid source and was skipped")
                continue

            sections.append(
                ExtractedSection(
                    section_id=f"cell-{cell_index}",
                    section_type=cell_type,
                    text=text,
                )
            )

        return ExtractedDocument(
            relative_path=metadata.relative_path,
            file_type="ipynb",
            status="partial" if invalid_cells else "success",
            sections=sections,
            warnings=warnings,
        )


def _source_text(source: Any) -> str | None:
    """Return notebook source while accepting the two JSON forms Jupyter writes."""
    if isinstance(source, str):
        return source
    if isinstance(source, list) and all(isinstance(line, str) for line in source):
        return "".join(source)
    return None


def _failed_result(metadata: FileRecord, message: str) -> ExtractedDocument:
    return ExtractedDocument(
        relative_path=metadata.relative_path,
        file_type="ipynb",
        status="failed",
        sections=[],
        errors=[message],
    )
