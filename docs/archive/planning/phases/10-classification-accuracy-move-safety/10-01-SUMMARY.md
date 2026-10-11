---
phase: "10-classification-accuracy-move-safety"
plan: "01"
subsystem: "classifiers/book-detector,classifiers/rules-engine"
tags: ["testing", "false-positives", "book-detector", "rules-engine", "financial-exclusion"]
dependency_graph:
  requires: []
  provides: ["ACC-01", "ACC-02", "ACC-03"]
  affects: ["tests/test_book_detector.py", "tests/test_rules_engine.py"]
tech_stack:
  added: []
  patterns:
    - "TDD: tests written first, verified against existing correct production code"
    - "pytest fixtures for FileMetadata construction with tmp_path"
    - "unittest.mock.patch for isolating book detector signal chain"
key_files:
  created: []
  modified:
    - "tests/test_book_detector.py"
    - "tests/test_rules_engine.py"
decisions:
  - "No production code changes needed: book_detector.py already has correct financial exclusion flow (is_financial_document runs before ISBN extraction at line ~566)"
  - "Test coverage proves the financial check is absolute: extract_pdf_metadata not called when is_financial_document returns True"
  - "MIN_YEAR=1990 / MAX_YEAR=2040 boundary tests added to document the intentional date validation range"
metrics:
  duration: "~15 minutes"
  completed: "2026-03-22T18:14:34Z"
  tasks_completed: 2
  files_changed: 2
  tests_added: 19
  tests_before: 140
  tests_after: 159
---

# Phase 10 Plan 01: Book Detector False Positive Prevention + Rules Engine Date Edge Cases Summary

Test coverage to prevent French financial PDFs from being misclassified as books, plus rules engine date extraction boundary tests.

## What Was Done

### Task 1: Book Detector False Positive Tests (ACC-01, ACC-02)

Added `TestBookDetectorFalsePositives` class (11 tests) to `tests/test_book_detector.py`:

- **`test_iban_containing_pdf_not_classified_as_book`** — French bank statement with IBAN + BANQUE keywords returns None; `extract_pdf_metadata` is never called (financial check short-circuits the pipeline)
- **`test_financial_doc_with_isbn_like_reference`** — Content with both IBAN and a 13-digit number resembling an ISBN still returns None (financial check has absolute precedence)
- **`test_real_book_with_valid_isbn_not_blocked`** — Legitimate book PDF with no financial patterns correctly classifies as a book (confidence=1.0)
- **`test_invalid_isbn_all_zeros`** — All-zero ISBN does not crash; returns None (below threshold)
- **`test_iban_like_pattern_not_treated_as_isbn`** — French IBAN in a `facture_*.pdf` is not misread as ISBN
- **`test_swiss_iban_pattern_excluded`** — Swiss CH-format IBAN in an UBS document is excluded
- **`test_is_financial_document_minimum_threshold`** — Single FINANCIAL_EXCLUSION_PATTERN match returns False (MIN_FINANCIAL_PATTERN_MATCHES=2)
- **`test_is_financial_document_at_threshold`** — Two pattern matches (IBAN + BANQUE) returns True
- **`test_is_financial_document_filename_match`** — Filename "facture_2025.pdf" returns True regardless of content
- **`test_is_financial_document_content_match`** — IBAN + BANQUE in content returns True
- **`test_is_financial_document_below_threshold`** — Single BANK keyword alone returns False

**Key finding:** Production code already correct. `classify()` checks `is_financial_document()` at line 566, before `extract_pdf_metadata()` at line 591. The tests now document and lock this behavior.

### Task 2: Rules Engine Date Edge Cases and Pattern Shadowing (ACC-03)

Added `TestRulesEngineDateEdgeCases` class (8 tests) to `tests/test_rules_engine.py`:

- **`test_date_extraction_year_1989`** — Year 1989 < MIN_YEAR (1990) → `_extract_date_from_filename` returns None
- **`test_date_extraction_year_2041`** — Year 2041 > MAX_YEAR (2040) → returns None (avoids false positives from crypto keys etc.)
- **`test_date_extraction_pre_min_year`** — Year 1899 → returns None
- **`test_date_extraction_future_year_boundary`** — Year 2040 (at MAX_YEAR) → accepted, year==2040
- **`test_date_extraction_year_1990_min_boundary`** — Year 1990 (at MIN_YEAR) → accepted, year==1990
- **`test_pattern_shadowing_specific_before_general`** — When specific rule listed first, it wins for both-matching file
- **`test_pattern_shadowing_order_matters`** — When general rule listed first, it wins even if specific also matches
- **`test_pattern_shadowing_non_matching_file_uses_correct_rule`** — File matching only general pattern routes to general destination

**Key finding:** Rules engine applies rules in dict insertion order; first match wins. There is no automatic specificity ranking — YAML order controls routing priority.

## Deviations from Plan

None - plan executed exactly as written. Production code was already correct; tests verify existing behavior.

## Test Results

```
159 passed in 1.50s (was 140 before)
+19 new tests added
```

## Self-Check: PASSED

- tests/test_book_detector.py: FOUND
- tests/test_rules_engine.py: FOUND
- task1 commit 9509155: FOUND
- task2 commit 2b425f0: FOUND
