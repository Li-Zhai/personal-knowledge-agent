"""Read-only recursive filesystem discovery."""

from __future__ import annotations

import logging
import stat
from datetime import UTC, datetime
from pathlib import Path

from personal_knowledge_agent.discovery.models import FileRecord, ScanError, ScanResult

logger = logging.getLogger(__name__)


def scan_directory(root: str | Path) -> ScanResult:
    """Inventory regular files beneath *root* without reading their contents.

    Symbolic links are skipped. Recoverable filesystem errors are returned in the
    result and logged as warnings so one inaccessible path does not stop a scan.
    """
    root_path = Path(root).expanduser()
    files: list[FileRecord] = []
    errors: list[ScanError] = []

    try:
        if root_path.is_symlink():
            _record_error(errors, root_path, "scan root must not be a symbolic link")
            return ScanResult(files=files, errors=errors)
        if not root_path.is_dir():
            _record_error(errors, root_path, "scan root is not a directory")
            return ScanResult(files=files, errors=errors)
    except OSError as error:
        _record_os_error(errors, root_path, error)
        return ScanResult(files=files, errors=errors)

    def on_error(error: OSError) -> None:
        _record_os_error(
            errors, Path(error.filename) if error.filename else root_path, error
        )

    for directory, directory_names, file_names in root_path.walk(
        top_down=True,
        follow_symlinks=False,
        on_error=on_error,
    ):
        traversable_directories: list[str] = []
        for name in directory_names:
            path = directory / name
            try:
                if not path.is_symlink():
                    traversable_directories.append(name)
            except OSError as error:
                _record_os_error(errors, path, error)
        directory_names[:] = sorted(traversable_directories)

        for name in sorted(file_names):
            path = directory / name
            try:
                if path.is_symlink():
                    continue
                metadata = path.stat()
            except OSError as error:
                _record_os_error(errors, path, error)
                continue

            if not stat.S_ISREG(metadata.st_mode):
                continue

            files.append(
                FileRecord(
                    relative_path=path.relative_to(root_path).as_posix(),
                    extension=path.suffix,
                    size_bytes=metadata.st_size,
                    modified_at=_utc_timestamp(metadata.st_mtime),
                )
            )

    return ScanResult(files=files, errors=errors)


def _utc_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat().replace("+00:00", "Z")


def _record_os_error(errors: list[ScanError], path: Path, error: OSError) -> None:
    _record_error(errors, path, str(error))


def _record_error(errors: list[ScanError], path: Path, message: str) -> None:
    scan_error = ScanError(path=str(path), message=message)
    errors.append(scan_error)
    logger.warning("Could not inspect %s: %s", scan_error.path, scan_error.message)
