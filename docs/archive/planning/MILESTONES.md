# Milestones

## v1.2 Reliability & Performance (Shipped: 2026-03-22)

**Phases completed:** 4 phases (8–11), 11 plans
**Source code:** ~21,500 LOC Python | **Test suite:** ~19,200 LOC Python | **Tests:** 1,488 passing
**Git range:** Phase 8 Foundation Hardening → Phase 11 Performance + Pipeline Tests
**Timeline:** 21 days (2026-03-01 → 2026-03-22)

**Key accomplishments:**

1. Eliminated all broad `except Exception` (BLE001) in pipeline, classifiers, and utilities — every exception is now specific and logged
2. Ollama circuit breaker + health check at init: semantic/LLM classifiers auto-disable when server is unreachable, no per-file failures
3. LLM response parsing hardened: JSON-first strategy, confidence coercion, URL-decode, PARA category allowlist — no more garbage classifications
4. Book detector false positives eliminated: French financial documents (IBAN-containing) no longer misclassified as books
5. Batch move safety: permission pre-check before first move, stop-on-first-failure, LIFO rollback of completed moves
6. Adaptive threading: batches < 5 files skip thread pool overhead; hash cache avoids redundant SHA256; centralized content truncation across all classifiers

---

## v1.1 Inbox Throughput (Shipped: 2026-03-01)

**Phases completed:** 7 phases, 16 plans
**Source code:** ~17,600 LOC Python | **Test suite:** ~16,600 LOC Python
**Git range:** Phase 1 Bug Fixes → Phase 7 Inbox UX

**Key accomplishments:**

1. Fixed silent pipeline failures: uppercase extension detection, OCR confidence threshold (0.3→0.7), MLX encoder zero-vector on high-density text
2. Eliminated defensive anti-patterns: replaced all bare `except` blocks, centralized placeholder cleanup into `placeholder_resolver.py`, logged specific ISBN enrichment failures
3. Achieved 80%+ test coverage: pipeline exception isolation, concurrent bookstore conflict resolution, rules engine Unicode/special-character edge cases
4. Shipped classification transparency: `SignalResult` model captures all 6 classifier outputs; `--dry-run`, `--verbose`, and JSON `signals` array added to classify/scan/move
5. Added content-aware classification for Excel/ODS (openpyxl + odfpy) and ZIP/7Z (stdlib + optional py7zr) — filenames and cell values now drive semantic routing
6. Introduced `ExtensionRouterClassifier` as Signal 5: 17 extensions across video/audio/images/security/scripts groups + catch-all for unknowns
7. Shipped `inbox` command: one-shot drain of any directory with `[idx/total] file → dest` progress display and by-signal post-run summary

---
