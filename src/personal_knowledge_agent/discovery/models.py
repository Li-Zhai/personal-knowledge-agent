"""Data structures used by the read-only file-discovery stage."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class FileRecord:
    """Metadata for one regular file found below a scan root."""

    relative_path: str
    extension: str
    size_bytes: int
    modified_at: str


@dataclass(frozen=True, slots=True)
class ScanError:
    """A filesystem error that did not prevent the rest of a scan."""

    path: str
    message: str


@dataclass(frozen=True, slots=True)
class ScanResult:
    """The serializable output of a directory scan."""

    files: list[FileRecord]
    errors: list[ScanError]

    def to_dict(self) -> dict[str, object]:
        """Return the JSON-compatible inventory format."""
        return {
            "total_files": len(self.files),
            "files": [asdict(file) for file in self.files],
            "errors": [asdict(error) for error in self.errors],
        }
