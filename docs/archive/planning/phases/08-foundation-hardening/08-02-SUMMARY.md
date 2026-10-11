---
phase: 08-foundation-hardening
plan: 02
subsystem: utils
tags: [exceptions, subprocess-safety, platform-markers, test-quality]
dependency_graph:
  requires: []
  provides: [exception-narrowing, subprocess-extension-validation, macos-platform-markers]
  affects: [src/para_files/utils/, tests/]
tech_stack:
  added: []
  patterns: [specific-exception-types, platform-skip-markers, subprocess-allowlist]
key_files:
  created: []
  modified:
    - src/para_files/utils/pandoc.py
    - src/para_files/utils/ocr.py
    - src/para_files/utils/isbn_lookup.py
    - src/para_files/utils/file_utils.py
    - src/para_files/utils/chm_metadata.py
    - src/para_files/utils/pdf_metadata.py
    - src/para_files/utils/epub_metadata.py
    - src/para_files/utils/exiftool.py
    - src/para_files/utils/geolocation.py
    - src/para_files/utils/technology_extractor.py
    - tests/conftest.py
    - tests/test_ocr.py
    - tests/test_ocr_metadata.py
    - tests/test_pandoc.py
    - tests/test_pdf_metadata.py
    - tests/test_geolocation.py
    - pyproject.toml
decisions:
  - "ALLOWED_EXTENSIONS in pandoc.py excludes .md/.tex/.latex - those are read directly as text"
  - "exiftool.py has no extension restriction per user decision (metadata tool, safe for all types)"
  - "Added zipfile.BadZipFile and RuntimeError to exception tuples after discovering test failures"
  - "Added tests/ to pythonpath in pyproject.toml to enable conftest imports in test files"
metrics:
  duration_minutes: 29
  completed: "2026-03-22T15:42:17Z"
  tasks_completed: 2
  files_modified: 17
---

# Phase 8 Plan 2: Exception Narrowing and Platform Markers Summary

**One-liner:** Replaced all `except Exception: # noqa: BLE001` suppressions in 10 utility files with specific exception types, added subprocess extension allowlists to pandoc.py and chm_metadata.py, and isolated macOS OCR tests with `macos_only` skip markers.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Narrow exceptions in utility modules and add subprocess extension validation | a83015e | 14 files |
| 2 | Add macOS platform skip markers for OCR tests | fff7cc6 | 6 files |

## What Was Done

### Task 1: Exception Narrowing and Subprocess Extension Validation

**10 utility files updated** with specific exception types replacing broad `except Exception`:

| Module | Exceptions Added | Sites Fixed |
|--------|-----------------|-------------|
| `pandoc.py` | `subprocess.SubprocessError, FileNotFoundError, OSError` | 2 |
| `ocr.py` | `ImportError, OSError, RuntimeError, ValueError` | 2 |
| `isbn_lookup.py` | `ConnectionError, TimeoutError, OSError, ValueError, KeyError` | 6 |
| `file_utils.py` | Various + `zipfile.BadZipFile` | 7 |
| `chm_metadata.py` | `subprocess.SubprocessError, FileNotFoundError, OSError, UnicodeDecodeError, ValueError` | 4 |
| `pdf_metadata.py` | `OSError, ValueError, KeyError, RuntimeError, PyPdfError` | 4 |
| `epub_metadata.py` | `OSError, ValueError, KeyError, UnicodeDecodeError` | 2 |
| `exiftool.py` | `subprocess.SubprocessError, FileNotFoundError, OSError` | 1 |
| `geolocation.py` | `ConnectionError, TimeoutError, OSError, ValueError` | 1 |
| `technology_extractor.py` | `ValueError, KeyError, OSError, RuntimeError` | 2 |

**Subprocess extension validation:**
- `pandoc.py`: Added `ALLOWED_EXTENSIONS: frozenset[str]` with 18 supported formats; both `_run_pandoc_to_plain()` and `extract_metadata()` now check before subprocess call
- `chm_metadata.py`: `_extract_chm_to_temp()` now checks `suffix.lower() != ".chm"` before subprocess
- `exiftool.py`: No extension restriction added (per plan — metadata tool is safe for all types)

