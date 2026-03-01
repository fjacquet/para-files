---
phase: 07-inbox-processing-ux
plan: 01
subsystem: cli
tags: [inbox, cli, ux, classification, batch-processing]
dependency_graph:
  requires:
    - pipeline.classify_file
    - mover.move_classified_file
    - cli.shared (discover_files, validate_directory_or_exit, load_config_or_exit, setup_logging)
    - types.ClassificationSource.DEFAULT
  provides:
    - inbox CLI command (one-shot inbox drain)
    - _InboxStats dataclass
    - _process_inbox_file helper
    - _print_inbox_summary helper
  affects:
    - main.py (new import)
    - cli/__init__.py (new import + __all__ entry)
tech_stack:
  added: []
  patterns:
    - dataclass for stats accumulation
    - ClassificationSource.DEFAULT check for skip decision
    - non-recursive discover_files (inbox root only)
    - [idx/total] progress prefix pattern
key_files:
  created:
    - src/para_files/cli/inbox_cmd.py
  modified:
    - src/para_files/main.py
    - src/para_files/cli/__init__.py
decisions:
  - Use _InboxStats dataclass (not dict) for clarity and type safety
  - Check ClassificationSource.DEFAULT to determine stay-in-inbox vs move
  - Non-recursive discover (inbox root only — subdirs are intentional PARA structure)
  - print [idx/total] prefix unconditionally for all files (moved and stayed)
  - INBOX label in progress line for unclassified files (distinguishes from moved)
  - by_signal sorted by count descending (most active signals first)
metrics:
  duration: 3 minutes
  completed: 2026-03-01
  tasks_completed: 2
  files_changed: 3
---

# Phase 7 Plan 01: Inbox CLI Command Summary

**One-liner:** One-shot `inbox` CLI command with [idx/total] progress display and post-run summary, skipping DEFAULT-classified files and tallying by-signal breakdown.

## What Was Built

The `inbox` command processes an entire inbox directory in one command. It:
- Iterates all files in the inbox root (non-recursive)
- Classifies each file via the pipeline
- Moves confidently-classified files to their PARA destination
- Leaves files whose source is `ClassificationSource.DEFAULT` in place (reported as INBOX)
- Prints `[idx/total]` progress for every file during processing
- Prints a summary table (total, moved, stayed, failed, by-signal breakdown)

## Key Implementation Decisions

| Decision | Rationale |
|----------|-----------|
| `_InboxStats` dataclass | Typed, mutable container avoids dict with magic keys |
| `ClassificationSource.DEFAULT` check | Definitive signal that pipeline found no confident match |
| Non-recursive `discover_files` | Inbox root only; subdirectories are intentional PARA structure |
| INBOX label in progress line | Clearly distinguishes unclassified from moved at a glance |
| by_signal sorted desc | Most-active classifiers appear first in summary |

## Files Modified

| File | Change |
|------|--------|
| `src/para_files/cli/inbox_cmd.py` | Created — full inbox command implementation |
| `src/para_files/main.py` | Added `inbox_cmd` import for side-effect registration |
| `src/para_files/cli/__init__.py` | Added `inbox_cmd` import and `__all__` entry |

## Verification Results

- `ruff check src/ tests/` — all checks passed
- `ruff format src/ tests/` — 1 file reformatted (inbox_cmd.py formatting pass)
- `mypy src/` — success, no issues in 64 source files
- `uv run para-files inbox --help` — shows command with `--dry-run`, `--reference-tree`, `--conflict`, `--verbose`
- Smoke test: `uv run para-files inbox <tmp_dir> --dry-run` — prints progress line and summary `Total processed : 1`

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

Files verified:
- src/para_files/cli/inbox_cmd.py: FOUND
- src/para_files/main.py: FOUND (contains inbox_cmd)
- src/para_files/cli/__init__.py: FOUND (contains inbox_cmd)

Commits verified:
- 9318bdd: feat(07-01): implement inbox CLI command
- 48552b7: feat(07-01): register inbox_cmd in main.py and cli/__init__.py
