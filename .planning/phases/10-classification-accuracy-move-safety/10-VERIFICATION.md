---
phase: 10-classification-accuracy-move-safety
verified: 2026-03-22T00:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 10: Classification Accuracy + Move Safety Verification Report

**Phase Goal:** Fix three classes of correctness bugs: (1) book detector false positives on French
financial documents, (2) silent YAML misconfiguration, (3) unsafe batch move operations. Also route
unclassifiable files from `0_Inbox` to `6_unclassified`.
**Verified:** 2026-03-22
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                    | Status     | Evidence                                                                         |
|----|------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------|
| 1  | `is_financial_document()` called BEFORE `extract_pdf_metadata()` in `classify()`        | VERIFIED   | Line 566 vs 591 in `book_detector.py`; financial check returns None immediately  |
| 2  | Financial false positive tests lock book detector behavior                               | VERIFIED   | `TestBookDetectorFalsePositives` (11 tests) in `test_book_detector.py`           |
| 3  | Rules engine date edge case tests cover years 1989, 2041, pattern shadowing              | VERIFIED   | `TestRulesEngineDateEdgeCases` (8 tests) in `test_rules_engine.py`               |
| 4  | `ReferenceTreeModel` + `RoutingRuleModel` validate YAML at load time with fail-fast      | VERIFIED   | Both Pydantic models in `reference_tree.py` lines 29-56; `load()` raises ValueError |
| 5  | `DEFAULT_UNCLASSIFIED_CATEGORY = "6_unclassified"` exists as module-level constant      | VERIFIED   | `pipeline.py` line 53; used in `classify()` line 357                            |
| 6  | `BatchMover` with completed-moves tracking, stop-on-first-failure, rollback              | VERIFIED   | `BatchMover`, `BatchMoveResult` in `mover.py` lines 492-633                     |
| 7  | `validate_destination_permissions()` runs before first file is moved (pre-flight)        | VERIFIED   | `_check_destination_permissions()` called at entry of `_move_files_sequential()` line 272 |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact                                              | Requirement | Status     | Details                                                         |
|-------------------------------------------------------|-------------|------------|-----------------------------------------------------------------|
| `src/para_files/classifiers/book_detector.py`         | ACC-01/02   | VERIFIED   | `is_financial_document` at line 566, before `extract_pdf_metadata` at 591 |
| `tests/test_book_detector.py` — `TestBookDetectorFalsePositives` | ACC-01/02 | VERIFIED | 11 tests including IBAN, Swiss IBAN, French filename patterns |
| `tests/test_rules_engine.py` — `TestRulesEngineDateEdgeCases`    | ACC-03    | VERIFIED | 8 tests covering MIN_YEAR=1990, MAX_YEAR=2040 boundaries and pattern shadowing |
| `src/para_files/reference_tree.py` — `RoutingRuleModel`, `ReferenceTreeModel` | ACC-04 | VERIFIED | Both Pydantic models present; `load()` raises `ValueError` with file path on validation failure |
| `src/para_files/pipeline.py` — `DEFAULT_UNCLASSIFIED_CATEGORY`   | ACC-05    | VERIFIED   | Constant `= "6_unclassified"` at line 53, used as fallback in `classify()` |
| `src/para_files/mover.py` — `BatchMover`, `BatchMoveResult`, `validate_destination_permissions` | MOV-01/02 | VERIFIED | All three present; LIFO rollback with `shutil.move`; `os.access(W_OK)` pre-flight |
| `src/para_files/cli/move_cmd.py` — `--rollback/--no-rollback` flag | MOV-02  | VERIFIED   | Flag at line 576; pre-flight at line 272 raises `typer.Exit(code=1)` on failure |

---

### Key Link Verification

