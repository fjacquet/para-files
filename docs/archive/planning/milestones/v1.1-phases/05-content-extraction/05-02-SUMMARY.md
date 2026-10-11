---
phase: 05-content-extraction
plan: "02"
subsystem: content-extraction
tags: [zipfile, py7zr, archive, manifest, file-utils, classification]

# Dependency graph
requires:
  - phase: 05-01
    provides: Excel and ODS content extraction helpers already in file_utils.py
provides:
  - ARCHIVE_EXTENSIONS constant for .zip/.7z/.7zip dispatch
  - _read_archive_manifest() function using stdlib zipfile and optional py7zr
  - Archive manifest routing in read_content_preview()
  - py7zr optional extra in pyproject.toml (archives extra)
affects: [pipeline, semantic-router, classification-signal]

# Tech tracking
tech-stack:
  added: [py7zr>=0.22.0 (optional archives extra)]
  patterns:
    - Lazy-import optional dependency with graceful ImportError fallback
    - Manifest-only archive reading (no extraction) for safe classification signal
    - Extension dispatch pattern (frozenset constant + early return) in read_content_preview

key-files:
  created: []
  modified:
    - src/para_files/utils/file_utils.py
    - pyproject.toml
    - uv.lock

key-decisions:
  - "Use stdlib zipfile for ZIP (no new dependency) — namelist() only, no extraction"
  - "Use py7zr as optional extra (not hard dependency) — ImportError path returns Filename: fallback"
  - "Manifest format: 'Archive manifest (N files):\\n  file1.pdf\\n  file2.docx' — human readable for semantic routing"
  - "BLE001 noqa on broad except — zipfile raises BadZipFile, RuntimeError (password), NotImplementedError (compression) — all handled uniformly"
  - "Remove type: ignore after py7zr install — py7zr ships its own stubs, no ignore needed"

patterns-established:
  - "Optional dependency pattern: lazy import + ImportError fallback + optional-dependencies extra in pyproject.toml"

requirements-completed:
  - XTRCT-03
  - XTRCT-04

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 05 Plan 02: Archive Manifest Reading Summary

**ZIP and 7Z archive manifest reading via stdlib zipfile and optional py7zr, wired into read_content_preview() so internal filenames drive classification without any file extraction.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T07:27:41Z
- **Completed:** 2026-03-01T07:29:41Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `ARCHIVE_EXTENSIONS` frozenset constant (`{".zip", ".7z", ".7zip"}`) after `EXCEL_EXTENSIONS`
- Added `_read_archive_manifest()` using stdlib `zipfile.ZipFile.namelist()` for ZIP and lazy-import `py7zr.SevenZipFile.getnames()` for 7Z
- Wired archive dispatch into `read_content_preview()` between ODS and pandoc blocks
- Added `py7zr>=0.22.0` as optional `archives` extra in `pyproject.toml`
- Corrupt/encrypted/password-protected archives log a warning and return `"Filename: X"` — no crash

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _read_archive_manifest() and wire into read_content_preview for ZIP and 7Z** - `8e95fc1` (feat)
2. **Task 2: Add py7zr as optional dependency in pyproject.toml** - `5d790dd` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/para_files/utils/file_utils.py` - Added ARCHIVE_EXTENSIONS constant,_read_archive_manifest() function, and dispatch in read_content_preview()
- `pyproject.toml` - Added archives optional-dependencies group with py7zr>=0.22.0
- `uv.lock` - Updated with py7zr and its transitive dependencies

## Decisions Made

- Used stdlib `zipfile` for ZIP — no new dependency needed, only `namelist()` (no extraction)
- Used py7zr as optional extra with graceful `ImportError` fallback returning `"Filename: X"`
- Removed `type: ignore[import-not-found]` after py7zr installation — py7zr ships its own stubs
- Broad `except Exception` with `BLE001` noqa intentional — zipfile raises multiple exception types for corrupt/encrypted/unsupported archives

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adjusted type: ignore comment after py7zr installation**

- **Found during:** Task 2 (py7zr installation)
- **Issue:** Plan specified `# type: ignore[import-untyped]` but mypy saw `import-not-found` before install, then neither error after install (py7zr ships stubs)
- **Fix:** Used `import-not-found` during Task 1, then removed entirely after py7zr was installed in Task 2
- **Files modified:** src/para_files/utils/file_utils.py
- **Verification:** `uv run mypy src/para_files/utils/file_utils.py` reports no issues
- **Committed in:** 5d790dd (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - minor type ignore adjustment)
**Impact on plan:** Necessary for mypy compliance. No scope creep.

## Issues Encountered

- mypy `unused-ignore` error because py7zr wasn't installed when Task 1 ran — resolved by installing py7zr in Task 2 and removing the now-unused ignore comment.

## User Setup Required

None - py7zr is installed automatically via `uv sync --all-extras`. No external services or manual configuration needed.

## Next Phase Readiness

- Archive manifest classification signal is now available in the pipeline
- ZIP and 7Z files with meaningful internal filenames will route correctly (e.g., "documents.zip" containing "invoice_2024.pdf" → documents category)
- 7Z support available when py7zr extra is installed; degrades gracefully otherwise

---
*Phase: 05-content-extraction*
*Completed: 2026-03-01*
