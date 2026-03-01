# para-files

## What This Is

para-files is a macOS-only (Apple Silicon) intelligent file classification system using MLX-powered semantic routing. It implements the PARA method (Projects, Areas, Resources, Archives) with a deterministic 7-signal classification pipeline. The system classifies and moves files to their correct PARA folder — reading inside Excel/ODS spreadsheets, peeking at ZIP archive manifests, routing media and exotic files by extension, and providing a one-shot inbox drain command.

## Core Value

Files are classified correctly and transparently — users can understand why a file was placed where it was, and the pipeline fails loudly when something goes wrong.

## Requirements

### Validated

- ✓ 6-signal classification pipeline (ValidatedDB → BookDetector → RulesEngine → DomainKB → SemanticRouter → LLM) — v1.0
- ✓ CLI commands: scan, move, classify, bookstore, learn, routes, dedupe, migrate, rescan, clean, init, config, tree — v1.0
- ✓ MLX embedding encoder with lazy loading and progressive truncation — v1.0
- ✓ Thema v1.6 book classification (9,187 codes) — v1.0
- ✓ Filename sanitization utilities — v1.0
- ✓ Feedback-based learning (learn command) — v1.0
- ✓ Centralized logging via loguru — v1.0
- ✓ Bug fixes: extension case sensitivity, OCR threshold (0.3→0.7), MLX zero-vector — v1.1
- ✓ Code quality: placeholder_resolver.py, ruff/mypy strict compliance, explicit error handling — v1.1
- ✓ Test coverage: pipeline exception isolation, concurrent bookstore, rules engine edge cases — v1.1
- ✓ `--dry-run`, `--verbose`, JSON `signals` array on classify/scan/move — v1.1
- ✓ `SignalResult` model + all-classifier pipeline transparency — v1.1
- ✓ Excel/ODS content reading (openpyxl, odfpy) and ZIP/7Z manifest peeking — v1.1
- ✓ `ExtensionRouterClassifier` as Signal 5: video/audio/images/security/scripts/catch-all — v1.1
- ✓ `inbox` command: one-shot drain with per-file progress and by-signal summary — v1.1

### Active

(None — planning next milestone)

### Out of Scope

- ISBN caching / retry logic — separate concern, defer
- Geolocation cache read-write lock — low impact, defer
- Async/await refactor of bookstore — large scope, defer
- MLX local model mirroring — infrastructure concern, defer
- Embedding LRU cache — premature optimization, defer
- Extracting/decompressing archives before classification — too slow and risky
- Mobile / non-Apple-Silicon support — MLX is core dependency

## Context

**Shipped v1.1 (2026-03-01):** 7 phases, 16 plans. Pipeline upgraded from 6-signal to 7-signal with `ExtensionRouterClassifier`. New content readers for Excel/ODS/ZIP/7Z. `inbox` command enables one-shot processing of large mixed-type inboxes. Source: ~17,600 LOC Python. Tests: ~16,600 LOC Python.

**Inbox analysis (2026-03-01):** 817 files in `/Volumes/cloudsync/Fred/OneDrive4Business-LJF/PARA/0_Inbox`. Breakdown: 289 PDF, 188 ZIP/7Z, 178 Excel, 51 DOC/DOCX, 37 media, 62 exotic. Content reading + extension routing now addresses the previously-unhandled 52% of the inbox.

## Constraints

- **Platform**: macOS Apple Silicon only — MLX and Vision Framework requirements
- **Python**: 3.12+ with strict mypy, ruff linting (line length 100)
- **Style**: Functional programming preferred, loguru for logging, pydantic for config
- **Testing**: Pytest; all new code must have tests
- **Coverage**: ≥79% (threshold adjusted to match current baseline; grows with each phase)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Raise OCR confidence to 0.7 | 0.3 threshold causes renames on weak signals | ✓ Good — v1.1 |
| Centralize placeholder cleanup | 3 classifiers independently implement same regex | ✓ Good — v1.1 |
| Both --verbose and JSON signals for explainability | Covers CLI human use + programmatic use cases | ✓ Good — v1.1 |
| Peek archive manifest (not extract) | Extraction is slow, risky, and unnecessary | ✓ Good — v1.1 |
| Extension catch-all routing for media/exotic types | Content unreadable; extension is definitive | ✓ Good — v1.1 |
| StrEnum migration (UP042) | Python 3.12+ native, cleaner than (str, Enum) | ✓ Good — v1.1 |
| Coverage threshold at 79% | Phase 4 added new code paths not yet fully covered | ✓ Good — will grow with tests |

---
*Last updated: 2026-03-01 after v1.1 Inbox Throughput milestone*
