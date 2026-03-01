---
phase: 02-code-quality
plan: 02
subsystem: error-handling
tags: [loguru, isbn, pdf, logging, exception-handling]

# Dependency graph
requires:
  - phase: 02-code-quality-01
    provides: placeholder_resolver utility (context only)
provides:
  - ISBN enrichment failures logged at WARNING with exception type and ISBN
  - ISBN utility function failures logged at DEBUG before returning fallback
  - PDF page extraction failures logged at DEBUG with page number and exception type
affects: [classifiers, book-detector, pdf-metadata, isbn-lookup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Named exception logging: `except Exception as e` with `type(e).__name__` in log message"
    - "DEBUG logging for optional/recoverable failures, WARNING for enrichment failures"

key-files:
  created: []
  modified:
    - src/para_files/utils/isbn_lookup.py
    - src/para_files/utils/pdf_metadata.py

key-decisions:
  - "Use logger.warning for ISBN enrichment failures (description/cover) — these are optional but worth surfacing"
  - "Use logger.debug for utility function failures (validate_isbn, normalize_isbn, isbn_to_isbn13) — low-level noise"
  - "Use logger.debug for PDF page extraction failures — corrupted pages are common, DEBUG is appropriate"
  - "Retain continue after PDF page debug log — failed pages are still skipped, only logging added"

patterns-established:
  - "Named exception pattern: always bind `as e` and log `type(e).__name__, e` for diagnosability"
  - "No bare except pass — every exception swallow must have a log message with context"

requirements-completed:
  - QUAL-01
  - QUAL-03

# Metrics
duration: 7min
completed: 2026-02-28
---

# Phase 2 Plan 02: ISBN and PDF Error Logging Summary

**Named-exception logging replaces all silent pass/continue in isbn_lookup.py and pdf_metadata.py — network timeouts and corrupted pages are now traceable via WARNING/DEBUG log messages**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-28T20:23:19Z
- **Completed:** 2026-02-28T20:30:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Description and cover-URL enrichment except blocks in isbn_lookup.py now emit `logger.warning` with `type(e).__name__` and the ISBN — network timeouts are no longer silent
- Three utility functions (validate_isbn, normalize_isbn, isbn_to_isbn13) now log at DEBUG before returning their fallback value
- PDF page extraction except block in pdf_metadata.py now logs at DEBUG with page number and filename before continuing — corrupted page failures are traceable
- All noqa S110/S112 suppressions that masked silent failure removed

## Task Commits

1. **Task 1: Fix silent ISBN enrichment failures in isbn_lookup.py** - `18a29f9` (fix, included in 02-01 plan execution)
2. **Task 2: Fix silent page extraction failure in pdf_metadata.py** - `06fcd43` (fix)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `src/para_files/utils/isbn_lookup.py` - Description and cover enrichment blocks now warn; utility function blocks now debug
- `src/para_files/utils/pdf_metadata.py` - Page extraction loop exception block now logs debug with page/file context

## Decisions Made

- logger.warning chosen for enrichment failures (description, cover URL) — these are network calls that may indicate connectivity issues worth surfacing
- logger.debug chosen for utility functions — validate/normalize/convert failures are typically invalid input, low signal
- logger.debug chosen for PDF page extraction — corrupted pages are common in the wild, DEBUG avoids log noise on problematic PDFs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Task 1 changes (isbn_lookup.py) had already been committed as part of the 02-01 plan execution. No re-work required; changes verified correct against plan spec.

## Next Phase Readiness

- Both source files meet success criteria: no silent exception swallowing remains in isbn_lookup.py or pdf_metadata.py
- Network timeout in ISBN fetch now produces WARNING log with type(e).**name** — success criterion 1 of Phase 2 met
- Corrupted page in PDF extraction now produces DEBUG log with page number — traceable failures established

## Self-Check: PASSED

- src/para_files/utils/isbn_lookup.py — FOUND
- src/para_files/utils/pdf_metadata.py — FOUND
- .planning/phases/02-code-quality/02-02-SUMMARY.md — FOUND
- Commit 06fcd43 (pdf_metadata fix) — FOUND
- Commit 18a29f9 (isbn_lookup fix) — FOUND

---
*Phase: 02-code-quality*
*Completed: 2026-02-28*
