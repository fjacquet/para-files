# para-files — Technical Debt & Quality Cleanup

## What This Is

para-files is a macOS-only (Apple Silicon) intelligent file classification system using MLX-powered semantic routing. It implements the PARA method with a deterministic 6-signal classification pipeline. This milestone focuses on cleaning known concerns: fixing bugs, improving code quality, expanding test coverage, and adding missing user-facing features.

## Core Value

Files are classified correctly and transparently — users can understand why a file was placed where it was, and the pipeline fails loudly when something goes wrong.

## Requirements

### Validated

- ✓ 6-signal classification pipeline (ValidatedDB → BookDetector → RulesEngine → DomainKB → SemanticRouter → LLM) — existing
- ✓ CLI commands: scan, move, classify, bookstore, learn, routes, dedupe, migrate, rescan, clean, init, config, tree — existing
- ✓ Typer-based CLI with --dry-run on move command — existing
- ✓ MLX embedding encoder with lazy loading — existing
- ✓ Thema v1.6 book classification (9,187 codes) — existing
- ✓ Filename sanitization utilities — existing
- ✓ Feedback-based learning (learn command) — existing
- ✓ Centralized logging via loguru — existing

### Active

- [ ] Fix file extension case sensitivity (uppercase .PDF, .EPUB, .CHM not detected)
- [ ] Raise OCR rename confidence threshold from 0.3 to 0.7 (prevent bad renames)
- [ ] Fix MLX encoder zero-vector fallback for high-density text (adaptive truncation)
- [ ] Replace 20+ bare `except Exception` blocks with typed handlers + improved logging
- [ ] Centralize placeholder cleanup logic (`{year}`, `{issuer}`, `{location}`) into shared utility
- [ ] Add test coverage for pipeline exception handling when classifiers fail
- [ ] Add test coverage for concurrent bookstore processing conflicts
- [ ] Add test coverage for rules engine edge cases (overlapping patterns, special chars)
- [ ] Add `--dry-run` to `classify` command (preview without moving)
- [ ] Add confidence explainability: `--verbose` shows which classifier matched + score
- [ ] Add `signals` array to JSON output with per-classifier results

### Out of Scope

- ISBN caching / retry logic — separate concern, defer
- Geolocation cache read-write lock — low impact, defer
- Async/await refactor of bookstore — large scope, defer
- MLX local model mirroring — infrastructure concern, defer
- Embedding LRU cache — premature optimization, defer

## Context

Codebase map produced 2026-02-28. Key fragile areas: book_detector.py exclusion heuristics, taxonomy_classifier.py placeholder resolution, rules_engine.py glob interaction. All subprocess calls already use list args (no shell=True). SQLite thread safety is handled via RLock; `check_same_thread=False` is intentional and documented.

## Constraints

- **Platform**: macOS Apple Silicon only — MLX and Vision Framework requirements
- **Python**: 3.12+ with strict mypy, ruff linting (line length 100)
- **Style**: Functional programming preferred, loguru for logging, pydantic for config
- **Testing**: Pytest; all new code must have tests; no new `# noqa: BLE001` without specific exception type

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Raise OCR confidence to 0.7 | 0.3 threshold causes renames on weak signals (e.g. "Annual Report" in bank statement header) | — Pending |
| Centralize placeholder cleanup | 3 classifiers independently implement same regex — maintenance burden and inconsistency risk | — Pending |
| Both --verbose and JSON signals for explainability | Covers CLI human use + programmatic use cases without duplication | — Pending |

---
*Last updated: 2026-02-28 after initialization*
