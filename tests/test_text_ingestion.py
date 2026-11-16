from __future__ import annotations

from pathlib import Path

import pytest

from personal_knowledge_agent.discovery.models import FileRecord
from personal_knowledge_agent.ingestion.extractors.text import TextExtractor


def _file_record(path: Path, root: Path) -> FileRecord:
    return FileRecord(
        relative_path=path.relative_to(root).as_posix(),
        extension=path.suffix,
        size_bytes=path.stat().st_size,
        modified_at="2026-01-01T00:00:00Z",
    )


@pytest.mark.parametrize(
    ("name", "contents", "file_type"),
    [
        ("notes.txt", "first line\n  second line\n", "txt"),
        ("readme.md", "# Heading\n\nParagraph\n", "md"),
        ("example.py", "def greet() -> str:\n    return 'hello'\n", "py"),
    ],
)
def test_text_extractor_preserves_utf8_content(
    tmp_path: Path, name: str, contents: str, file_type: str
) -> None:
    source = tmp_path / "nested" / name
    source.parent.mkdir()
    source.write_text(contents, encoding="utf-8")

    result = TextExtractor().extract(source, _file_record(source, tmp_path))

    assert result.relative_path == f"nested/{name}"
    assert result.file_type == file_type
    assert result.status == "success"
    assert [
        (section.section_id, section.section_type, section.text)
        for section in result.sections
    ] == [("document", "text", contents)]


def test_text_extractor_preserves_empty_files(tmp_path: Path) -> None:
    source = tmp_path / "empty.txt"
    source.write_text("", encoding="utf-8")

    result = TextExtractor().extract(source, _file_record(source, tmp_path))

    assert result.status == "success"
    assert result.sections[0].text == ""


def test_text_extractor_rejects_invalid_utf8(tmp_path: Path) -> None:
    source = tmp_path / "invalid.txt"
    source.write_bytes(b"\xff\xfe")

    result = TextExtractor().extract(source, _file_record(source, tmp_path))

    assert result.status == "failed"
    assert result.sections == []
    assert "UTF-8" in result.errors[0]


def test_text_extractor_rejects_binary_content(tmp_path: Path) -> None:
    source = tmp_path / "binary.py"
    source.write_bytes(b"print('not really source')\x00")

    result = TextExtractor().extract(source, _file_record(source, tmp_path))

    assert result.status == "failed"
    assert "binary" in result.errors[0]


def test_text_extractor_handles_missing_files(tmp_path: Path) -> None:
    source = tmp_path / "missing.txt"
    metadata = FileRecord(
        relative_path="missing.txt",
        extension=".txt",
        size_bytes=0,
        modified_at="2026-01-01T00:00:00Z",
    )

    result = TextExtractor().extract(source, metadata)

    assert result.status == "failed"
    assert result.sections == []
    assert "Could not read text file" in result.errors[0]
