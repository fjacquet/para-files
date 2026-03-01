---
phase: 05-content-extraction
plan: "01"
subsystem: content-extraction
tags: [openpyxl, odfpy, xlrd, spreadsheet, excel, ods, file-utils]

# Dependency graph
requires:
  - phase: 04-user-features
    provides: "read_content_preview() dispatch framework in file_utils.py"
provides:
  - "Excel (.xlsx, .xlsm, .xls) content extraction via _read_excel_file()"
  - "ODS content extraction via _read_ods_file()"
  - "EXCEL_EXTENSIONS and _SPREADSHEET_MAX_CELLS constants"
  - "odfpy installed as project dependency"
affects: [pipeline, semantic-router, classifiers]

# Tech tracking
tech-stack:
  added: [odfpy>=1.4.1, openpyxl (already present but now used), xlrd (optional lazy import)]
  patterns:
    - "Lazy imports inside private functions (avoids top-level import errors for optional deps)"
    - "Extract-helper + dispatch pattern: _extract_*_content() + _read_*_file() pairs"
    - "Graceful degradation: ImportError and Exception both return filename fallback"
    - "Cell count guard with _SPREADSHEET_MAX_CELLS constant prevents runaway on large sheets"

key-files:
  created: []
  modified:
    - src/para_files/utils/file_utils.py
    - pyproject.toml
    - uv.lock

key-decisions:
  - "Use openpyxl read_only=True, data_only=True for xlsx/xlsm: avoids formula eval, faster"
  - "xlrd used only for legacy .xls (lazy import); prefer openpyxl for modern formats"
  - "All odfpy/xlrd/openpyxl imports are lazy (inside function body) to avoid module-level failures"
  - "Extract helper functions (_extract_xlsx_content, _extract_xls_content, _extract_ods_content) to stay within ruff C901/PLR0912 complexity limits"
  - "Add PLR0911 per-file ignore for file_utils.py (read_content_preview is a dispatch function by design)"

patterns-established:
  - "Reader pattern: private _read_*_file() calls _extract_*_content() helper, catches ImportError + Exception separately"
  - "Constants for magic values: _SPREADSHEET_MAX_CELLS = 200 instead of inline literals"

requirements-completed: [XTRCT-01, XTRCT-02, XTRCT-04]

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 5 Plan 01: Excel and ODS Content Extraction Summary

**openpyxl-based xlsx/xlsm reader, xlrd-based legacy xls reader, and odfpy-based ODS reader wired into read_content_preview() dispatch with graceful corruption fallback**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-01T12:41:24Z
- **Completed:** 2026-03-01T12:44:37Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `EXCEL_EXTENSIONS` frozenset constant and `_SPREADSHEET_MAX_CELLS = 200` guard constant
- Implemented `_extract_xlsx_content()` / `_extract_xls_content()` helper pair + `_read_excel_file()` dispatcher for .xlsx, .xlsm, .xls files
- Implemented `_extract_ods_content()` helper + `_read_ods_file()` dispatcher for .ods files
- Added `odfpy>=1.4.1` to pyproject.toml and installed successfully
- Wired both dispatchers into `read_content_preview()` after the PDF block
- All corrupt/encrypted files log a warning and return `Filename: X` — no crash

## Task Commits

Each task was committed atomically:

1. **Task 1+2: Excel (_read_excel_file) and ODS (_read_ods_file) readers** - `a1c476f` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/para_files/utils/file_utils.py` - Added EXCEL_EXTENSIONS, _SPREADSHEET_MAX_CELLS, _extract_xlsx_content, _extract_xls_content, _read_excel_file, _extract_ods_content, _read_ods_file; wired into read_content_preview()
- `pyproject.toml` - Added odfpy>=1.4.1 dependency; added mypy overrides for odf.*, xlrd.*, openpyxl.*; added PLR0911 per-file ignore for file_utils.py
- `uv.lock` - Updated lockfile with odfpy and defusedxml (odfpy dependency)

## Decisions Made

- Used `read_only=True, data_only=True` with openpyxl to skip formula evaluation and reduce memory usage
- Kept all library imports lazy (inside function body) to avoid top-level ImportError if a library is absent
- Refactored into `_extract_*_content()` helpers to meet ruff C901 (complexity ≤ 10) and PLR0912 (branches ≤ 12) requirements
- Added `PLR0911` per-file ignore for `file_utils.py` since `read_content_preview()` is an extension dispatch function and multiple returns are structurally required

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `# type: ignore[import-untyped]` comments after adding mypy overrides**
- **Found during:** Task 1+2 verification (mypy run)
- **Issue:** Plan template included `# type: ignore[import-untyped]` on odfpy/xlrd imports, but adding these modules to mypy overrides made the comments redundant causing `unused-ignore` errors
- **Fix:** Removed the comments from the lazy imports; overrides in pyproject.toml handle the suppression
- **Files modified:** src/para_files/utils/file_utils.py, pyproject.toml
- **Verification:** mypy passes with no errors
- **Committed in:** a1c476f

**2. [Rule 1 - Bug] Refactored to fix ruff complexity/magic-value violations**
- **Found during:** Task 1+2 verification (ruff check)
- **Issue:** _read_excel_file had C901 complexity=19, PLR0912 branches=18; magic `200` triggered PLR2004; read_content_preview exceeded PLR0911 return limit
- **Fix:** Extracted _extract_xlsx_content, _extract_xls_content, _extract_ods_content helpers; replaced magic 200 with _SPREADSHEET_MAX_CELLS constant; added PLR0911 per-file ignore
- **Files modified:** src/para_files/utils/file_utils.py, pyproject.toml
- **Verification:** ruff check passes with no violations
- **Committed in:** a1c476f

---

**Total deviations:** 2 auto-fixed (both Rule 1 — code correctness and linting compliance)
**Impact on plan:** Both fixes required for CI to pass. No functional scope creep — same behavior, cleaner structure.

## Issues Encountered

None beyond the ruff/mypy violations corrected under Deviations above.

## User Setup Required

None - no external service configuration required. `odfpy` is installed automatically via `uv sync`.

## Next Phase Readiness

- Spreadsheet content extraction is live; pipeline will now receive sheet names + cell values for Excel/ODS files
- Semantic router can classify budget spreadsheets, project plans, and financial files correctly
- Next plans in phase 05 can build on this extraction foundation (e.g., archive manifest peeking, CSV enrichment)

## Self-Check: PASSED

- `src/para_files/utils/file_utils.py` — FOUND
- `pyproject.toml` — FOUND
- `.planning/phases/05-content-extraction/05-01-SUMMARY.md` — FOUND
- Commit `a1c476f` — FOUND

---
*Phase: 05-content-extraction*
*Completed: 2026-03-01*
