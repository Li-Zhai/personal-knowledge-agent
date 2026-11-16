# Personal Knowledge Agent

Keep generated inventory and extraction files outside the academic archive. First
create an inventory from the archive root:

```bash
uv run personal-knowledge-agent scan \
  "/path/to/academic/archive" \
  --output data/inventory.json
```

Then ingest that inventory using the same archive root:

```bash
uv run personal-knowledge-agent ingest \
  --inventory data/inventory.json \
  --root "/path/to/academic/archive" \
  --output data/extracted.json
```

The output is an object with `total_documents` and an ordered `documents` list.
Each document retains its relative path, file type, status, warnings/errors, and
ordered sections. Sections retain their identifier, type, text, PDF page number
when applicable, and `needs_ocr` flag.

Discovery errors are retained in the inventory. If present, ingestion reports
their count in its summary and includes them as `discovery_errors` in the output;
they remain distinct from document extraction failures.

Exit code `0` indicates a completed batch (individual document failures are
recorded in the output). Exit code `1` indicates an inventory, archive-root, or
output setup failure. Invalid command-line arguments exit with code `2`.
