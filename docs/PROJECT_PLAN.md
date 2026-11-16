# Personal Knowledge Agent — Project Plan

Canonical, living roadmap. Last verified: 2026-11-15.
Update this document when milestones, evidence, or architectural decisions change.
Keep implementation details in milestone-specific plans; see the [README](../README.md)
for CLI usage and [AGENT.md](../AGENT.md) for repository operating rules.

## 1. Project vision

Build a personal AI knowledge agent for an undergraduate and master's academic
archive: lecture slides, handwritten assignments, mathematical notes, Jupyter
notebooks, source code, and other documents in deeply nested directories.

The final product should combine keyword and semantic search, retrieval-augmented
question answering, and an LLM agent that can use retrieval and source-inspection
tools. Answers should cite original files and PDF pages accurately.
The objective is useful, trustworthy knowledge retrieval; perfect transcription
is not required to deliver value.

## 2. High-level architecture

```text
Read-only academic archive
  → recursive discovery → inventory JSON                         [implemented]
  → format-specific native extraction → document/section JSON    [implemented]
  → selective OCR with native/OCR provenance                     [planned]
  → structure-aware chunks → persistent keyword/vector indexes   [planned]
  → hybrid retrieval and ranking                                [planned]
  → LLM agent + retrieval/source tools → cited answers            [planned]
Evaluation and integrity checks span the pipeline.
```

The Python package uses a `src/` layout. `discovery/` owns traversal and file
metadata; `ingestion/` owns extractor dispatch, standardized results, and JSON I/O;
`cli.py` exposes `scan` and `ingest`. Retrieval and agent layers do not yet exist.
Generated inventories, extracted text, and future indexes stay outside the archive.

Inventory records retain relative paths, extensions, sizes, and modification times.
Extraction results retain relative paths, file types, statuses, errors/warnings,
and ordered sections with identifiers, types, text, PDF page numbers where applicable,
and `needs_ocr` flags. Explicit native/OCR provenance is still future work.

## 3. Master roadmap

**Status key:** Complete = implemented and verified; Active = work underway;
Planned = intended work not yet implemented; Deferred = outside current scope.
The active planning focus is Stage 3A; no Stage 3 implementation is claimed.

### Stage 1 — File Discovery · Complete

- Recursive scanning and standardized file records; deterministic inventory JSON.
- Relative paths preserve nested archive structure; symlinks are skipped and
  recoverable discovery errors are recorded separately.
- Completion criteria met: metadata and nested paths are preserved, discovery
  errors do not discard readable files, and CLI output stays outside the archive.
- Evidence: `discovery/`, scanner/CLI tests, and the saved 283-file inventory.

### Stage 2 — Document Ingestion · Complete

- **2A:** PyMuPDF native PDF extraction with ordered page sections, retained blank
  pages, errors/warnings, and preliminary OCR-candidate flags.
- **2B:** UTF-8 `.txt`, `.md`, and `.py` extraction; `.ipynb` markdown/code cells
  preserve order and boundaries without executing code or extracting outputs.
- **2C:** Inventory-driven CLI ingestion and structured JSON output; per-document
  failures are isolated and unsupported files receive explicit result records.
- **Cross-stage integrity and data safety:** validated inventory paths, archive-root
  containment, protected output destinations, atomic JSON writes, and propagation
  of discovery errors separately from extraction failures.
- Completion criteria met: supported formats flow through the CLI with document
  and section traceability, failures remain visible without stopping the batch,
  and tested output safeguards protect source materials and the input inventory.

Verification snapshot (2026-11-15):

| Measure | Verified result |
| --- | --- |
| Automated tests | 33 passed |
| Inventory files / ingestion result records | 283 / 283 |
| Extracted sections | 2,961 |
| Document-level extraction failures | 0 |
| Unsupported files | 155 |
| OCR candidates | 32 documents / 237 PDF pages |
| Status breakdown | 96 success, 19 partial, 13 needs_ocr, 155 unsupported |

Evidence: current source and tests, `data/scan-test-output.json`, and
`data/extracted.json`. Counts match the supplied historical report. Tests were
rerun locally (`.venv/bin/python -m pytest -q`); archive counts were recomputed
from saved JSON, not from a fresh archive extraction. Neither saved artifact
records a run timestamp or code revision, so its exact generation context is unknown.
No discovery errors or document error entries appear in these saved results.
Tests emit PyMuPDF/SWIG deprecation warnings. Zero failures does not establish
extraction completeness or retrieval quality, and 283 records includes unsupported files.

### Stage 3 — OCR & Mathematical Content Extraction · Planned

