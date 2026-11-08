from __future__ import annotations

from pathlib import Path

import pymupdf

from personal_knowledge_agent.discovery.models import FileRecord
from personal_knowledge_agent.discovery.scanner import scan_directory
from personal_knowledge_agent.ingestion.extractors.pdf import PdfTextExtractor
from personal_knowledge_agent.ingestion.pipeline import ingest_discovered_files


def _file_record(path: Path, root: Path) -> FileRecord:
    return FileRecord(
        relative_path=path.relative_to(root).as_posix(),
        extension=path.suffix,
        size_bytes=path.stat().st_size,
        modified_at="2026-01-01T00:00:00Z",
    )


def _write_pdf(path: Path, page_text: list[str]) -> None:
    document = pymupdf.open()
    try:
        for text in page_text:
            page = document.new_page()
            if text:
                page.insert_text((72, 72), text)
        document.save(path)
    finally:
        document.close()


def test_pdf_extractor_preserves_page_order_numbers_and_blank_pages(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "course" / "lecture.pdf"
    pdf.parent.mkdir()
    _write_pdf(
        pdf,
        [
            "First page has enough native text to be meaningful.",
            "",
            "Third page is also meaningful native text.",
        ],
    )

    result = PdfTextExtractor().extract(pdf, _file_record(pdf, tmp_path))

    assert result.relative_path == "course/lecture.pdf"
    assert result.file_type == "pdf"
    assert result.status == "partial"
    assert [section.section_id for section in result.sections] == [
        "page-1",
        "page-2",
        "page-3",
    ]
    assert [section.page_number for section in result.sections] == [1, 2, 3]
    assert [section.text for section in result.sections] == [
        "First page has enough native text to be meaningful.\n",
        "",
        "Third page is also meaningful native text.\n",
    ]
    assert result.sections[1].needs_ocr is True


def test_pdf_extractor_marks_text_poor_pages_and_document_needing_ocr(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "scanned.pdf"
    _write_pdf(pdf, ["title", ""])

    result = PdfTextExtractor().extract(pdf, _file_record(pdf, tmp_path))

    assert result.status == "needs_ocr"
    assert [section.needs_ocr for section in result.sections] == [True, True]
    assert len(result.warnings) == 2


def test_pdf_extractor_reports_success_for_pages_with_meaningful_native_text(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "native.pdf"
    _write_pdf(pdf, ["This page contains enough text to be treated as native content."])

    result = PdfTextExtractor().extract(pdf, _file_record(pdf, tmp_path))

    assert result.status == "success"
    assert result.errors == []
    assert result.sections[0].needs_ocr is False


def test_pdf_extractor_handles_corrupted_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "broken.pdf"
    pdf.write_bytes(b"not a PDF")

    result = PdfTextExtractor().extract(pdf, _file_record(pdf, tmp_path))

    assert result.status == "failed"
    assert result.sections == []
    assert len(result.errors) == 1


def test_pdf_extractor_handles_password_protected_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "protected.pdf"
    document = pymupdf.open()
    try:
        document.new_page().insert_text((72, 72), "Protected PDF content")
        document.save(
            pdf,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="owner-password",
            user_pw="user-password",
        )
    finally:
        document.close()

    result = PdfTextExtractor().extract(pdf, _file_record(pdf, tmp_path))

    assert result.status == "failed"
    assert result.sections == []
    assert "password-protected" in result.errors[0]


def test_pipeline_uses_discovered_records_preserves_order_and_isolates_failures(
    tmp_path: Path,
) -> None:
    broken_pdf = tmp_path / "01-broken.pdf"
    valid_pdf = tmp_path / "02-valid.pdf"
    ignored_text = tmp_path / "03-notes.txt"
    broken_pdf.write_bytes(b"not a PDF")
    _write_pdf(
        valid_pdf, ["A sufficiently long valid PDF page follows a broken document."]
    )
    ignored_text.write_text("not in scope", encoding="utf-8")

    inventory = scan_directory(tmp_path)
    results = ingest_discovered_files(tmp_path, inventory.files)

    assert [result.relative_path for result in results] == [
        "01-broken.pdf",
        "02-valid.pdf",
        "03-notes.txt",
    ]
    assert [result.status for result in results] == ["failed", "success", "unsupported"]
    assert results[1].sections[0].page_number == 1
