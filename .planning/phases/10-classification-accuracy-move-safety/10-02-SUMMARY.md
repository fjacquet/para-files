---
phase: 10-classification-accuracy-move-safety
plan: "02"
subsystem: classification
tags: [pydantic, yaml-validation, pipeline, reference-tree, unclassified]

# Dependency graph
requires:
  - phase: 10-classification-accuracy-move-safety
    provides: phase context and classification accuracy requirements (ACC-04, ACC-05)

provides:
  - Pydantic validation (ReferenceTreeModel, RoutingRuleModel) in reference_tree.py
  - Fail-fast YAML loading with clear error messages including file path and failing field
  - DEFAULT_UNCLASSIFIED_CATEGORY = "6_unclassified" constant in pipeline.py
  - Pipeline default category changed from 0_Inbox to 6_unclassified
  - LLM classifier rejects both 0_Inbox and 6_unclassified responses

affects: [pipeline, reference-tree, classification, mover, cli-scan, cli-inbox]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic model wrapping raw YAML dict at load time for structural validation"
    - "Module-level DEFAULT_UNCLASSIFIED_CATEGORY constant for pipeline fallback"

key-files:
  created: []
  modified:
    - src/para_files/reference_tree.py
    - src/para_files/pipeline.py
    - src/para_files/classifiers/llm_classifier.py
    - tests/test_reference_tree.py
    - tests/test_pipeline.py

key-decisions:
  - "Use plain ValueError (not custom exception) for YAML validation failures — simpler, consistent with project style"
  - "Load raw YAML into a local variable first to avoid mypy 'unreachable' false positive on None check"
  - "6_unclassified added to _VALID_PARA_PREFIXES so sanitization passes, but immediately rejected to defer to pipeline default"
  - "Update existing test assertions from 0_Inbox to 6_unclassified for consistency"

patterns-established:
  - "Fail-fast YAML validation: wrap parsed dict in Pydantic model before use, raise ValueError with file path on failure"
  - "Semantic routing constants: pipeline-level DEFAULT_UNCLASSIFIED_CATEGORY keeps the fallback destination in one place"

requirements-completed: [ACC-04, ACC-05]

# Metrics
duration: 18min
completed: 2026-03-22
---

# Phase 10 Plan 02: YAML Validation and Unclassified Routing Summary

**Pydantic ReferenceTreeModel + RoutingRuleModel validate YAML at load time, and pipeline now routes unmatched files to 6_unclassified instead of 0_Inbox**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-22T10:00:00Z
- **Completed:** 2026-03-22T10:18:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `RoutingRuleModel` and `ReferenceTreeModel` Pydantic models to `reference_tree.py` — any YAML with missing or empty `destination` fields now raises `ValueError` at startup with file path
- Changed pipeline default from `"0_Inbox"` to `DEFAULT_UNCLASSIFIED_CATEGORY = "6_unclassified"` — unmatched files no longer pollute the user triage inbox
- Updated `llm_classifier.py` to reject LLM responses of `"6_unclassified"` (alongside `"0_Inbox"`) so the LLM cannot erroneously claim the file is unclassifiable
- Added 6 new `TestReferenceTreeValidation` tests covering malformed YAML, empty YAML, missing/empty destination, and valid minimal/full cases
- Added `TestDefaultUnclassifiedCategory` with 2 tests verifying the constant value and no-match behavior

## Task Commits

1. **Task 1: Add Pydantic validation to reference tree YAML loading** - `9851d00` (feat)
2. **Task 2: Route unclassified files to 6_unclassified instead of 0_Inbox** - `5c091ae` (feat)

## Files Created/Modified

