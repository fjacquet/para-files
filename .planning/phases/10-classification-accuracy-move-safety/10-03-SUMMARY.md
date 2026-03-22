---
phase: 10-classification-accuracy-move-safety
plan: "03"
subsystem: mover + cli
tags: [move-safety, rollback, permissions, batch-move, tdd]
dependency_graph:
  requires: []
  provides:
    - BatchMover class with stop-on-failure and LIFO rollback
    - validate_destination_permissions pre-flight function
    - CLI --rollback/--no-rollback flag
    - Sequential move pre-flight permission check
  affects:
    - src/para_files/mover.py
    - src/para_files/cli/move_cmd.py
tech_stack:
  added: []
  patterns:
    - os.access(path, os.W_OK) for permission probing
    - LIFO rollback via reversed(completed_moves)
    - shutil.move for atomic rollback operations
    - Typer Exit(code=1) for permission rejection
key_files:
  created: []
  modified:
    - src/para_files/mover.py
    - src/para_files/cli/move_cmd.py
    - tests/test_mover.py
decisions:
  - BatchMoveResult uses Pydantic BaseModel with arbitrary_types_allowed for Path tuples
  - BatchMover tracks completed_moves only for actual (non-dry-run, non-skipped) moves
  - Rollback failure on individual files logged as warning, not hard error
  - CLI sequential path uses _check_destination_permissions() helper to keep move() complexity within limits
  - Extracted _move_files_sequential() helper to reduce move() branch count below C901/PLR0912 thresholds
  - BatchMover import removed from CLI (future adoption path) - validate_destination_permissions is the immediate integration
metrics:
  duration_seconds: 689
  completed_date: "2026-03-22"
  tasks_completed: 2
  tasks_total: 2
  files_created: 0
  files_modified: 3
requirements: [MOV-01, MOV-02]
---

# Phase 10 Plan 03: Batch Move Safety (Rollback + Permission Pre-check) Summary

BatchMover class with stop-on-failure, LIFO rollback tracking via `(source, destination)` tuples, and `os.access(W_OK)` destination permission pre-flight integrated into the CLI move command with a `--rollback/--no-rollback` flag.

## What Was Built

### Task 1: BatchMover with rollback tracking and permission pre-check (TDD)

**`validate_destination_permissions(destinations: set[Path]) -> list[Path]`** added to `mover.py`:
- Walks up to nearest existing parent for non-existent destination paths
- Uses `os.access(check_path, os.W_OK)` for each unique destination directory
- Returns list of unwritable paths (empty = all OK)

**`BatchMoveResult(BaseModel)`** added to `mover.py`:
- Fields: `results`, `completed_moves`, `total`, `succeeded`, `failed_at`, `failure_message`
- `completed_moves` is `list[tuple[Path, Path]]` for `(source, destination)` pairs

**`BatchMover`** class added to `mover.py`:
- `move_batch(items)`: iterates `(source, dest_dir, classification)` triples, stops on first `success=False`, returns `BatchMoveResult`
- Only tracks moves with actual actions (not `skipped`, `would be moved`, `would be copied`)
- `rollback()`: reverses `_completed_moves` in LIFO order using `shutil.move`, logs warnings for failures, clears list after completion
- Dry-run rollback returns `action="would rollback"` without moving files

### Task 2: CLI integration

**`src/para_files/cli/move_cmd.py`** updated:
- Import `validate_destination_permissions` from mover
- New `--rollback/--no-rollback` flag (default `True`) on `move` command
- Extracted `_check_destination_permissions(expanded_files, pipeline)` helper — classifies all files to find destinations, calls `validate_destination_permissions`, prints clear error
- Extracted `_move_files_sequential(...)` helper — contains the sequential file loop with permission pre-check at the top
- Pre-flight runs only in sequential mode (not parallel), only when `not dry_run and enable_rollback`
- Rejects entire batch with `Exit(code=1)` if any destination is unwritable

## Tests Added

10 new tests across 3 new test classes in `tests/test_mover.py`:

| Class | Tests |
|---|---|
| `TestValidateDestinationPermissions` | writable dir, read-only dir (strip write bits), nonexistent parent, multiple dirs |
| `TestBatchMover` | all succeed, stop on first failure, completed_moves tracking, permission check rejects |
| `TestBatchMoverRollback` | full rollback after partial failure, dry-run rollback |

All 40 tests pass (30 pre-existing + 10 new).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Complexity] Extracted sequential logic to reduce move() complexity**
- **Found during:** Task 2 — ruff C901/PLR0912 (complexity 14 > 10, branches 15 > 12)
- **Issue:** Adding the permission pre-check inline pushed `move()` over complexity limits
- **Fix:** Extracted `_move_files_sequential()` and `_check_destination_permissions()` helpers
- **Files modified:** `src/para_files/cli/move_cmd.py`
- **Commit:** 2cf2e5f

**2. [Rule 2 - Test Safety] Replaced os.chmod literal restore values with Path.chmod() and dynamic mode**
- **Found during:** Task 1 — semgrep CWE-276 warning on hardcoded `0o755` restore values
- **Fix:** Used `path.chmod(original_mode & ~0o222)` to strip write bits and `path.chmod(original_mode)` to restore, avoiding hardcoded permission literals
- **Files modified:** `tests/test_mover.py`

**3. [Rule 1 - Style] Renamed duplicate inner function names**
- **Found during:** Task 1 — three `mock_move` closures in the same test class caused ruff confusion
- **Fix:** Renamed to `mock_move`, `mock_move_tracking`, `mock_move_rollback`
- **Files modified:** `tests/test_mover.py`

## Out-of-Scope Pre-existing Issues (Deferred)

Ruff reported 17 errors in unrelated files during `make quality`:
- `src/para_files/utils/chm_metadata.py` — line length, type issues
- `src/para_files/utils/pandoc.py` — complexity
- `tests/test_ocr.py`, `tests/test_ocr_metadata.py`, `tests/test_pandoc.py`, `tests/test_pipeline.py`, `tests/test_placeholder_resolver.py`, `tests/test_reference_tree.py`

These are pre-existing and out of scope for this plan. Documented in deferred-items.md.

## Self-Check: PASSED

- src/para_files/mover.py: FOUND
- src/para_files/cli/move_cmd.py: FOUND
- tests/test_mover.py: FOUND
- commit 36a8ccf (Task 1): FOUND
- commit 2cf2e5f (Task 2): FOUND
