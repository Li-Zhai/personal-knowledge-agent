from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from personal_knowledge_agent.cli import main
from personal_knowledge_agent.discovery.models import FileRecord, ScanResult
from personal_knowledge_agent.discovery.scanner import scan_directory
from personal_knowledge_agent.ingestion.io import (
    InventoryError,
    load_inventory,
    validate_paths_within_root,
    write_inventory_output,
)


def _write_pdf(path: Path, text: str) -> None:
    document = pymupdf.open()
    try:
        document.new_page().insert_text((72, 72), text)
        document.save(path)
    finally:
        document.close()


def _write_inventory(path: Path, root: Path) -> None:
    path.write_text(json.dumps(scan_directory(root).to_dict()), encoding="utf-8")


def test_ingest_cli_loads_inventory_and_serializes_mixed_documents(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archive with spaces"
    archive.mkdir()
    _write_pdf(
        archive / "01-lecture.pdf",
        "This PDF has enough native text for the ingestion test.",
    )
    (archive / "02-notes.txt").write_text("café notes\n", encoding="utf-8")
    (archive / "03-分析.ipynb").write_text(
        json.dumps(
            {
                "cells": [
                    {"cell_type": "markdown", "source": "# Title\n"},
                    {"cell_type": "code", "source": ["answer = 42\n"]},
                ]
            }
        ),
        encoding="utf-8",
    )
    (archive / "04-data.csv").write_text("a,b\n", encoding="utf-8")
    inventory = tmp_path / "inventory.json"
    output = tmp_path / "output" / "extracted.json"
    _write_inventory(inventory, archive)

    exit_code = main(
        [
            "ingest",
            "--inventory",
            str(inventory),
            "--root",
            str(archive),
            "--output",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["total_documents"] == 4
    assert [document["relative_path"] for document in payload["documents"]] == [
        "01-lecture.pdf",
        "02-notes.txt",
        "03-分析.ipynb",
        "04-data.csv",
    ]
    assert [document["status"] for document in payload["documents"]] == [
        "success",
        "success",
        "success",
        "unsupported",
    ]
    assert payload["documents"][0]["sections"][0] == {
        "section_id": "page-1",
        "section_type": "page",
        "text": "This PDF has enough native text for the ingestion test.\n",
        "page_number": 1,
        "needs_ocr": False,
    }
    assert [
        section["section_id"] for section in payload["documents"][2]["sections"]
    ] == [
        "cell-1",
        "cell-2",
    ]
    assert "Processed 4 documents" in capsys.readouterr().out


def test_inventory_loader_reconstructs_records_and_validates_paths(
    tmp_path: Path,
) -> None:
    inventory = tmp_path / "inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "relative_path": "nested/å.txt",
                        "extension": ".txt",
                        "size_bytes": 4,
                        "modified_at": "2026-01-01T00:00:00Z",
                    }
                ],
                "errors": [],
                "total_files": 1,
            }
        ),
        encoding="utf-8",
    )
    root = tmp_path / "root"
    root.mkdir()

    files = load_inventory(inventory)

    assert files == [FileRecord("nested/å.txt", ".txt", 4, "2026-01-01T00:00:00Z")]
    assert validate_paths_within_root(root, files) == root.resolve()


