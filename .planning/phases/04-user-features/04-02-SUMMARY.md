---
phase: 04-user-features
plan: 02
subsystem: cli
tags: [typer, signals, verbose, dry-run, json-output, classify, scan, move]

# Dependency graph
requires:
  - phase: 04-user-features-01
    provides: SignalResult type on ClassificationResult, pipeline runs all classifiers

provides:
  - classify --dry-run flag suppressing OCR rename side effects with "dry run" label in output
  - --verbose signal breakdown on classify/scan/move showing per-classifier name + score
  - JSON signals array on classify/scan/move --json output

affects: [04-user-features]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - verbose/dry_run keyword-only params threaded through helper functions
    - signal breakdown displayed as [matched]/[      ] rows after main classification line
    - signals array in JSON with source/name/score/matched fields

key-files:
  created: []
  modified:
    - src/para_files/cli/shared.py
    - src/para_files/cli/classify_cmd.py
    - src/para_files/cli/scan_cmd.py
    - src/para_files/cli/move_cmd.py

key-decisions:
  - "Reduce scan() cyclomatic complexity by extracting _scan_files_parallel helper (C901 compliance)"
  - "dry_run in classify suppresses only OCR rename side effects; classify never moves files"
  - "signals array placed before route_name in JSON for logical ordering (signals before route detail)"

patterns-established:
  - "verbose=False, dry_run=False as keyword-only defaults in all print/helper functions"
  - "Signal row format: marker = '[matched]' if s.matched else '[      ]'; indent 6 spaces"

requirements-completed: [FEAT-01, FEAT-02, FEAT-03]

# Metrics
duration: 7min
completed: 2026-02-28
---

# Phase 4 Plan 02: User Features — Dry Run, Verbose Signals, JSON Signals Summary

**classify --dry-run previews classification without OCR rename; --verbose shows per-classifier signal rows on classify/scan/move; JSON --json output includes signals array with source/name/score/matched fields**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-28T21:15:48Z
- **Completed:** 2026-02-28T21:22:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `classify --dry-run/-n` suppresses OCR rename side effects and labels target line "dry run — no files moved"
- `--verbose` on classify/scan/move shows a per-classifier signal breakdown (e.g., "[matched] rules_engine: 95%")
- `--json` output on classify, scan, and move now includes a `signals` array with `source`, `name`, `score`, `matched` fields
- Extracted `_scan_files_parallel` helper from inline code in `scan()` to reduce cyclomatic complexity

## Task Commits

Each task was committed atomically:

1. **Task 1: classify --dry-run and verbose signals in shared.py + classify_cmd.py** - `97cc47d` (feat)
2. **Task 2: verbose signals in scan/move and JSON signals output** - `601211b` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `src/para_files/cli/shared.py` - `print_classification_result` gains `verbose`/`dry_run` params; `format_result_json` includes signals array
- `src/para_files/cli/classify_cmd.py` - `--dry-run/-n` option added; `verbose`/`dry_run` threaded through sequential and parallel helpers
- `src/para_files/cli/scan_cmd.py` - `_classify_file_for_scan` shows signals when verbose; JSON output includes signals; `_scan_files_parallel` extracted
- `src/para_files/cli/move_cmd.py` - `_print_move_result` shows signals when verbose; `_format_move_result_json` includes signals; `verbose` threaded through `_handle_move_file`

## Decisions Made

- Extracted `_scan_files_parallel` from inline code inside `scan()` to satisfy ruff C901 cyclomatic complexity limit (12 > 10)
- classify never moves files; `--dry-run` only suppresses OCR rename side effects; documented in code comment
- Signals array positioned before `route_name` in JSON dict for logical ordering

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Extracted _scan_files_parallel to fix cyclomatic complexity**
- **Found during:** Task 2 (scan_cmd.py changes)
- **Issue:** Adding verbose signal display to inline parallel loop in `scan()` pushed cyclomatic complexity to 12 (limit 10), causing ruff C901 error
- **Fix:** Extracted parallel scan loop into `_scan_files_parallel(files, pipeline, stats, max_workers, *, output_json, verbose)` helper
- **Files modified:** src/para_files/cli/scan_cmd.py
- **Verification:** `ruff check` passes, all tests pass
- **Committed in:** 601211b (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — blocking linting error)
**Impact on plan:** Necessary refactor to satisfy project ruff rules. Net positive — cleaner code structure.

## Issues Encountered

None — all quality checks passed cleanly after deviation fix.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 3 user features (FEAT-01, FEAT-02, FEAT-03) delivered and passing quality checks
- Phase 4 is now complete — both plans executed
- Classification pipeline now exposes full transparency to users via CLI and JSON

## Self-Check: PASSED

- FOUND: 04-02-SUMMARY.md
- FOUND: shared.py
- FOUND: classify_cmd.py
- FOUND: scan_cmd.py
- FOUND: move_cmd.py
- Commits 97cc47d and 601211b verified in git log

---
*Phase: 04-user-features*
*Completed: 2026-02-28*
