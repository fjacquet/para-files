# Milestones

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
