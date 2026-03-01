---
phase: phase-1-bug-fixes
plan: "01"
subsystem: classification-pipeline
tags: [bug-fix, extension-normalization, ocr-threshold, mlx-encoder, zero-vector]
dependency_graph:
  requires: []
  provides: [BUG-01-fix, BUG-02-fix, BUG-03-fix]
  affects: [file-classification, ocr-rename, semantic-routing]
tech_stack:
  added: []
  patterns: [progressive-truncation, per-text-retry, lowercase-normalization]
key_files:
  created: []
  modified:
    - src/para_files/utils/file_utils.py
    - src/para_files/config.py
    - src/para_files/encoders/mlx_encoder.py
    - tests/test_file_utils.py
    - tests/test_config.py
    - tests/test_encoders.py
decisions:
  - Raise OCR rename confidence to 0.7 to prevent false renames on weak signals
  - Use progressive truncation (fallback_chars/400/200/100) rather than single fallback step
  - Cast numpy tolist() results to list[float] for mypy compliance instead of type: ignore
metrics:
  duration: "6 minutes"
  completed: "2026-02-28"
  tasks_completed: 3
  files_modified: 6
---

# Phase 1 Plan 01: Three Classification Pipeline Bug Fixes Summary

**One-liner:** Lowercase extension normalization at FileMetadata construction, OCR rename threshold raised from 0.3 to 0.7, and MLX encoder zero-vector fallback replaced with per-text progressive truncation.

## What Was Done

Fixed three confirmed bugs that cause silent misclassifications in the para-files pipeline:

### BUG-01: Extension Case Normalization (Task 1)

**File:** `src/para_files/utils/file_utils.py`

Changed `extension=file_path.suffix` to `extension=file_path.suffix.lower()` in the `extract_file_metadata` function. This is the single authoritative construction point for `FileMetadata.extension`. Without this fix, a file named `document.PDF` would have `.PDF` stored as its extension, causing it to be invisible to downstream consumers that compare against lowercase extension sets (rules engine, book detector, etc.).

**Tests added:** `tests/test_file_utils.py::TestExtensionNormalization` — 4 tests covering .PDF, .EPUB, .CHM, and mixed-case .TxT inputs.

### BUG-02: OCR Rename Confidence Threshold (Task 2)

**File:** `src/para_files/config.py`

Changed `OCRRenameConfig.min_confidence` default from `0.3` to `0.7`. The previous 0.3 threshold allowed OCR renames to trigger on weak, unreliable signals — such as bank statement headers where the extracted metadata had poor confidence. This caused files to be renamed based on incorrect or partial OCR results.

**Tests added:** `tests/test_config.py::TestOCRRenameConfig` — 3 tests covering default value (0.7), explicit lower override (0.3), and out-of-range rejection (>1.0).

### BUG-03: MLX Encoder Zero-Vector Fallback (Task 3)

**File:** `src/para_files/encoders/mlx_encoder.py`

Replaced the batch-level zero-vector fallback with per-text progressive truncation. The original code would return `[0.0] * 768` silently if a second batch encode failed after token-limit truncation. This caused symbol-dense or source-code files to receive zero vectors, which collapse semantic routing (everything looks equally (dis)similar to a zero vector).

New implementation:

- Added `_encode_single(text)` helper that tries progressively shorter prefixes: `fallback_chars` (700) → 400 → 200 → 100 chars
- Updated `__call__` to catch batch IndexError and retry per-text via `_encode_single`
- Zero vector is now only returned from `_encode_single` if even the 100-char encode fails (logged as an error, not silently)
- Added `cast("list[float]", ...)` for mypy compliance on numpy `tolist()[0]` return values

**Tests added:** `tests/test_encoders.py::TestMLXEncoderZeroVectorGuard` — 2 tests covering non-zero result on batch failure with retry success, and progressive truncation behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Type] Fixed mypy TC006 cast() type expression quoting**

- **Found during:** Task 3 verification (mypy run)
- **Issue:** `cast(list[float], ...)` needs quotes around the type argument for `from __future__ import annotations` compatibility
- **Fix:** Changed to `cast("list[float]", ...)` in both call sites in `_encode_single`
- **Files modified:** `src/para_files/encoders/mlx_encoder.py`
- **Commit:** ee1cbbd

**2. [Rule 1 - Lint] Fixed ruff EM101/TRY003 in test exception raising**

- **Found during:** Task 3 verification (ruff check)
- **Issue:** `raise IndexError("message")` violates EM101 (string literal in exception)
- **Fix:** Assigned messages to variables before raising in both test mock functions
- **Files modified:** `tests/test_encoders.py`
- **Commit:** ee1cbbd

**Note:** `src/para_files/pipeline.py` has 2 pre-existing ruff errors (TRY003/EM102 at line 235). These were present before this plan and are out of scope — logged to deferred items.

## Verification Results

All success criteria met:

- `uv run pytest` exits 0: 1226 passed, 3 skipped (pre-existing skips)
- `metadata.extension == ".pdf"` for `document.PDF` input: confirmed by TestExtensionNormalization
- `OCRRenameConfig().min_confidence == 0.7`: confirmed by TestOCRRenameConfig
- Non-zero embedding after IndexError on batch + per-text retry: confirmed by TestMLXEncoderZeroVectorGuard
- No new ruff or mypy errors introduced

## Self-Check: PASSED

Files verified to exist:

- src/para_files/utils/file_utils.py: FOUND
- src/para_files/config.py: FOUND
- src/para_files/encoders/mlx_encoder.py: FOUND
- tests/test_file_utils.py: FOUND
- tests/test_config.py: FOUND
- tests/test_encoders.py: FOUND

Commits verified:

- d236ecd (Task 1 - extension normalization): FOUND
- 3664511 (Task 2 - OCR threshold): FOUND
- b74012f (Task 3 - zero-vector fix): FOUND
- ee1cbbd (Task 3 - ruff fixes): FOUND
