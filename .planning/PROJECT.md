# para-files — Inbox Throughput

## What This Is

para-files is a macOS-only (Apple Silicon) intelligent file classification system using MLX-powered semantic routing. It implements the PARA method with a deterministic 6-signal classification pipeline. This milestone focuses on dramatically improving inbox throughput — reading Excel/ODS content, peeking inside ZIP archives, routing media files by extension, and providing a one-shot inbox processing workflow.

## Core Value

Files are classified correctly and transparently — users can understand why a file was placed where it was, and the pipeline fails loudly when something goes wrong.

## Current Milestone: v1.1 Inbox Throughput

**Goal:** Classify the majority of a large (800+) mixed-type inbox automatically, with near-zero files landing back in Inbox due to format blindness.

**Target features:**
- Excel/ODS content reading for semantic classification
- ZIP/7Z archive manifest peeking for content-based routing
- Extension-based catch-all routing for media and exotic file types
- One-shot inbox processing command

## Requirements

### Validated

- ✓ 6-signal classification pipeline (ValidatedDB → BookDetector → RulesEngine → DomainKB → SemanticRouter → LLM) — v1.0
- ✓ CLI commands: scan, move, classify, bookstore, learn, routes, dedupe, migrate, rescan, clean, init, config, tree — v1.0
- ✓ Typer-based CLI with --dry-run on classify and move commands — v1.0
- ✓ MLX embedding encoder with lazy loading and progressive truncation — v1.0
- ✓ Thema v1.6 book classification (9,187 codes) — v1.0
- ✓ Filename sanitization utilities — v1.0
- ✓ Feedback-based learning (learn command) — v1.0
- ✓ Centralized logging via loguru — v1.0
- ✓ Bug fixes: extension case sensitivity, OCR threshold, MLX zero-vector — v1.0
- ✓ --verbose signal display and JSON signals array — v1.0

### Active

- [ ] Excel/ODS files (.xlsx, .xls, .xlsm, .ods) content readable for semantic classification
- [ ] ZIP/7Z archive manifest peeked and used as classification signal
- [ ] Media files (.3gp, .m4v, .m4a, .mp3, .gif, .tif, .psd) routed by extension to fixed folders
- [ ] Exotic/rare file types (.p7b, .kdbx, .tax, .rtsz, .ps1, .asc, .potx) routed to sensible catch-all folders
- [ ] One-shot inbox processing: single command classifies and moves all files, leaving unclassified in place
- [ ] Progress display during bulk processing (count, current file, destination)
- [ ] Post-run summary: how many moved, how many stayed, breakdown by signal

### Out of Scope

- ISBN caching / retry logic — separate concern, defer
- Geolocation cache read-write lock — low impact, defer
- Async/await refactor of bookstore — large scope, defer
- MLX local model mirroring — infrastructure concern, defer
- Embedding LRU cache — premature optimization, defer
- Extracting/decompressing archives before classification — too slow and risky

## Context

Inbox analysis (2026-03-01): 817 files in `/Volumes/cloudsync/Fred/OneDrive4Business-LJF/PARA/0_Inbox`. Breakdown: 289 PDF, 188 ZIP/7Z, 178 Excel (xlsx/xls/xlsm/ods), 51 DOC/DOCX, 37 media, 62 exotic. The pipeline handles PDFs and text docs well. The three largest unhandled groups — Excel, archives, media — account for ~52% of the inbox and need targeted readers/routers.

## Constraints

- **Platform**: macOS Apple Silicon only — MLX and Vision Framework requirements
- **Python**: 3.12+ with strict mypy, ruff linting (line length 100)
- **Style**: Functional programming preferred, loguru for logging, pydantic for config
- **Testing**: Pytest; all new code must have tests
- **Dependencies**: openpyxl already available via xlsx reader; zipfile is stdlib; no new heavy deps

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Raise OCR confidence to 0.7 | 0.3 threshold causes renames on weak signals | ✓ Good — v1.0 |
| Centralize placeholder cleanup | 3 classifiers independently implement same regex | ✓ Good — v1.0 |
| Both --verbose and JSON signals for explainability | Covers CLI human use + programmatic use cases | ✓ Good — v1.0 |
| Peek archive manifest (not extract) | Extraction is slow, risky, and unnecessary — filenames inside give strong signal | — Pending |
| Extension catch-all routing for media/exotic types | Content unreadable; extension is definitive for these types | — Pending |

---
*Last updated: 2026-03-01 after milestone v1.1 initialization*