### Task 2: macOS Platform Skip Markers

- `tests/conftest.py`: Added `macos_only = pytest.mark.skipif(platform.system() != "Darwin", ...)`
- `pyproject.toml`: Registered `macos_only` marker in pytest markers list
- `pyproject.toml`: Added `tests/` to `pythonpath` to enable `from conftest import macos_only`
- `tests/test_ocr.py`: `@macos_only` applied to `TestExtractTextIntegration` class
- `tests/test_ocr_metadata.py`: `from conftest import macos_only` added (available for future use)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_pandoc.py used .md extension not in ALLOWED_EXTENSIONS**
- **Found during:** Task 1 verification
- **Issue:** `test_extract_metadata_success` and integration test used `.md` which was intentionally excluded from `ALLOWED_EXTENSIONS`
- **Fix:** Updated tests to use `.rst` extension which is in the allowlist
- **Files modified:** `tests/test_pandoc.py`
- **Commit:** a83015e

**2. [Rule 1 - Bug] pypdf.errors.PyPdfError not caught by initial exception tuple**
- **Found during:** Task 1 verification (test_file_utils.py::TestExtensionNormalization::test_extension_stored_lowercase)
- **Issue:** pypdf raises `PdfStreamError` which doesn't inherit from `OSError, ValueError, KeyError, RuntimeError`
- **Fix:** Added `PyPdfError` import and added to exception tuple in `pdf_metadata.py`
- **Files modified:** `src/para_files/utils/pdf_metadata.py`
- **Commit:** a83015e

**3. [Rule 1 - Bug] Test mocks raised generic Exception not matching narrowed handlers**
- **Found during:** Task 1 verification (multiple test files)
- **Issue:** `test_pdf_metadata.py`, `test_ocr.py`, `test_geolocation.py` raised bare `Exception(...)` which no longer matched narrowed catches
- **Fix:** Updated test mocks to raise specific exceptions: `PyPdfError`, `OSError`, `ConnectionError`
- **Files modified:** `tests/test_pdf_metadata.py`, `tests/test_ocr.py`, `tests/test_geolocation.py`
- **Commit:** a83015e

**4. [Rule 1 - Bug] zipfile.BadZipFile not caught for Excel/ODS/archive operations**
- **Found during:** Task 1 full suite run (test_content_extraction.py)
- **Issue:** `BadZipFile` inherits from `Exception` directly, not from `OSError` — `.xlsx`/`.ods`/`.zip` corrupt file tests failed
- **Fix:** Added `subprocess` and `zipfile` top-level imports to `file_utils.py`; added `zipfile.BadZipFile` to Excel, ODS, and archive exception catches
- **Files modified:** `src/para_files/utils/file_utils.py`
- **Commit:** fff7cc6

**5. [Rule 1 - Bug] RuntimeError not in technology_extractor exception tuples**
- **Found during:** Task 2 full suite run (test_technology_extractor.py)
- **Issue:** Tests raised `RuntimeError("Embedding failed")` but catch only had `ValueError, KeyError, OSError`
- **Fix:** Added `RuntimeError` to both exception tuples in `technology_extractor.py`
- **Files modified:** `src/para_files/utils/technology_extractor.py`
- **Commit:** fff7cc6

## Verification

```
PASS: No BLE001 suppressions in src/para_files/utils/
PASS: pandoc.py has ALLOWED_EXTENSIONS frozenset
PASS: chm_metadata.py has .chm suffix check before subprocess
PASS: exiftool.py has no extension restriction (per user decision)
PASS: tests/conftest.py has macos_only marker definition
PASS: tests/test_ocr.py uses @macos_only on integration tests
PASS: macos_only registered in pyproject.toml markers
All 400+ tests pass (excluding pre-existing isbn_lookup pkg_resources failures)
```

## Self-Check: PASSED

- SUMMARY.md exists at `.planning/phases/08-foundation-hardening/08-02-SUMMARY.md`
- Commit a83015e exists (Task 1: exception narrowing + subprocess validation)
- Commit fff7cc6 exists (Task 2: platform markers + exception coverage fixes)
- Zero BLE001 suppressions in all 10 utility files
- All tests pass (except pre-existing isbn_lookup failures)
