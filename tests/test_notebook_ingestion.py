from __future__ import annotations

import json
from pathlib import Path

from personal_knowledge_agent.discovery.models import FileRecord
from personal_knowledge_agent.ingestion.extractors.notebook import NotebookExtractor


def _file_record(path: Path, root: Path) -> FileRecord:
    return FileRecord(
        relative_path=path.relative_to(root).as_posix(),
        extension=path.suffix,
        size_bytes=path.stat().st_size,
        modified_at="2026-01-01T00:00:00Z",
    )


def _write_notebook(path: Path, cells: list[object]) -> None:
    path.write_text(json.dumps({"cells": cells}), encoding="utf-8")


def test_notebook_extractor_preserves_markdown_code_order_and_boundaries(
    tmp_path: Path,
) -> None:
    notebook = tmp_path / "work" / "analysis.ipynb"
    notebook.parent.mkdir()
    _write_notebook(
        notebook,
        [
            {"cell_type": "markdown", "source": ["# Title\n", "Introduction\n"]},
            {
                "cell_type": "code",
                "source": "answer = 6 * 7\n",
                "outputs": [{"text": "42"}],
                "execution_count": 3,
            },
            {"cell_type": "markdown", "source": []},
        ],
    )

    result = NotebookExtractor().extract(notebook, _file_record(notebook, tmp_path))

    assert result.relative_path == "work/analysis.ipynb"
    assert result.file_type == "ipynb"
    assert result.status == "success"
    assert [
        (section.section_id, section.section_type, section.text)
        for section in result.sections
    ] == [
        ("cell-1", "markdown", "# Title\nIntroduction\n"),
        ("cell-2", "code", "answer = 6 * 7\n"),
        ("cell-3", "markdown", ""),
    ]
    assert "42" not in "".join(section.text for section in result.sections)


def test_notebook_extractor_handles_malformed_json(tmp_path: Path) -> None:
    notebook = tmp_path / "broken.ipynb"
    notebook.write_text("{not JSON", encoding="utf-8")

    result = NotebookExtractor().extract(notebook, _file_record(notebook, tmp_path))

    assert result.status == "failed"
    assert result.sections == []


def test_notebook_extractor_handles_invalid_cells_without_losing_positions(
    tmp_path: Path,
) -> None:
    notebook = tmp_path / "partial.ipynb"
    _write_notebook(
        notebook,
        [
            {"cell_type": "markdown"},
            {"cell_type": "code", "source": ["valid = True\n"]},
            {"cell_type": "code", "source": ["not", 1]},
            {"cell_type": "raw", "source": "not extracted"},
            "not a cell",
        ],
    )

    result = NotebookExtractor().extract(notebook, _file_record(notebook, tmp_path))

    assert result.status == "partial"
    assert [(section.section_id, section.text) for section in result.sections] == [
        ("cell-1", ""),
        ("cell-2", "valid = True\n"),
    ]
    assert len(result.warnings) == 3


def test_notebook_extractor_requires_a_cells_list(tmp_path: Path) -> None:
    notebook = tmp_path / "invalid.ipynb"
    notebook.write_text(json.dumps({"cells": {}}), encoding="utf-8")

    result = NotebookExtractor().extract(notebook, _file_record(notebook, tmp_path))

    assert result.status == "failed"
    assert "cells list" in result.errors[0]
