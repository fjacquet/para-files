---
phase: 08-foundation-hardening
plan: "03"
subsystem: testing
tags: [placeholder-resolver, pandoc, classifiers, tdd, error-handling]

# Dependency graph
requires:
  - phase: 08-01
    provides: encoder exception handling and classifier error boundaries
  - phase: 08-02
    provides: pandoc ALLOWED_EXTENSIONS allowlist and extension validation
provides:
  - Placeholder resolver with required/optional distinction (issuer/technology/location/country = required; year/YYYY/MM/DD/month/day = optional)
  - clean_unreplaced_placeholders returns str | None (None = reject bad path)
  - All 3 classifier call sites handle None from placeholder resolver
  - 19-test placeholder resolver test suite
  - 20-test pandoc integration test suite covering all failure modes
affects: [pipeline, classifiers, testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Required vs optional placeholder distinction with explicit rejection"
    - "noqa: PLR0911 for methods with legitimate multiple return paths (consistent with codebase)"

key-files:
  created:
    - tests/test_placeholder_resolver.py
    - tests/test_pandoc_integration.py
  modified:
    - src/para_files/utils/placeholder_resolver.py
    - src/para_files/classifiers/rules_engine.py
    - src/para_files/classifiers/semantic_classifier.py
    - src/para_files/classifiers/taxonomy_classifier.py
    - tests/test_rules_engine.py

key-decisions:
  - "location and country are required placeholders (unresolved = None), not optional — aligns with issuer and technology"
  - "taxonomy_classifier._resolve_pattern return type updated to str | None to propagate rejection"
  - "taxonomy_classifier.classify gets noqa: PLR0911 (same pattern as book_detector.py and llm_classifier.py)"

patterns-established:
  - "Placeholder policy pattern: required fields cause rejection (None), optional fields strip cleanly"
  - "Caller pattern: always check None before using clean_unreplaced_placeholders result"

requirements-completed: [ERR-04, TEST-02, TEST-05]

# Metrics
duration: 15min
completed: 2026-03-22
---

# Phase 08 Plan 03: Placeholder Rejection Policy and Pandoc Test Suite Summary

**Placeholder resolver now rejects paths with unresolved required placeholders (issuer/technology/location/country) returning None, strips optional date placeholders cleanly, with 39 new tests covering all edge cases**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-22T15:46:34Z
- **Completed:** 2026-03-22T16:01:34Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added `_REQUIRED_PLACEHOLDERS` and `_OPTIONAL_PLACEHOLDERS` to placeholder resolver, making `clean_unreplaced_placeholders` return `str | None`
- Updated all 3 classifier call sites (rules_engine, semantic_classifier, taxonomy_classifier) to handle None return with proper type safety
- Created 19-test `test_placeholder_resolver.py` covering required rejection, optional stripping, pass-through, and resolve+clean round-trips
- Created 20-test `test_pandoc_integration.py` covering broken install, timeout, extension validation, non-zero exit, empty output, and happy path

## Task Commits

Each task was committed atomically:

1. **Task 1: Update placeholder resolver with required/optional policy and add tests** - `929225f` (feat)
2. **Task 2: Create pandoc integration tests for failure modes** - `e3cbbb6` (test)

**Plan metadata:** (docs commit follows)

_Note: TDD tasks may have multiple commits (test -> feat -> refactor)_

## Files Created/Modified

- `src/para_files/utils/placeholder_resolver.py` - Added `_REQUIRED_PLACEHOLDERS`/`_OPTIONAL_PLACEHOLDERS`, changed return type to `str | None`, added loguru warning
- `src/para_files/classifiers/rules_engine.py` - Updated to handle None from placeholder resolver, updated `_make_classification` return type to `ClassificationResult | None`
- `src/para_files/classifiers/semantic_classifier.py` - Updated `_resolve_pattern` to return `str | None`, added None guard before ClassificationResult construction
- `src/para_files/classifiers/taxonomy_classifier.py` - Added loguru import, updated `_resolve_pattern` return type, added 3 None guards at call sites, added `noqa: PLR0911`
- `tests/test_placeholder_resolver.py` - New: 19 tests in 4 test classes
- `tests/test_pandoc_integration.py` - New: 20 tests in 6 test classes
- `tests/test_rules_engine.py` - Updated 3 tests: location/country now expected to reject (None), not strip

## Decisions Made

- **location and country as required placeholders**: The plan spec defines both as required (`_REQUIRED_PLACEHOLDERS`). This conflicted with 3 pre-existing tests that expected them to be stripped. Updated those tests to match the new correct behavior.
- **taxonomy_classifier._resolve_pattern return type**: Needed to change from `str` to `str | None` to propagate the rejection properly up to `classify`. This required adding 3 None guards at all call sites.
- **noqa: PLR0911**: The `classify` method had too many return statements after adding None guards. Applied `# noqa: PLR0911` consistent with `book_detector.py` and `llm_classifier.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated 3 pre-existing tests in test_rules_engine.py**
- **Found during:** Task 1 (running tests after implementation)
- **Issue:** `TestCleanUnreplacedLocation` expected `location`/`country` to be stripped (old behavior). After making them required, the tests failed with `None != 'photos/2024'`
- **Fix:** Updated test docstrings and assertions to reflect that unresolved location/country now causes rejection (returns None)
- **Files modified:** `tests/test_rules_engine.py`
- **Verification:** `uv run pytest tests/test_rules_engine.py -x -q` exits 0
- **Committed in:** 929225f (Task 1 commit)

**2. [Rule 1 - Bug] Fixed mypy type errors across 3 classifiers**
- **Found during:** Task 1 (mypy check after implementation)
- **Issue:** 4 mypy errors: `_make_classification` return type still `ClassificationResult`, `_resolve_pattern` return type still `str`, `category_path` used as `str` after resolving to `str | None`, taxonomy call sites using `str | None` where `str` expected
- **Fix:** Updated return types to `str | None` where needed, added early None checks before uses
- **Files modified:** `src/para_files/classifiers/rules_engine.py`, `src/para_files/classifiers/semantic_classifier.py`, `src/para_files/classifiers/taxonomy_classifier.py`
- **Verification:** `uv run mypy ...` exits 0 with "Success: no issues found in 4 source files"
- **Committed in:** 929225f (Task 1 commit)

**3. [Rule 1 - Bug] Added noqa: PLR0911 to taxonomy_classifier.classify**
- **Found during:** Task 1 (ruff check after implementation)
- **Issue:** New None guards added 3 more return statements, pushing classify over PLR0911 limit (7 > 6)
- **Fix:** Added `# noqa: PLR0911` consistent with `book_detector.py:482` and `llm_classifier.py:276`
- **Files modified:** `src/para_files/classifiers/taxonomy_classifier.py`
- **Verification:** `uv run ruff check ...` exits 0
- **Committed in:** 929225f (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 - Bug)
**Impact on plan:** All auto-fixes necessary for type correctness and test alignment with new behavior. No scope creep.

## Issues Encountered

Pre-existing failure in `tests/test_isbn_lookup.py::TestLookupIsbn::test_lookup_with_valid_isbn_structure` due to `ModuleNotFoundError: No module named 'pkg_resources'` in isbnlib. Confirmed pre-existing (fails on main without our changes). Out of scope.

## Next Phase Readiness

- Placeholder rejection policy in place: paths with missing required fields (issuer, technology, location, country) return None and are skipped by classifiers
- Full test coverage for placeholder edge cases (19 tests) and pandoc failure modes (20 tests)
- Ready for Phase 08 Plan 04 if it exists; foundation hardening goals for ERR-04, TEST-02, TEST-05 are met

---
*Phase: 08-foundation-hardening*
*Completed: 2026-03-22*
