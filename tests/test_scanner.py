from __future__ import annotations

import json
from pathlib import Path

import pytest

from personal_knowledge_agent.cli import main
from personal_knowledge_agent.discovery.scanner import scan_directory


def test_scan_directory_preserves_nested_relative_paths_and_metadata(
    tmp_path: Path,
) -> None:
    notes = tmp_path / "course" / "week-01"
    notes.mkdir(parents=True)
    lecture = notes / "lecture.pdf"
    lecture.write_bytes(b"notes")
    unfamiliar = tmp_path / "dataset.custom-format"
    unfamiliar.write_text("data", encoding="utf-8")
    (tmp_path / "empty").mkdir()

    result = scan_directory(tmp_path)

    records = {record.relative_path: record for record in result.files}
    assert result.errors == []
    assert result.to_dict()["total_files"] == 2
    assert records["course/week-01/lecture.pdf"].extension == ".pdf"
    assert records["course/week-01/lecture.pdf"].size_bytes == 5
    assert records["dataset.custom-format"].extension == ".custom-format"
    assert records["dataset.custom-format"].modified_at.endswith("Z")


def test_scan_directory_does_not_follow_symbolic_links(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "outside.txt").write_text("outside", encoding="utf-8")
    (tmp_path / "linked-directory").symlink_to(target, target_is_directory=True)
    (tmp_path / "linked-file.txt").symlink_to(target / "outside.txt")

    result = scan_directory(tmp_path)

    assert [record.relative_path for record in result.files] == ["target/outside.txt"]


def test_scan_directory_collects_mocked_stat_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    readable = tmp_path / "readable.txt"
    unreadable = tmp_path / "unreadable.txt"
    readable.write_text("available", encoding="utf-8")
    unreadable.write_text("unavailable", encoding="utf-8")
    original_stat = Path.stat

    def raising_stat(path: Path, *args: object, **kwargs: object) -> object:
        if path == unreadable:
            raise PermissionError("permission denied")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", raising_stat)

    result = scan_directory(tmp_path)

    assert [record.relative_path for record in result.files] == ["readable.txt"]
    assert len(result.errors) == 1
    assert result.errors[0].path == str(unreadable)
    assert "permission denied" in result.errors[0].message
    assert "Could not inspect" in caplog.text


def test_cli_writes_json_inventory(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "reading.txt").write_text("content", encoding="utf-8")
    output = tmp_path / "generated" / "inventory.json"

    exit_code = main(["scan", str(archive), "--output", str(output)])

    inventory = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert inventory["total_files"] == 1
    assert inventory["files"][0]["relative_path"] == "reading.txt"
    assert inventory["errors"] == []


def test_cli_refuses_to_write_within_scanned_directory(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    output = archive / "inventory.json"

    with pytest.raises(SystemExit, match="2"):
        main(["scan", str(archive), "--output", str(output)])

    assert not output.exists()
