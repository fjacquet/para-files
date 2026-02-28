---
phase: 04-user-features
plan: 01
subsystem: pipeline
tags: [pydantic, classification, signals, types, mypy]

# Dependency graph
requires: []
provides:
  - SignalResult Pydantic model in types.py with source, name, score, matched fields
  - signals: list[SignalResult] field on ClassificationResult (default empty, backward compatible)
  - pipeline.classify() runs all classifiers and populates signals on returned result
affects:
  - 04-02 (JSON output with signals)
  - Any CLI --verbose classifier detail display

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SignalResult captures per-classifier execution telemetry (run-all, record-all, winner=first-match)
    - getattr with isinstance guard for safe source extraction from mock/dynamic classifiers

key-files:
  created: []
  modified:
    - src/para_files/types.py
    - src/para_files/pipeline.py

key-decisions:
  - "Run all classifiers (not first-match-return) so every signal is recorded; winner is still first match"
  - "signals field has default_factory=list for backward compatibility with existing ClassificationResult construction"
  - "Use getattr + isinstance guard to safely extract ClassificationSource from classifier, fallback to DEFAULT for mocks/invalid"

patterns-established:
  - "SignalResult always appended for every classifier regardless of match outcome"
  - "winner.model_copy(update={'signals': signals}) attaches full signal list to winning result"

requirements-completed: [FEAT-03]

# Metrics
duration: 12min
completed: 2026-02-28
---

# Phase 4 Plan 01: Signal Capture Foundation Summary

**SignalResult Pydantic model and pipeline run-all-classifiers refactor enabling per-classifier transparency for FEAT-03**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-28T21:55:00Z
- **Completed:** 2026-02-28T22:07:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `SignalResult` Pydantic model to `types.py` with strict types: `source: ClassificationSource`, `name: str`, `score: float`, `matched: bool`
- Added `signals: list[SignalResult]` field to `ClassificationResult` with `default_factory=list` (backward compatible)
- Refactored `pipeline.classify()` to run every classifier and collect a `SignalResult` per classifier before returning the winner
- All 1246 existing tests pass unchanged (backward compatibility confirmed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add SignalResult model and signals field to ClassificationResult** - `f53a9c6` (feat)
2. **Task 2: Collect all classifier signals in pipeline.classify()** - `1d645ab` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/para_files/types.py` - Added `SignalResult` model before `ClassificationResult`; added `signals` field; updated module docstring
- `src/para_files/pipeline.py` - Imported `SignalResult`; rewrote `classify()` loop to run all classifiers; added safe source extraction with `getattr`/`isinstance`

## Decisions Made

- Run all classifiers instead of returning on first match, so the full signal chain is observable — winner is still the first classifier that returns non-None (first-match semantics preserved)
- `signals` field uses `default_factory=list` so all code that constructs `ClassificationResult(category=..., confidence=...)` continues to work without modification
- Use `getattr(classifier, "source", ClassificationSource.DEFAULT)` + `isinstance` check to safely extract source even from mock classifiers (MagicMock) in tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed SignalResult construction failure when classifier.source is a MagicMock**

- **Found during:** Task 2 (pipeline.classify() refactor)
- **Issue:** Test `test_classifier_exception_handling` and `test_pipeline_skips_failing_classifier_and_continues` use `MagicMock()` for classifiers without setting `.source`. Pydantic `SignalResult` validation rejects a MagicMock as `ClassificationSource` enum.
- **Fix:** Moved `source` extraction before the try/except block using `getattr(classifier, "source", ClassificationSource.DEFAULT)` with `isinstance` guard — applies to all three paths (matched, not matched, exception).
- **Files modified:** `src/para_files/pipeline.py`
- **Verification:** `uv run pytest tests/ -q` → 1246 passed, 3 skipped
- **Committed in:** `1d645ab` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was necessary for correctness — Pydantic validation would raise in tests with mock classifiers. No scope creep.

## Issues Encountered

- Pre-existing ruff TRY003/EM102 errors at `pipeline.py:274` were already documented in STATE.md as deferred and out-of-scope. Not introduced by this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `SignalResult` and `ClassificationResult.signals` are ready for consumption
- Plan 04-02 can emit signals in JSON output and display verbose classifier details in the CLI
- All downstream consumers of `ClassificationResult` continue to work without changes

## Self-Check: PASSED

- FOUND: `src/para_files/types.py` (modified — SignalResult added)
- FOUND: `src/para_files/pipeline.py` (modified — run-all classifiers)
- FOUND: `.planning/phases/04-user-features/04-01-SUMMARY.md`
- FOUND commit: `f53a9c6` (Task 1: types.py)
- FOUND commit: `1d645ab` (Task 2: pipeline.py)
- `grep "class SignalResult"` → line 135 in types.py
- `grep "signals:"` → line 163 in types.py
- `uv run pytest tests/ -q` → 1246 passed, 3 skipped

---
*Phase: 04-user-features*
*Completed: 2026-02-28*