| Milestone | Intended deliverable | Status |
| --- | --- | --- |
| 3A | Representative OCR benchmark and evidence-based recommendation | Planned — next |
| 3B | Distinguishable native/OCR text provenance model | Planned |
| 3C | Selective OCR supplementing native extraction | Planned |
| 3D | Mixed-content handling and OCR-candidate refinement | Planned |
| 3E | Mathematical recognition experiments and documented limits | Planned — experimental |
| 3F | Full-archive validation and integrity review | Planned |

The sequence preserves native text and traceability while testing whether OCR
adds useful content. Detailed acceptance thresholds and tool choices are not yet
finalized. Mathematical recognition success is not a gate for retrieval work.

### Stage 4 — Chunking & Indexing · Planned

Structure-aware chunks, source metadata, embeddings, persistent storage, and
incremental indexing. Preserve links from chunks to original files and sections.

### Stage 5 — Retrieval · Planned

Keyword, semantic, and hybrid search; relevance ranking and retrieval evaluation.

### Stage 6 — Knowledge Agent · Planned

LLM integration, retrieval tools, multi-step reasoning, source inspection, and
citation-grounded answers.

### Stage 7 — Evaluation & Reliability · Planned

End-to-end benchmarks, retrieval accuracy, citation correctness, hallucination
prevention, performance, and reliability improvements. Earlier milestone checks
remain necessary; evaluation is not postponed entirely until this stage.

Stages 4–7 are high-level commitments only. Detailed implementation plans,
technology choices, and completion criteria remain to be defined.

## 4. Current milestone and immediate next steps

**Next milestone: Stage 3A — Representative OCR benchmark.**
Active work is planning this benchmark; OCR integration has not started.

1. Select representative native-text, scanned, handwritten, mathematical,
   graph-heavy, and mixed-content pages, including sparse native pages as controls.
2. Define a small reference set and evaluation rubric for useful text recovery,
   source/page fidelity, errors, runtime, and operational/privacy constraints.
3. Compare candidate OCR approaches against the native-extraction baseline;
   record gains, regressions, and cases where OCR adds no value.
4. Recommend an approach and identify requirements for 3B/3C before integration.

Proposed 3A completion criteria, for review: a documented representative sample,
repeatable comparison, qualitative/error and runtime results, and a justified
recommendation or explicit finding that further investigation is needed.
Sample size, engines, and numeric quality thresholds remain open decisions.

## 5. Important architectural decisions

- **Read-only sources:** academic materials are irreplaceable. Read them without
  modification; keep generated artifacts separate and retain output safety checks.
- **Traceability throughout:** document paths, section identifiers, and PDF pages
  provide the foundation for inspection and future citations; preserve these links.
- **OCR supplements native text:** retain useful native extraction to avoid
  replacing reliable text with recognition errors or losing mixed-content material.
- **Explicit provenance:** future native and OCR text must be distinguishable so
  downstream retrieval and inspection can assess their origin. `needs_ocr` alone
  is a candidate flag, not an implemented provenance model.
- **Mathematics is experimental:** handwriting and formula recognition may improve
  coverage, but must not block building and evaluating useful retrieval.
- **Incremental, testable development:** add abstractions and dependencies only
  for demonstrated needs; verify each milestone before expanding scope.
- **Retrieval usefulness governs fidelity:** prioritize information that helps
  answer real archive questions over perfect layout or transcription.
- **Local data control:** do not transmit archive contents to external services
  without explicit authorization; include this constraint in OCR/LLM choices.

## 6. Deferred work and known limitations

**Deferred options, not committed format requirements:** ZIP, XLSX, CSV, TSV,
DOCX, HTML, `.tm`, and other unsupported formats. Saved results also include
extensionless files and `.pyc`; not every discovered file needs a future extractor.
Prioritize additional formats only when their retrieval value justifies the work.

**Deferred advanced capabilities:** mathematical OCR beyond the bounded 3E
experiments, detailed layout reconstruction, and semantic interpretation of graphs
or diagrams. These are not prerequisites for the core retrieval pipeline.

**Known current limitations:** PDF extraction returns native text, not visual or
graph understanding. The OCR heuristic flags pages with fewer than 20 stripped
characters: sparse pages can be false positives, while pages with native text
plus image-only notes or equations can be missed. Graph-heavy PDFs may lose
meaning despite having enough text to avoid a flag; archive-wide impact is unmeasured.
Text support is limited to the listed extensions and UTF-8; binary/invalid text
fails explicitly. Notebook outputs and raw cells are excluded. Password-protected
and corrupted PDFs fail explicitly. Symlinked archive content is not discovered.

**Outstanding committed work:** Stages 3–7 above, including provenance, candidate
refinement, incremental indexing, retrieval evaluation, and citation-grounded answers.
No discrepancy with the supplied historical status was found; saved extraction
counts are not proof of full archive coverage, OCR quality, or answer quality.
