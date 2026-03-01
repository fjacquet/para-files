---
phase: 01-bug-fixes
verified: 2026-02-28T00:00:00Z
status: passed
score: 3/3 must-haves verified
re_verification: false
---

# Phase 1: Bug Fixes Verification Report

**Phase Goal:** The classification pipeline handles real-world input correctly without silent fallbacks
**Verified:** 2026-02-28
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                            | Status     | Evidence                                                                              |
|----|----------------------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------|
| 1  | A file named `document.PDF` is classified correctly (not skipped)                | VERIFIED   | `file_utils.py:172` — `extension=file_path.suffix.lower()`; 4 tests in `TestExtensionNormalization` |
| 2  | OCR rename only triggers when confidence exceeds 0.7                             | VERIFIED   | `config.py:185` — `default=0.7` in `OCRRenameConfig.min_confidence`; 3 tests in `TestOCRRenameConfig` |
| 3  | Technical/symbol-dense text receives a real embedding, not a zero vector         | VERIFIED   | `mlx_encoder.py:66-100` — `_encode_single` with progressive truncation; zero vector only on logged exception; 2 tests in `TestMLXEncoderZeroVectorGuard` |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact                                      | Expected                                  | Status     | Details                                                                  |
|-----------------------------------------------|-------------------------------------------|------------|--------------------------------------------------------------------------|
| `src/para_files/utils/file_utils.py`          | Normalized lowercase extension            | VERIFIED   | Line 172: `extension=file_path.suffix.lower()` matches required pattern  |
| `src/para_files/config.py`                    | OCR rename confidence default = 0.7       | VERIFIED   | Line 185: `default=0.7` in `OCRRenameConfig.min_confidence` field        |
| `src/para_files/encoders/mlx_encoder.py`      | `_encode_single` helper with progressive truncation | VERIFIED | Lines 66-100: `_encode_single` exists with fallback_chars/400/200/100 chain |
| `tests/test_file_utils.py`                    | Extension case normalization tests        | VERIFIED   | `TestExtensionNormalization` class, lines 22-48, 4 tests including `test_extension_stored_lowercase` |
| `tests/test_config.py`                        | OCR rename confidence default test        | VERIFIED   | `TestOCRRenameConfig` class, lines 79-101, 3 tests including `test_ocr_rename_min_confidence_default` |
| `tests/test_encoders.py`                      | Zero-vector guard test                    | VERIFIED   | `TestMLXEncoderZeroVectorGuard` class, lines 100-161, 2 tests including `test_no_zero_vector_for_dense_text` |

### Key Link Verification

| From                                     | To                               | Via                                                     | Status   | Details                                                             |
|------------------------------------------|----------------------------------|---------------------------------------------------------|----------|---------------------------------------------------------------------|
| `src/para_files/utils/file_utils.py`     | `FileMetadata.extension`         | `extension=file_path.suffix.lower()` in `extract_file_metadata` | WIRED | Line 172 matches required pattern exactly                          |
| `src/para_files/encoders/mlx_encoder.py` | `self._model.encode`             | per-text retry loop in `__call__` via `_encode_single`  | WIRED    | `__call__` lines 119-129: batch failure triggers `[self._encode_single(t) for t in texts]`; `_encode_single` lines 84-100 call `self._model.encode` per candidate |

### Requirements Coverage

| Requirement | Source Plan | Description                                                         | Status    | Evidence                                                                 |
|-------------|-------------|---------------------------------------------------------------------|-----------|--------------------------------------------------------------------------|
| BUG-01      | 01-PLAN.md  | File extension detection handles uppercase extensions correctly     | SATISFIED | `file_utils.py:172` lowercase normalization + `TestExtensionNormalization` (4 tests) |
| BUG-02      | 01-PLAN.md  | OCR rename default confidence threshold raised to 0.7 (was 0.3)    | SATISFIED | `config.py:185` `default=0.7` + `TestOCRRenameConfig` (3 tests)         |
| BUG-03      | 01-PLAN.md  | MLX encoder handles high token-density text without zero vectors    | SATISFIED | `mlx_encoder.py:66-100` `_encode_single` + `TestMLXEncoderZeroVectorGuard` (2 tests) |

