---
phase: 11-performance-pipeline-tests
plan: "02"
subsystem: tests
tags: [testing, pipeline, concurrency, tdd, TEST-01, TEST-03]
dependency_graph:
  requires: []
  provides: [TEST-01, TEST-03]
  affects: [tests/test_pipeline_order.py, tests/test_concurrent_move.py]
tech_stack:
  added: []
  patterns:
    - ClassificationPipeline.__new__() injection bypasses __init__ for unit tests
    - MagicMock with side_effect for crash simulation in concurrent tests
    - dry_run=True for filesystem-safe concurrent move verification
key_files:
  created:
    - tests/test_pipeline_order.py
    - tests/test_concurrent_move.py
  modified: []
decisions:
  - Pipeline tests use __new__() injection with _initialized=True to bypass classifier init
  - Concurrent tests verify via success+skip+fail counts (not results list) since output_json=False
  - get_target_path mocked to return real Path so FileMover can compute destinations in dry-run
metrics:
  duration: 5m
  completed_date: "2026-03-22"
  tasks_completed: 2
  files_changed: 2
---

# Phase 11 Plan 02: Pipeline Order and Concurrent Move Tests Summary

**One-liner:** Pipeline classifier ordering and thread-safe concurrent move verified via injection-based unit tests and real-filesystem load tests.

## What Was Built

Two test suites locking the pipeline ordering contract and concurrent move thread-safety:

- `tests/test_pipeline_order.py` (TEST-01): 4 tests using `ClassificationPipeline.__new__()` injection to verify classifier execution order, first-match-wins behaviour, disabled-classifier passthrough, and single-exception recovery.
- `tests/test_concurrent_move.py` (TEST-03): 3 tests using real `tmp_path` files to verify one crashing worker does not lose other workers' results, 10-file load produces zero silent losses, and sequential vs parallel execution cover the same file set.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Pipeline order and failure isolation tests | 32e7110 | Done |
| 2 | Concurrent move threading tests + lint fixes | 606d5a5 | Done |

## Verification Results

- `uv run pytest tests/test_pipeline_order.py -v` — 4 passed
- `uv run pytest tests/test_concurrent_move.py -v` — 3 passed
- `uv run pytest tests/ --tb=short` — 1488 passed, 3 skipped (OCR)
- `uv run ruff check tests/test_pipeline_order.py tests/test_concurrent_move.py` — no errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Lint errors in generated test files**
- **Found during:** Task 2 verification
- **Issue:** Unused `pytest` import in `test_pipeline_order.py`; `dict()` calls instead of literals (C408) in `test_concurrent_move.py`; exception string literal not assigned to variable (EM101/TRY003)
- **Fix:** Removed unused import; rewrote module-level kwargs as dict literals; assigned error message to variable before raising
- **Files modified:** `tests/test_pipeline_order.py`, `tests/test_concurrent_move.py`
- **Commit:** 606d5a5

## Self-Check: PASSED

All files exist, both commits verified.

**2. [Rule 2 - Missing functionality] Plan's return type spec was inaccurate**
- **Found during:** Task 2 implementation
- **Issue:** Plan's interfaces block described `_move_files_parallel` returning `tuple[list[MoveResult], set[Path], int, int, int]` but the actual return is `tuple[list[dict], set[Path], int, int, int]` (dicts, not MoveResult objects). Sequential also returns `list[dict]`, not `list[MoveResult]`.
- **Fix:** Tests use actual dict-based return structure and verify via count sums (success+skip+fail) rather than inspecting result objects
- **Files modified:** `tests/test_concurrent_move.py`
- **Commit:** 606d5a5
