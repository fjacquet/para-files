# para-files

## What This Is

para-files is an intelligent file classification system using Ollama-powered semantic routing (via litellm). It implements the PARA method (Projects, Areas, Resources, Archives) with a deterministic 6-signal classification pipeline. The system classifies and moves files to their correct PARA folder with circuit-breaker-protected Ollama calls, batch move rollback, and adaptive threading. OCR features require macOS (Apple Silicon).

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
- ✓ Bug fixes: extension case sensitivity, OCR confidence threshold (0.3→0.7), MLX zero-vector — v1.1
- ✓ Code quality: placeholder_resolver.py, ruff/mypy strict compliance, explicit error handling — v1.1
- ✓ Test coverage: pipeline exception isolation, concurrent bookstore, rules engine edge cases — v1.1
- ✓ `--dry-run`, `--verbose`, JSON `signals` array on classify/scan/move — v1.1
- ✓ `SignalResult` model + all-classifier pipeline transparency — v1.1
- ✓ Excel/ODS content reading (openpyxl, odfpy) and ZIP/7Z manifest peeking — v1.1
- ✓ `ExtensionRouterClassifier` as Signal 5: video/audio/images/security/scripts/catch-all — v1.1
- ✓ `inbox` command: one-shot drain with per-file progress and by-signal summary — v1.1
- ✓ Specific exception handling: zero BLE001 in pipeline, classifiers, utilities — v1.2
- ✓ Placeholder resolution: required vs optional policy (reject on missing issuer/technology) — v1.2
- ✓ Subprocess extension validation: pandoc/chm allowlists before execution — v1.2
- ✓ macOS OCR test isolation with platform skip markers — v1.2
- ✓ Ollama circuit breaker + health check at init (disable semantic/LLM when unreachable) — v1.2
- ✓ Encoder connection-error short-circuit (no retry loop when Ollama is down) — v1.2
- ✓ Ctrl+C handling: KeyboardInterrupt caught in classify loop, exits cleanly — v1.2
- ✓ LLM response parsing hardened: JSON-first, confidence coercion, URL-decode, allowlist — v1.2
- ✓ LRU embedding cache (500 entries, SHA256 key on first 2000 chars) — v1.2
- ✓ ISBN error distinction: transient retry vs data error skip — v1.2
- ✓ Book detector false positives on French financial documents eliminated — v1.2
- ✓ YAML reference tree validation: Pydantic models, fail-fast on invalid config — v1.2
- ✓ Unclassifiable files routed to 6_unclassified — v1.2
- ✓ Batch move safety: permission pre-check, stop-on-first-failure, rollback — v1.2
- ✓ Adaptive thread pool: skip threading for < 5 files — v1.2
- ✓ Hash cache: mtime+path keyed cache eliminates redundant SHA256 — v1.2
- ✓ Centralized content truncation: all classifiers use DEFAULT_CONTENT_PREVIEW_CHARS — v1.2
- ✓ Pipeline order/failure tests: classifier ordering, first-match-wins, exception isolation — v1.2
- ✓ Concurrent move tests: thread crash isolation, 10-file load, sequential/parallel parity — v1.2

### Active

(Next milestone — to be defined via `/gsd:new-milestone`)

### Out of Scope

- Incremental learning from corrections — large scope, requires pipeline architecture changes
- Category aliases/synonyms — requires reference tree redesign
- YAML tree lazy-loading — current tree size manageable
- Async/await refactor — current threading model sufficient
- Extracting/decompressing archives before classification — too slow and risky
- Mobile support — desktop CLI tool
- Full cross-platform support — OCR remains macOS-only

## Context

**Shipped v1.2 (2026-03-22):** 4 phases, 11 plans. Pipeline is now resilient to Ollama failures (circuit breaker, health check, timeout), handles errors explicitly (zero BLE001), and adapts performance to workload size. Book detector accuracy improved, batch moves have rollback safety. 1,488 tests passing. Source: ~21,500 LOC Python. Tests: ~19,200 LOC Python.

**Shipped v1.1 (2026-03-01):** 7 phases, 16 plans. Pipeline upgraded to 7-signal with ExtensionRouterClassifier. Content readers for Excel/ODS/ZIP/7Z. `inbox` command for one-shot processing.

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
| Coverage threshold at 79% | Phase 4 added new code paths not yet fully covered | ✓ Good — grows with phases |
| Pipeline short-circuit (break on first match) | Running all 6 classifiers wastes Ollama calls | ✓ Good — v1.2 |
| LLM timeout 15s + graceful Ctrl+C | ministral-3:8b can take 30-55s, often returns 0_Inbox | ✓ Good — v1.2 |
| Migrate from MLX to litellm/Ollama | Cross-platform, unified API, no Apple Silicon requirement | ✓ Good — v1.2 |
| Circuit breaker (not retry backoff) | Fail-fast for batch processing, avoid hammering down server | ✓ Good — v1.2 |
| Required vs optional placeholders | Silent stripping of {issuer} produces bad paths | ✓ Good — v1.2 |
| 6_unclassified vs 0_Inbox for no-match | Distinct semantics: user triage vs pipeline failure | ✓ Good — v1.2 |
| BatchMover LIFO rollback | Undo completed moves on batch failure | ✓ Good — v1.2 |

---
*Last updated: 2026-03-22 after v1.2 milestone — Reliability & Performance shipped*