All three requirements declared in the PLAN frontmatter are satisfied. REQUIREMENTS.md traceability table marks BUG-01, BUG-02, and BUG-03 as Complete for Phase 1. No orphaned requirements found for this phase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

No TODO, FIXME, PLACEHOLDER, stub returns, or empty handlers found in any of the three modified source files.

**Notable:** The zero-vector path in `_encode_single` (line 99-100) is the only remaining `[0.0] * dim` return. It is guarded by a `logger.exception(...)` call on line 97 and is only reachable if even the 100-character encode fails — this is acceptable and correctly logged as an error.

### Human Verification Required

None. All three fixes are deterministic and fully verifiable by static analysis and unit tests. No visual rendering, real-time behavior, or external service integration is involved.

---

## Detail Walkthrough

### BUG-01: Extension Case Normalization

**Fix location:** `src/para_files/utils/file_utils.py`, line 172

The `extract_file_metadata` function constructs a `FileMetadata` instance at lines 169-183. The `extension` field is set to `file_path.suffix.lower()` — this is the single authoritative construction point. Downstream consumers (rules engine, book detector) that compare extensions against lowercase sets will now see `.pdf` for `document.PDF`, not `.PDF`.

The PDF metadata extraction guard at line 160 (`if file_path.suffix.lower() == ".pdf"`) is independent — it uses the raw path suffix, not `FileMetadata.extension`. This is correct and unchanged.

**Test evidence:** `tests/test_file_utils.py::TestExtensionNormalization`

- `test_extension_stored_lowercase` — `document.PDF` → `meta.extension == ".pdf"`
- `test_extension_lowercase_epub` — `book.EPUB` → `meta.extension == ".epub"`
- `test_extension_lowercase_chm` — `manual.CHM` → `meta.extension == ".chm"`
- `test_mixed_case_extension` — `file.TxT` → `meta.extension == ".txt"`

### BUG-02: OCR Rename Confidence Threshold

**Fix location:** `src/para_files/config.py`, lines 184-189

`OCRRenameConfig.min_confidence` Field default is `0.7`, with `ge=0.0` and `le=1.0` validators intact. The description string is unchanged. Users can still override to a lower value explicitly (verified by `test_ocr_rename_min_confidence_accepts_low_value`).

**Test evidence:** `tests/test_config.py::TestOCRRenameConfig`

- `test_ocr_rename_min_confidence_default` — `OCRRenameConfig().min_confidence == 0.7`
- `test_ocr_rename_min_confidence_accepts_low_value` — explicit 0.3 accepted
- `test_ocr_rename_min_confidence_rejects_out_of_range` — 1.5 raises `ValidationError`

### BUG-03: MLX Encoder Zero-Vector Replacement

**Fix location:** `src/para_files/encoders/mlx_encoder.py`, lines 66-129

`_encode_single` (lines 66-100) implements progressive truncation:

1. Try `text[:fallback_chars]` (700 chars)
2. Try `text[:400]`
3. Try `text[:200]`
4. Last resort: `text[:100]` or `"document"`
5. Only if all of the above fail: return `[0.0] * dim` with `logger.exception()`

`__call__` (lines 102-129) uses this:

- Normal path: batch encode all truncated texts (line 121)
- On `IndexError`: `logger.warning(...)` then `return [self._encode_single(t) for t in texts]` (line 125)

The original silent `return [[0.0] * 768 for _ in texts]` is entirely removed. The zero-vector path is only reachable via the logged exception at line 97 in `_encode_single`.

**Test evidence:** `tests/test_encoders.py::TestMLXEncoderZeroVectorGuard`

- `test_no_zero_vector_for_dense_text` — 2000-char input returns non-zero embedding after batch failure + per-text retry
- `test_encode_single_progressive_truncation` — verifies `_encode_single` tries multiple lengths, not just the shortest

---

_Verified: 2026-02-28_
_Verifier: Claude (gsd-verifier)_
