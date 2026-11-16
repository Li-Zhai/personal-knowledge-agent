"""Inventory and JSON I/O helpers for command-line ingestion."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from personal_knowledge_agent.discovery.models import FileRecord, ScanError, ScanResult
from personal_knowledge_agent.ingestion.models import ExtractedDocument


class InventoryError(ValueError):
    """Raised when a discovery inventory cannot be used for ingestion."""


@dataclass(frozen=True, slots=True)
class LoadedInventory:
    """The usable records and non-fatal discovery errors from an inventory."""

    files: list[FileRecord]
    errors: list[ScanError]


def load_inventory(path: str | Path) -> list[FileRecord]:
    """Load Stage 1 file records from a JSON inventory.

    This compatibility helper retains the original list-only interface. Call
    :func:`load_inventory_with_errors` when discovery errors are also needed.
    """
    return load_inventory_with_errors(path).files


def load_inventory_with_errors(path: str | Path) -> LoadedInventory:
    """Load Stage 1 file records and its non-fatal discovery errors."""
    inventory_path = Path(path)
    try:
        with inventory_path.open(encoding="utf-8") as inventory_file:
            data = json.load(inventory_file)
    except OSError as error:
        raise InventoryError(
            f"Could not read inventory {inventory_path}: {error}"
        ) from error
    except json.JSONDecodeError as error:
        raise InventoryError(f"Inventory JSON is invalid: {error}") from error

    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        raise InventoryError("Inventory must contain a 'files' list")

    files: list[FileRecord] = []
    for index, item in enumerate(data["files"], start=1):
        if not isinstance(item, dict):
            raise InventoryError(f"Inventory file {index} must be an object")
        files.append(_file_record_from_dict(item, index))

    errors_data = data.get("errors", [])
    if not isinstance(errors_data, list):
        raise InventoryError("Inventory 'errors' must be a list")
    errors: list[ScanError] = []
    for index, item in enumerate(errors_data, start=1):
        if not isinstance(item, dict):
            raise InventoryError(f"Inventory error {index} must be an object")
        errors.append(_scan_error_from_dict(item, index))
    return LoadedInventory(files=files, errors=errors)


def validate_paths_within_root(root: str | Path, files: list[FileRecord]) -> Path:
    """Return a usable root after ensuring every inventory path stays below it."""
    root_path = Path(root).expanduser()
    try:
        resolved_root = root_path.resolve(strict=True)
    except OSError as error:
        raise InventoryError(
            f"Could not access archive root {root_path}: {error}"
        ) from error
    if not resolved_root.is_dir():
        raise InventoryError(f"Archive root is not a directory: {root_path}")
    if not os.access(resolved_root, os.R_OK | os.X_OK):
        raise InventoryError(f"Archive root is not readable: {root_path}")

    for file in files:
        relative_path = Path(file.relative_path)
        if relative_path.is_absolute():
            raise InventoryError(
                f"Inventory path must be relative to the archive root: {file.relative_path}"
            )
        try:
            (resolved_root / relative_path).resolve(strict=False).relative_to(
                resolved_root
            )
        except ValueError as error:
            raise InventoryError(
                f"Inventory path escapes the archive root: {file.relative_path}"
            ) from error
    return resolved_root


def extraction_output(
    documents: list[ExtractedDocument],
    *,
    discovery_errors: list[ScanError] | None = None,
) -> dict[str, object]:
    """Return the stable, JSON-compatible extraction output representation."""
    output: dict[str, object] = {
        "total_documents": len(documents),
        "documents": [asdict(document) for document in documents],
    }
    if discovery_errors:
        output["discovery_errors"] = [asdict(error) for error in discovery_errors]
    return output


def write_extraction_output(
    path: str | Path,
    documents: list[ExtractedDocument],
    *,
    discovery_errors: list[ScanError] | None = None,
) -> None:
    """Atomically write extraction results, leaving no partial destination on error."""
    _write_json_atomically(
        path,
        extraction_output(documents, discovery_errors=discovery_errors),
        "output",
    )


def write_inventory_output(path: str | Path, result: ScanResult) -> None:
    """Atomically write a discovery inventory, leaving no partial destination."""
    _write_json_atomically(path, result.to_dict(), "inventory")


def _write_json_atomically(
    path: str | Path, payload_data: dict[str, object], label: str
) -> None:
    output_path = Path(path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(payload_data, indent=2, ensure_ascii=False)
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            text=True,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as output_file:
                output_file.write(payload)
                output_file.write("\n")
            temporary_path.replace(output_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
    except (OSError, TypeError, ValueError) as error:
        raise OSError(f"Could not write {label} {output_path}: {error}") from error


def _file_record_from_dict(item: dict[str, Any], index: int) -> FileRecord:
    fields = ("relative_path", "extension", "size_bytes", "modified_at")
    if any(field not in item for field in fields):
        raise InventoryError(f"Inventory file {index} is missing required metadata")
    if not isinstance(item["relative_path"], str) or not item["relative_path"]:
        raise InventoryError(f"Inventory file {index} has an invalid relative_path")
    if not isinstance(item["extension"], str):
        raise InventoryError(f"Inventory file {index} has an invalid extension")
    if not isinstance(item["size_bytes"], int) or isinstance(item["size_bytes"], bool):
        raise InventoryError(f"Inventory file {index} has an invalid size_bytes")
    if not isinstance(item["modified_at"], str):
        raise InventoryError(f"Inventory file {index} has an invalid modified_at")
    return FileRecord(
        relative_path=item["relative_path"],
        extension=item["extension"],
        size_bytes=item["size_bytes"],
        modified_at=item["modified_at"],
    )


def _scan_error_from_dict(item: dict[str, Any], index: int) -> ScanError:
    if not isinstance(item.get("path"), str) or not item["path"]:
        raise InventoryError(f"Inventory error {index} has an invalid path")
    if not isinstance(item.get("message"), str) or not item["message"]:
        raise InventoryError(f"Inventory error {index} has an invalid message")
    return ScanError(path=item["path"], message=item["message"])
