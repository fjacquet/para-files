---
phase: 11-performance-pipeline-tests
plan: 01
subsystem: performance
tags: [threading, caching, content-truncation, hashlib, move-cmd, mover, semantic-classifier]

requires:
  - phase: 10-classification-accuracy-move-safety
    provides: BatchMover rollback and CLI permission pre-check

provides:
  - SINGLE_THREAD_THRESHOLD = 5 constant in move_cmd.py enforcing sequential mode for small batches
  - _hash_cache module-level dict in mover.py keyed by (path, mtime) for zero-cost repeat hashing
  - DEFAULT_CONTENT_PREVIEW_CHARS centralized in semantic_classifier.py, book_detector.py, rules_engine.py

affects: [pipeline, mover, classifiers, move-cmd]

tech-stack:
  added: []
  patterns:
    - "Adaptive single-threading: skip thread pool for batches < SINGLE_THREAD_THRESHOLD (5)"
    - "Process-lifetime hash cache keyed by (str(path), mtime_float) — mtime change auto-invalidates"
    - "Centralized content truncation: DEFAULT_CONTENT_PREVIEW_CHARS imported from config, not hardcoded"

key-files:
  created:
    - tests/test_single_thread_threshold.py
  modified:
    - src/para_files/cli/move_cmd.py
    - src/para_files/mover.py
    - src/para_files/classifiers/semantic_classifier.py
    - src/para_files/classifiers/book_detector.py
    - src/para_files/classifiers/rules_engine.py
    - tests/test_mover.py

key-decisions:
  - "SINGLE_THREAD_THRESHOLD = 5 exclusive (< 5 forces sequential, >= 5 allows parallel)"
  - "Hash cache uses plain dict keyed by (str(path), mtime_float) — no lru_cache due to tuple key"
  - "book_detector.py and rules_engine.py also updated to use DEFAULT_CONTENT_PREVIEW_CHARS for [:2000] content slices"
  - "content[:500] (year regex) and content[:1000] (tech extraction) left unchanged — deliberately narrower windows"

patterns-established:
  - "Adaptive threading: SINGLE_THREAD_THRESHOLD guards thread pool dispatch in move_cmd"
  - "Mtime-keyed hash cache: cheap process-lifetime caching without external dependencies"
  - "Single source of truth for content length: DEFAULT_CONTENT_PREVIEW_CHARS from config.py"

requirements-completed: [PERF-01, PERF-02, PERF-03]

duration: 7min
completed: 2026-03-22
---

# Phase 11 Plan 01: Performance Pipeline Tests Summary

**Adaptive single-threading (< 5 files), process-lifetime hash cache keyed by path+mtime, and centralized DEFAULT_CONTENT_PREVIEW_CHARS across all classifiers**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-22T18:59:01Z
- **Completed:** 2026-03-22T19:06:54Z
- **Tasks:** 3
- **Files modified:** 6 (plus 2 test files)

## Accomplishments

- Added `SINGLE_THREAD_THRESHOLD = 5` constant in move_cmd.py; batches < 5 files skip thread pool overhead entirely, with `--verbose` logging
- Added `_hash_cache: dict[tuple[str, float], str]` at module level in mover.py; `_compute_file_hash` checks cache before running hashlib.sha256()
- Removed `MAX_CONTENT_LENGTH = 2000` local constant from semantic_classifier.py and replaced with `DEFAULT_CONTENT_PREVIEW_CHARS` imported from config; also centralized the `[:2000]` content slices in book_detector.py and rules_engine.py

## Task Commits

1. **Task 1: PERF-01 — Adaptive single-threading threshold in move_cmd.py** - `9b3a447` (feat)
2. **Task 2: PERF-02 — Hash cache in mover.py (path + mtime key)** - `9a3d133` (feat)
3. **Task 3: PERF-03 — Centralize content truncation in semantic_classifier.py** - `8b72ee0` (feat)

## Files Created/Modified

- `src/para_files/cli/move_cmd.py` - Added SINGLE_THREAD_THRESHOLD = 5, updated dispatch gate, added verbose log
- `src/para_files/mover.py` - Added _hash_cache dict, updated _compute_file_hash with cache check/insert
- `src/para_files/classifiers/semantic_classifier.py` - Removed MAX_CONTENT_LENGTH, imported DEFAULT_CONTENT_PREVIEW_CHARS
- `src/para_files/classifiers/book_detector.py` - Imported and used DEFAULT_CONTENT_PREVIEW_CHARS for thema lookup truncation
- `src/para_files/classifiers/rules_engine.py` - Imported and used DEFAULT_CONTENT_PREVIEW_CHARS for header content slice
- `tests/test_single_thread_threshold.py` - New: 5 tests for SINGLE_THREAD_THRESHOLD constant and logic
- `tests/test_mover.py` - Added 4 cache tests: existence, hit, mtime invalidation, files_are_identical integration

## Decisions Made

- SINGLE_THREAD_THRESHOLD is EXCLUSIVE (< 5 forces sequential, exactly 5 uses parallel) — matches ROADMAP success criterion "fewer than 5 files"
- Hash cache uses plain dict instead of functools.lru_cache because the composite (path, mtime) tuple key is cleaner with explicit dict management
- book_detector.py `[:2000]` (thema lookup) and rules_engine.py `[:2000]` (header year search) both centralized — same value as DEFAULT_CONTENT_PREVIEW_CHARS
- content[:500] (year regex narrow search) and content[:1000] (tech extraction) left unchanged — these are purposefully narrower windows for specific pattern matching, not general content truncation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Extended PERF-03 to cover book_detector.py and rules_engine.py**

- **Found during:** Task 3 (audit grep after semantic_classifier change)
- **Issue:** Audit grep revealed `content[:2000]` slices in book_detector.py and rules_engine.py — same pattern as the semantic_classifier local constant
- **Fix:** Imported DEFAULT_CONTENT_PREVIEW_CHARS in both files and replaced the `[:2000]` hardcoded slices
- **Files modified:** src/para_files/classifiers/book_detector.py, src/para_files/classifiers/rules_engine.py
- **Verification:** All 1488 tests pass, ruff and mypy clean
- **Committed in:** 8b72ee0 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical coverage)
**Impact on plan:** Audit-driven extension of PERF-03 to two additional classifiers. No scope creep — exactly what the plan's audit step called for.

## Issues Encountered

- Ruff import sort error on semantic_classifier.py after initial edit — fixed by reordering `from para_files.config import DEFAULT_CONTENT_PREVIEW_CHARS` before other para_files imports alphabetically.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Three performance improvements are in place and tested
- Ready for plan 11-02 (pipeline tests or remaining performance work)
- All 1488 tests pass, no regressions

---
*Phase: 11-performance-pipeline-tests*
*Completed: 2026-03-22*
