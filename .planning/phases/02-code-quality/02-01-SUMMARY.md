---
phase: 02-code-quality
plan: "01"
subsystem: classifiers
tags: [python, refactor, dry, placeholder, utils]

requires: []
provides:
  - "src/para_files/utils/placeholder_resolver.py with resolve_placeholders and clean_unreplaced_placeholders"
  - "Single canonical placeholder cleanup replacing three divergent implementations"
affects:
  - "Any future classifier that needs placeholder cleanup"
  - "03-explainability"

tech-stack:
  added: []
  patterns:
    - "Centralized utility pattern: shared logic in utils/, imported by all consumers"
    - "Pure function pattern: placeholder_resolver functions are side-effect-free"

key-files:
  created:
    - src/para_files/utils/placeholder_resolver.py
  modified:
    - src/para_files/classifiers/rules_engine.py
    - src/para_files/classifiers/semantic_classifier.py
    - src/para_files/classifiers/taxonomy_classifier.py
    - tests/test_rules_engine.py

key-decisions:
  - "Delete private methods _clean_unreplaced_location and _clean_unreplaced_date from RulesEngineClassifier — functionality now lives in placeholder_resolver"
  - "Update tests to call clean_unreplaced_placeholders directly instead of deleted private methods"

patterns-established:
  - "Placeholder cleanup pattern: always call clean_unreplaced_placeholders(result) as final step in path resolution"
  - "Utility import pattern: from para_files.utils.placeholder_resolver import clean_unreplaced_placeholders"

requirements-completed: [QUAL-02]

duration: 6min
completed: 2026-02-28
---

# Phase 2 Plan 01: Placeholder Resolver Centralization Summary

**Single `clean_unreplaced_placeholders` utility in `placeholder_resolver.py` replaces three divergent inline regex cleanup implementations across rules_engine, semantic_classifier, and taxonomy_classifier**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-28T20:23:25Z
- **Completed:** 2026-02-28T20:29:25Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created `src/para_files/utils/placeholder_resolver.py` with two pure functions: `resolve_placeholders` (param substitution) and `clean_unreplaced_placeholders` (remove leftover tokens + normalize slashes)
- Replaced `_clean_unreplaced_location` + `_clean_unreplaced_date` in rules_engine.py with a single import call, eliminating 43 lines of duplicated logic
- Replaced inline `re.sub(r"\{[^}]+\}", ...)` chains in both semantic_classifier.py and taxonomy_classifier.py with the shared utility
- Updated test suite (TestCleanUnreplacedLocation, TestCleanUnreplacedDate) to test `clean_unreplaced_placeholders` directly rather than the deleted private methods

## Task Commits

Each task was committed atomically:

1. **Task 1: Create placeholder_resolver.py with unified cleanup logic** - `18a29f9` (feat)
2. **Task 2: Refactor three classifiers to use placeholder_resolver** - `1d09dcd` (refactor)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/para_files/utils/placeholder_resolver.py` - New canonical utility: resolve_placeholders + clean_unreplaced_placeholders
- `src/para_files/classifiers/rules_engine.py` - Deleted _clean_unreplaced_location/_clean_unreplaced_date, added import
- `src/para_files/classifiers/semantic_classifier.py` - Replaced inline re.sub chain with clean_unreplaced_placeholders call
- `src/para_files/classifiers/taxonomy_classifier.py` - Replaced inline re.sub chain with clean_unreplaced_placeholders call
- `tests/test_rules_engine.py` - Updated test classes to call shared utility directly

## Decisions Made

- Deleted the two private methods rather than delegating to the new utility — they were internal cleanup steps with no external callers, making deletion cleaner than wrapping
- Updated tests to call `clean_unreplaced_placeholders` directly rather than via the classifier, since the behavior is now owned by the utility module

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated tests that directly called deleted private methods**

- **Found during:** Task 2 (refactoring classifiers)
- **Issue:** `TestCleanUnreplacedLocation` and `TestCleanUnreplacedDate` test classes called `classifier._clean_unreplaced_location()` and `classifier._clean_unreplaced_date()` directly. Deleting those methods caused AttributeError on 9 tests.
- **Fix:** Updated both test classes to import and call `clean_unreplaced_placeholders` from `placeholder_resolver` directly, since behavior is now in the utility
- **Files modified:** tests/test_rules_engine.py
- **Verification:** 1226 tests pass, 3 skipped
- **Committed in:** 1d09dcd (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - test update for deleted private methods)
**Impact on plan:** Necessary correctness fix. Test semantics unchanged — still verify the same cleanup behavior, now through the canonical function.

## Issues Encountered

- Pre-existing ruff errors TRY003/EM102 in pipeline.py:235 remain (noted in STATE.md as out-of-scope). The classifiers themselves are ruff/mypy clean.

## Next Phase Readiness

- All classifiers now share a single placeholder cleanup path — adding a new placeholder type requires editing only `placeholder_resolver.py`
- 1226 tests passing, mypy clean across 62 source files
- Ready for Phase 2 Plan 02

---
*Phase: 02-code-quality*
*Completed: 2026-02-28*
