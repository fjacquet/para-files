# para-files

## What This Is

para-files is an intelligent file classification system using Ollama-powered semantic routing (via litellm). It implements the PARA method (Projects, Areas, Resources, Archives) with a deterministic 6-signal classification pipeline. The system classifies and moves files to their correct PARA folder — reading inside Excel/ODS spreadsheets, peeking at ZIP archive manifests, routing media and exotic files by extension, and providing a one-shot inbox drain command. OCR features require macOS (Apple Silicon).

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
- ✓ Specific exception handling: zero BLE001 in pipeline, classifiers, utilities — v1.2 Phase 8
- ✓ Placeholder resolution: required vs optional policy (reject on missing issuer/technology) — v1.2 Phase 8
- ✓ Subprocess extension validation: pandoc/chm allowlists before execution — v1.2 Phase 8
- ✓ macOS OCR test isolation with platform skip markers — v1.2 Phase 8
- ✓ Ollama circuit breaker + health check at init (disable semantic/LLM when unreachable) — v1.2 Phase 9
- ✓ Encoder connection-error short-circuit (no retry loop when Ollama is down) — v1.2 Phase 9
- ✓ Ctrl+C handling: KeyboardInterrupt caught in classify loop, exits cleanly — v1.2 Phase 9
- ✓ LLM response parsing hardened: JSON-first, confidence coercion, URL-decode, allowlist — v1.2 Phase 9
- ✓ LRU embedding cache (500 entries, SHA256 key on first 2000 chars) — v1.2 Phase 9
- ✓ ISBN error distinction: transient retry vs data error skip — v1.2 Phase 9
- ✓ Book detector false positives on French financial documents eliminated (is_financial_document precedence) — v1.2 Phase 10
- ✓ YAML reference tree validation: Pydantic models, fail-fast on invalid config — v1.2 Phase 10
- ✓ Unclassifiable files routed to 6_unclassified (DEFAULT_UNCLASSIFIED_CATEGORY constant) — v1.2 Phase 10
- ✓ Batch move safety: permission pre-check, stop-on-first-failure, rollback capability — v1.2 Phase 10
- ✓ Adaptive thread pool: SINGLE_THREAD_THRESHOLD=5 skips thread pool for small batches — v1.2 Phase 11
- ✓ Hash cache: mtime+path keyed cache eliminates redundant SHA256 computation — v1.2 Phase 11
- ✓ Centralized content truncation: all classifiers use DEFAULT_CONTENT_PREVIEW_CHARS from config — v1.2 Phase 11
- ✓ Pipeline order/failure tests: classifier ordering, first-match-wins, exception isolation verified — v1.2 Phase 11
- ✓ Concurrent move tests: thread crash isolation, 10-file load, sequential/parallel parity — v1.2 Phase 11

### Active

## Current Milestone: v1.2 Reliability & Performance

**Goal:** Make the classification pipeline trustworthy — fix silent failures, add timeouts and circuit breakers, harden error handling, and improve throughput.

**Target features:**

- LLM classifier timeout + graceful Ctrl+C handling
- Ollama circuit breaker (skip after repeated failures)
- Replace broad `except Exception` (BLE001) with specific exception types
- Fix silent placeholder resolution failures
- Embedding caching to avoid redundant Ollama calls
- Reduce book detector false positives on financial documents
- Batch rollback for move operations
- Adaptive thread pool sizing

### Out of Scope

- ISBN caching / retry logic — separate concern, defer
- Geolocation cache read-write lock — low impact, defer
- Async/await refactor of bookstore — large scope, defer
- MLX local model mirroring — infrastructure concern, defer
- Embedding LRU cache — promoted to v1.2 active scope
- Extracting/decompressing archives before classification — too slow and risky
- Mobile support — desktop CLI tool
- Full cross-platform support — OCR remains macOS-only

## Context

**v1.2 Phase 11 complete (2026-03-22):** Performance + Pipeline Tests. Adaptive threading skips thread pool for batches < 5 files. Hash cache (path+mtime key) avoids redundant SHA256 calls. All classifiers now use `DEFAULT_CONTENT_PREVIEW_CHARS` — no hidden truncation constants. Pipeline ordering and concurrent threading fully tested. 1488 tests passing. v1.2 milestone complete.

**v1.2 Phase 10 complete (2026-03-22):** Classification Accuracy + Move Safety. Book detector no longer misclassifies French financial documents (is_financial_document takes precedence). YAML reference tree validates with Pydantic at load time — fails fast on malformed config. Unclassifiable files route to 6_unclassified. BatchMover adds permission pre-check, stop-on-first-failure, and rollback. 1472 tests passing.

**v1.2 Phase 9 complete (2026-03-22):** LLM + Service Reliability. Circuit breaker, health check at init, encoder short-circuit on connection errors, clean Ctrl+C, LLM response hardening (JSON-first, confidence coercion, URL-decode, allowlist), LRU embedding cache, ISBN error distinction. 1435 tests passing.

**Shipped v1.1 (2026-03-01):** 7 phases, 16 plans. Pipeline upgraded from 6-signal to 7-signal with `ExtensionRouterClassifier`. New content readers for Excel/ODS/ZIP/7Z. `inbox` command enables one-shot processing of large mixed-type inboxes. Source: ~17,600 LOC Python. Tests: ~16,600 LOC Python.

**Inbox analysis (2026-03-01):** 817 files in `/Volumes/cloudsync/Fred/OneDrive4Business-LJF/PARA/0_Inbox`. Breakdown: 289 PDF, 188 ZIP/7Z, 178 Excel, 51 DOC/DOCX, 37 media, 62 exotic. Content reading + extension routing now addresses the previously-unhandled 52% of the inbox.

## Constraints

- **Platform**: macOS for OCR (Apple Silicon Vision Framework); core pipeline is cross-platform (Ollama)
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

| Pipeline short-circuit (break on first match) | Running all 6 classifiers even after match wastes 30-55s on Ollama | — Pending |
| LLM timeout 15s + graceful Ctrl+C | ministral-3:8b takes 30-55s and often returns 0_Inbox | — Pending |
| Migrate from MLX to litellm/Ollama | Cross-platform, unified API, no Apple Silicon requirement | ✓ Good — v1.2 prep |

---
*Last updated: 2026-03-22 after Phase 11 Performance + Pipeline Tests complete — v1.2 milestone complete*
