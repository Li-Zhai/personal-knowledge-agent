from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from personal_knowledge_agent.discovery.scanner import scan_directory
from personal_knowledge_agent.ingestion.pipeline import ingest_discovered_files


def _write_pdf(path: Path, text: str) -> None:
    document = pymupdf.open()
    try:
        document.new_page().insert_text((72, 72), text)
        document.save(path)
    finally:
        document.close()


def test_pipeline_dispatches_mixed_documents_and_preserves_metadata(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "01-document.pdf"
    text = tmp_path / "02-notes.txt"
    notebook = tmp_path / "03-analysis.ipynb"
    unknown = tmp_path / "04-data.csv"
    _write_pdf(pdf, "A sufficiently long PDF page for ingestion verification.")
    text.write_text("notes\n", encoding="utf-8")
    notebook.write_text(
        json.dumps({"cells": [{"cell_type": "code", "source": "x = 1\n"}]}),
        encoding="utf-8",
    )
    unknown.write_text("a,b\n1,2\n", encoding="utf-8")

    inventory = scan_directory(tmp_path)
    results = ingest_discovered_files(tmp_path, inventory.files)

    assert [result.relative_path for result in results] == [
        "01-document.pdf",
        "02-notes.txt",
        "03-analysis.ipynb",
        "04-data.csv",
    ]
    assert [result.file_type for result in results] == ["pdf", "txt", "ipynb", "csv"]
    assert [result.status for result in results] == [
        "success",
        "success",
        "success",
        "unsupported",
    ]
    assert results[2].sections[0].section_type == "code"
    assert results[3].warnings == ["Unsupported file type: .csv"]


def test_pipeline_continues_after_text_decoding_failure(tmp_path: Path) -> None:
    invalid = tmp_path / "01-invalid.txt"
    valid = tmp_path / "02-valid.md"
    invalid.write_bytes(b"\xff")
    valid.write_text("# Works\n", encoding="utf-8")

    inventory = scan_directory(tmp_path)
    results = ingest_discovered_files(tmp_path, inventory.files)

    assert [result.status for result in results] == ["failed", "success"]
    assert results[1].sections[0].text == "# Works\n"