| From                                    | To                                          | Via                                   | Status  | Details                                          |
|-----------------------------------------|---------------------------------------------|---------------------------------------|---------|--------------------------------------------------|
| `book_detector.classify()`              | `is_financial_document()`                   | direct call at line 566               | WIRED   | Returns `None` immediately if True               |
| `book_detector.classify()`              | `extract_pdf_metadata()`                    | call at line 591 (after financial check) | WIRED | Only reached when not a financial document       |
| `reference_tree.ReferenceTree.load()`   | `ReferenceTreeModel(**self._data)`          | Pydantic validation in `load()` line 98 | WIRED  | `ValidationError` re-raised as `ValueError`      |
| `pipeline.classify()`                   | `DEFAULT_UNCLASSIFIED_CATEGORY`             | used as fallback at line 357          | WIRED   | Constant defined at module level, used in return |
| `mover.BatchMover.move_batch()`         | `self._completed_moves`                     | tracking + `rollback()` reads list    | WIRED   | LIFO via `reversed(self._completed_moves)`       |
| `move_cmd._move_files_sequential()`     | `validate_destination_permissions()`        | via `_check_destination_permissions()` helper | WIRED | Pre-flight before any `_handle_move_file()` call |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                               | Status    | Evidence                                                  |
|-------------|-------------|-----------------------------------------------------------|-----------|-----------------------------------------------------------|
| ACC-01      | 10-01       | `is_financial_document()` called first in `classify()`   | SATISFIED | Line 566 precedes line 591 in `book_detector.py`          |
| ACC-02      | 10-01       | Financial check short-circuits ISBN extraction            | SATISFIED | Returns `None` at line 568 before any ISBN loop           |
| ACC-03      | 10-01       | Date edge case tests: 1989, 2041, pattern shadowing       | SATISFIED | `TestRulesEngineDateEdgeCases` (8 tests)                  |
| ACC-04      | 10-02       | Pydantic validation, fail-fast on invalid YAML            | SATISFIED | `ReferenceTreeModel`, `RoutingRuleModel` + ValueError raise |
| ACC-05      | 10-02       | `DEFAULT_UNCLASSIFIED_CATEGORY = "6_unclassified"` constant | SATISFIED | `pipeline.py` line 53; fallback at line 357               |
| MOV-01      | 10-03       | BatchMover with completed-moves tracking and rollback     | SATISFIED | `BatchMover.move_batch()` + `rollback()` LIFO             |
| MOV-02      | 10-03       | `validate_destination_permissions()` before first move   | SATISFIED | `_check_destination_permissions()` at line 272, pre-loop  |

---

### Anti-Patterns Found

None detected in the phase-modified files. Specific checks performed:

- No `TODO/FIXME/PLACEHOLDER` comments in `book_detector.py`, `pipeline.py`, `reference_tree.py`, `mover.py`, `move_cmd.py`
- No stub returns (`return null`, `return {}`, `return []`) in new code paths
- `BatchMover.rollback()` has substantive implementation (shutil.move, LIFO order, warning on failure)
- `validate_destination_permissions()` has substantive implementation (os.access walk-up logic)
- Pre-noted ruff issues in unrelated files (`chm_metadata.py`, `pandoc.py`, test files) are pre-existing and out of scope

---

### Human Verification Required

None. All requirements are structurally verifiable from the codebase:

- Financial exclusion order (line numbers)
- Pydantic model existence and wiring
- Constant definition and usage
- BatchMover implementation completeness
- Pre-flight call site ordering
- 1472 passing tests confirm runtime correctness

---

### Test Suite Summary

| Test Class                        | File                      | Tests | What It Covers                                          |
|-----------------------------------|---------------------------|-------|---------------------------------------------------------|
| `TestBookDetectorFalsePositives`  | `test_book_detector.py`   | 11    | IBAN false positive, Swiss IBAN, financial filename, threshold |
| `TestRulesEngineDateEdgeCases`    | `test_rules_engine.py`    | 8     | Year 1989/2041 boundaries, pattern shadowing order      |
| `TestReferenceTreeValidation`     | `test_reference_tree.py`  | 6     | Malformed YAML, empty YAML, missing/empty destination   |
| `TestDefaultUnclassifiedCategory` | `test_pipeline.py`        | 2     | Constant value, no-match pipeline fallback              |
| `TestValidateDestinationPermissions` | `test_mover.py`        | 4     | Writable/read-only dir, nonexistent parent, multiple dirs |
| `TestBatchMover`                  | `test_mover.py`           | 4     | All succeed, stop-on-first-failure, completed_moves tracking |
| `TestBatchMoverRollback`          | `test_mover.py`           | 2     | Full rollback after partial failure, dry-run rollback   |

**Full suite:** 1472 passed, 3 skipped (macOS OCR — expected)

---

### Gaps Summary

No gaps. All 7 observable truths are verified. All 7 requirements (ACC-01 through ACC-05, MOV-01,
MOV-02) are satisfied with substantive implementations and supporting test coverage. The three
correctness bug classes are fixed and locked by tests. Unclassifiable files now route to
`6_unclassified`.

---

_Verified: 2026-03-22_
_Verifier: Claude (gsd-verifier)_