- `src/para_files/reference_tree.py` - Added `RoutingRuleModel`, `ReferenceTreeModel`, updated `load()` with None check and Pydantic validation
- `src/para_files/pipeline.py` - Added `DEFAULT_UNCLASSIFIED_CATEGORY = "6_unclassified"`, updated fallback in `classify()` and docstrings
- `src/para_files/classifiers/llm_classifier.py` - Added `"6_unclassified"` to `_VALID_PARA_PREFIXES`, updated rejection check to cover both `0_Inbox` and `6_unclassified`
- `tests/test_reference_tree.py` - Added `TestReferenceTreeValidation` with 6 tests
- `tests/test_pipeline.py` - Added `DEFAULT_UNCLASSIFIED_CATEGORY` import, updated 3 existing assertions, added `TestDefaultUnclassifiedCategory` with 2 tests

## Decisions Made

- Used plain `ValueError` for YAML validation failures (not a custom `ReferenceTreeError`) — simpler and consistent with other error patterns in the codebase; custom exception was listed as an option in CONTEXT.md and was not required
- Loaded YAML into `raw_data: Any` local variable before assigning to `self._data` — prevents a mypy `[unreachable]` error caused by the `dict[str, Any]` type annotation on `_data` masking the `None` return case of `yaml.safe_load()`
- Added `"6_unclassified"` to `_VALID_PARA_PREFIXES` so the sanitization step passes it through, then immediately reject it at the same level as `"0_Inbox"` — this approach is consistent with the existing `0_Inbox` rejection logic

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mypy `[unreachable]` on None check in load()**
- **Found during:** Task 1 (reference tree validation)
- **Issue:** `self._data` typed as `dict[str, Any]` makes the `if self._data is None` branch unreachable according to mypy
- **Fix:** Load YAML into a local `raw_data: Any` variable first, check None on that, then assign to `self._data`
- **Files modified:** `src/para_files/reference_tree.py`
- **Verification:** `uv run mypy src/para_files/reference_tree.py` exits 0
- **Committed in:** `9851d00` (Task 1 commit)

**2. [Rule 1 - Bug] Fixed ruff E501 line too long in llm_classifier.py**
- **Found during:** Task 2 quality check
- **Issue:** `_VALID_PARA_PREFIXES` tuple exceeded 100-char line limit after adding `"6_unclassified"`
- **Fix:** Reformatted tuple as multi-line with trailing comma
- **Files modified:** `src/para_files/classifiers/llm_classifier.py`
- **Verification:** `uv run ruff check src/para_files/classifiers/llm_classifier.py` exits 0
- **Committed in:** `5c091ae` (Task 2 commit)

**3. [Rule 1 - Bug] Updated 3 existing test assertions from "0_Inbox" to "6_unclassified"**
- **Found during:** Task 2 (pipeline default change)
- **Issue:** `test_classify_returns_inbox_when_no_match`, `test_pipeline_returns_default_when_only_classifier_fails`, and `test_pipeline_returns_default_when_all_classifiers_fail` asserted `result.category == "0_Inbox"` — now incorrect after pipeline default change
- **Fix:** Updated all three tests to assert `result.category == DEFAULT_UNCLASSIFIED_CATEGORY`
- **Files modified:** `tests/test_pipeline.py`
- **Verification:** `uv run pytest tests/test_pipeline.py -x` exits 0
- **Committed in:** `5c091ae` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 downstream test update)
**Impact on plan:** All auto-fixes were necessary for correctness and code quality. No scope creep.

## Issues Encountered

None — plan executed cleanly once mypy reachability issue was identified and resolved.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- ACC-04 (YAML validation) and ACC-05 (6_unclassified routing) are verified complete
- `6_unclassified` folder should be created by the `init` command (deferred to ACC-05 note in CONTEXT.md: "Whether to add 6_unclassified to the PARA folder creation logic in init command")
- Phase 10-03 (mover rollback and permission pre-flight) can proceed

---
*Phase: 10-classification-accuracy-move-safety*
*Completed: 2026-03-22*

## Self-Check: PASSED

- FOUND: src/para_files/reference_tree.py
- FOUND: src/para_files/pipeline.py
- FOUND: src/para_files/classifiers/llm_classifier.py
- FOUND: .planning/phases/10-classification-accuracy-move-safety/10-02-SUMMARY.md
- FOUND: commit 9851d00 (Task 1)
- FOUND: commit 5c091ae (Task 2)