def test_ingest_cli_records_missing_source_without_stopping_batch(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "available.txt").write_text("available", encoding="utf-8")
    inventory = tmp_path / "inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "relative_path": "missing.txt",
                        "extension": ".txt",
                        "size_bytes": 0,
                        "modified_at": "2026-01-01T00:00:00Z",
                    },
                    {
                        "relative_path": "available.txt",
                        "extension": ".txt",
                        "size_bytes": 9,
                        "modified_at": "2026-01-01T00:00:00Z",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "extracted.json"

    assert (
        main(
            [
                "ingest",
                "--inventory",
                str(inventory),
                "--root",
                str(archive),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    documents = json.loads(output.read_text(encoding="utf-8"))["documents"]
    assert [document["status"] for document in documents] == ["failed", "success"]


def test_ingest_cli_preserves_discovery_errors_in_summary_and_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "available.txt").write_text("available", encoding="utf-8")
    inventory = tmp_path / "inventory.json"
    discovery_errors = [
        {"path": "archive/unreadable.txt", "message": "permission denied"}
    ]
    inventory.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "relative_path": "available.txt",
                        "extension": ".txt",
                        "size_bytes": 9,
                        "modified_at": "2026-01-01T00:00:00Z",
                    }
                ],
                "errors": discovery_errors,
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "extracted.json"

    assert (
        main(
            [
                "ingest",
                "--inventory",
                str(inventory),
                "--root",
                str(archive),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["documents"][0]["status"] == "success"
    assert payload["documents"][0]["errors"] == []
    assert payload["discovery_errors"] == discovery_errors
    assert "Discovery errors: 1" in capsys.readouterr().out


def test_ingest_cli_rejects_bad_inventory_and_escaping_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    inventory = tmp_path / "inventory.json"
    output = tmp_path / "extracted.json"
    output.write_text("existing output", encoding="utf-8")
    inventory.write_text("{not json", encoding="utf-8")

    assert (
        main(
            [
                "ingest",
                "--inventory",
                str(inventory),
                "--root",
                str(archive),
                "--output",
                str(output),
            ]
        )
        == 1
    )
    assert output.read_text(encoding="utf-8") == "existing output"
    assert "Inventory JSON is invalid" in capsys.readouterr().err

    inventory.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "relative_path": "../outside.txt",
                        "extension": ".txt",
                        "size_bytes": 0,
                        "modified_at": "2026-01-01T00:00:00Z",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "ingest",
                "--inventory",
                str(inventory),
                "--root",
                str(archive),
                "--output",
                str(output),
            ]
        )
        == 1
    )
    assert "escapes the archive root" in capsys.readouterr().err


def test_ingest_cli_rejects_source_archive_and_inventory_destinations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    source = archive / "notes.txt"
    source.write_text("original academic material", encoding="utf-8")
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory, archive)
    original_inventory = inventory.read_text(encoding="utf-8")

    assert (
        main(
            [
                "ingest",
                "--inventory",
                str(inventory),
                "--root",
                str(archive),
                "--output",
                str(source),
            ]
        )
        == 1
    )
    assert source.read_text(encoding="utf-8") == "original academic material"
    assert "outside the archive root" in capsys.readouterr().err

    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(archive, target_is_directory=True)
    assert (
        main(
            [
                "ingest",
                "--inventory",
                str(inventory),
                "--root",
                str(archive),
                "--output",
                str(linked_parent / "notes.txt"),
            ]
        )
        == 1
    )
    assert source.read_text(encoding="utf-8") == "original academic material"
    assert "outside the archive root" in capsys.readouterr().err

    assert (
        main(
            [
                "ingest",
                "--inventory",
                str(inventory),
                "--root",
                str(archive),
                "--output",
                str(inventory),
            ]
        )
        == 1
    )
    assert inventory.read_text(encoding="utf-8") == original_inventory
    assert "must not be the input inventory" in capsys.readouterr().err


def test_ingest_cli_reports_unwritable_output_destination(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "note.txt").write_text("note", encoding="utf-8")
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory, archive)
    output_parent = tmp_path / "not-a-directory"
    output_parent.write_text("file", encoding="utf-8")

    assert (
        main(
            [
                "ingest",
                "--inventory",
                str(inventory),
                "--root",
                str(archive),
                "--output",
                str(output_parent / "result.json"),
            ]
        )
        == 1
    )
    assert "Could not write output" in capsys.readouterr().err


def test_load_inventory_rejects_missing_and_malformed_records(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(InventoryError, match="Could not read inventory"):
        load_inventory(missing)

    malformed = tmp_path / "malformed.json"
    malformed.write_text(json.dumps({"files": [{}]}), encoding="utf-8")
    with pytest.raises(InventoryError, match="missing required metadata"):
        load_inventory(malformed)


def test_inventory_write_is_atomic_when_replacement_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "inventory.json"
    output.write_text("previous inventory", encoding="utf-8")
    result = ScanResult(files=[], errors=[])

    def fail_replace(source: Path, destination: Path) -> Path:
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="Could not write inventory"):
        write_inventory_output(output, result)

    assert output.read_text(encoding="utf-8") == "previous inventory"
    assert list(tmp_path.glob(".inventory.json.*.tmp")) == []
