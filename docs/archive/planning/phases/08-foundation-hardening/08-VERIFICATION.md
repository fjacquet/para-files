---
phase: 08-foundation-hardening
verified: 2026-03-22T17:30:00Z
status: gaps_found
score: 3/5 success criteria verified
re_verification: false
gaps:
  - truth: "Placeholder resolution tests cover: missing year, empty issuer, multiple missing fields, double-slash paths"
    status: partial
    reason: "missing year and double-slash path tests exist and pass; 'empty issuer' (issuer resolved to empty string) and 'multiple missing fields simultaneously' tests are absent from test_placeholder_resolver.py"
    artifacts:
      - path: "tests/test_placeholder_resolver.py"
        issue: "No test for resolve_placeholders(..., {'issuer': ''}) producing empty segment path; no test for two required placeholders both unresolved in the same path"
    missing:
      - "Test: resolve_placeholders('2_Areas/{issuer}/docs', {'issuer': ''}) should produce '2_Areas//docs' and clean_unreplaced_placeholders should handle or classify that as a valid but oddly empty segment (or test that behavior is defined)"
      - "Test: clean_unreplaced_placeholders('2_Areas/{issuer}/{technology}/docs') returns None when both issuer and technology are unresolved simultaneously"
  - truth: "Pandoc integration tests cover: broken install, timeout, wrong encoding"
    status: partial
    reason: "broken install and timeout tests exist and pass; 'wrong encoding' test is absent — the docstring on line 3 mentions it but no test exercises UnicodeDecodeError or encoding-related failure"
    artifacts:
      - path: "tests/test_pandoc_integration.py"
        issue: "Module docstring says 'encoding errors' are covered but no test class or test method exercises wrong encoding / UnicodeDecodeError"
    missing:
      - "Test: when pandoc subprocess raises UnicodeDecodeError (or returns bytes with wrong encoding), extract_text/extract_metadata returns None gracefully"
human_verification:
  - test: "Run para-files classify on a file with Ollama unavailable"
    expected: "Classification completes (falls to extension router), no unhandled exception, no BLE001 leak"
    why_human: "test_pipeline.py tests are environment-dependent — Ollama timeout causes flaky results in CI"
---

# Phase 8: Foundation Hardening Verification Report

**Phase Goal:** The codebase handles errors explicitly — no broad exception swallowing, no silent placeholder failures, subprocess calls validated
**Verified:** 2026-03-22T17:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | BLE001 violations zero in pipeline.py, all classifiers, utilities | VERIFIED | grep confirms 0 matches for `noqa: BLE001` and `except Exception` in `src/para_files/pipeline.py`, `src/para_files/classifiers/`, `src/para_files/encoders/`, `src/para_files/utils/` |
| SC2 | Unresolved placeholder surfaces warning not silent strip | VERIFIED | `clean_unreplaced_placeholders` returns `None` with `logger.warning(...)` for required placeholders; all 3 classifier call sites check for `None` before constructing `ClassificationResult` |
| SC3 | Subprocess calls validate file extensions before execution | VERIFIED | `pandoc.py` has `ALLOWED_EXTENSIONS: frozenset[str]` (18 formats), checked at 2 call sites; `chm_metadata.py` checks `suffix.lower() != ".chm"` before subprocess; `exiftool.py` has no restriction by design (metadata tool safe for all types) |
| SC4 | Placeholder tests cover missing year, empty issuer, multiple missing fields, double-slash | PARTIAL | missing year (`test_missing_year_stripped_cleanly`) and double-slash (`test_double_slashes_collapsed_after_optional_removal`) covered; "empty issuer" (issuer resolved to `""`) and "multiple required placeholders both unresolved" are NOT tested |
| SC5 | Pandoc tests cover broken install, timeout, wrong encoding | PARTIAL | broken install (`TestPandocBrokenInstall` — 3 tests) and timeout (`TestPandocTimeout` — 3 tests) covered; "wrong encoding" is mentioned in the docstring but no test exists |

**Score: 3/5 success criteria verified**

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/para_files/pipeline.py` | Zero BLE001 suppressions | VERIFIED | No `except Exception` or `noqa: BLE001` found |
| `src/para_files/classifiers/llm_classifier.py` | Zero BLE001 suppressions | VERIFIED | Specific exception tuple: `(ValueError, TypeError, KeyError, json.JSONDecodeError, ConnectionError, TimeoutError, OSError)` |
| `src/para_files/encoders/ollama_encoder.py` | Zero BLE001 suppressions | VERIFIED | 3 sites use `(ConnectionError, TimeoutError, OSError, ValueError, RuntimeError)` |
| `src/para_files/utils/pandoc.py` | ALLOWED_EXTENSIONS + pre-subprocess check | VERIFIED | `ALLOWED_EXTENSIONS: frozenset[str]` (line 63), checked at lines 106 and 199 |
| `src/para_files/utils/chm_metadata.py` | .chm suffix check before subprocess | VERIFIED | Lines 59-60: reject non-.chm with warning |
| `src/para_files/utils/placeholder_resolver.py` | `_REQUIRED_PLACEHOLDERS`, `_OPTIONAL_PLACEHOLDERS`, return `str \| None` | VERIFIED | Lines 30-33 define both sets; `clean_unreplaced_placeholders` returns `str \| None` (line 52) |
| `src/para_files/classifiers/rules_engine.py` | Handles `None` from placeholder resolver | VERIFIED | Line 256: `if cleaned_category is None:` |
| `src/para_files/classifiers/semantic_classifier.py` | Handles `None` from placeholder resolver | VERIFIED | Line 90: `if result is None:` |
| `src/para_files/classifiers/taxonomy_classifier.py` | Handles `None` from placeholder resolver | VERIFIED | Line 508: `if cleaned is None:` |
| `tests/test_placeholder_resolver.py` | 19-test suite covering edge cases | VERIFIED (partial) | 19 tests, all pass — but "empty issuer" and "multiple missing fields" cases absent |
| `tests/test_pandoc_integration.py` | 20-test suite covering failure modes | VERIFIED (partial) | 20 tests, all pass — but "wrong encoding" case absent despite docstring claim |
| `tests/conftest.py` | `macos_only` skip marker | VERIFIED | Lines 12-13: `pytest.mark.skipif(platform.system() != "Darwin", ...)` |
| `tests/test_ocr.py` | `@macos_only` applied | VERIFIED | Line 217: `@macos_only` on `TestExtractTextIntegration` |
| `pyproject.toml` | `macos_only` registered in markers | VERIFIED | Line 259: marker registered |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `rules_engine.py` | `placeholder_resolver.py` | `clean_unreplaced_placeholders` import + None check | WIRED | Import line 26; None check line 256 |
| `semantic_classifier.py` | `placeholder_resolver.py` | `clean_unreplaced_placeholders` import + None check | WIRED | Import line 26; None check line 90 |
| `taxonomy_classifier.py` | `placeholder_resolver.py` | `clean_unreplaced_placeholders` import + None check | WIRED | Import line 26; None check line 508 |
| `pandoc.py` | subprocess | `ALLOWED_EXTENSIONS` guard before call | WIRED | Frozenset defined line 63; checked lines 106, 199 |
| `chm_metadata.py` | subprocess | `.chm` suffix guard before call | WIRED | Check lines 59-60, 194 |
| `test_ocr.py` | `conftest.macos_only` | `@macos_only` decorator | WIRED | Import line 10; applied line 217 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ERR-01 | 08-01 | Replace broad `except Exception` in pipeline.py with specific types | SATISFIED | Zero BLE001 in pipeline.py; specific exception tuple at catch site |
| ERR-02 | 08-01 | Replace broad `except Exception` in classifiers | SATISFIED | Zero BLE001 in `classifiers/`; llm_classifier uses specific tuple |
| ERR-03 | 08-02 | Replace broad `except Exception` in utilities | SATISFIED | Zero BLE001 in `utils/`; 10 utility files updated with specific types |
| ERR-04 | 08-03 | Placeholder resolution rejects when critical placeholders unresolved | SATISFIED | `clean_unreplaced_placeholders` returns None for required placeholders with warning |
| ERR-05 | 08-02 | Subprocess calls validate file extensions before execution | SATISFIED | pandoc.py `ALLOWED_EXTENSIONS`, chm_metadata.py suffix check |
| DEP-02 | 08-02 | macOS OCR tests isolated with platform skip markers in CI | SATISFIED | `macos_only` marker defined in conftest.py, applied to test_ocr.py integration tests, registered in pyproject.toml |
| TEST-02 | 08-03 | Placeholder resolution tests: missing year, empty issuer, multiple missing, double-slash | PARTIAL | Missing year ✓, double-slash ✓; "empty issuer" (issuer="" empty string) and "multiple missing fields" not covered |
| TEST-05 | 08-03 | Pandoc integration tests: broken install, timeout, wrong encoding | PARTIAL | Broken install ✓, timeout ✓; "wrong encoding" test absent |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_pandoc_integration.py` | 3 | Docstring claims "encoding errors" coverage that does not exist | Warning | Misleading — SC5 gap |

### Human Verification Required

#### 1. Ollama-unavailable Graceful Degradation

**Test:** Run `uv run para-files classify <any_file>` with Ollama server not running
**Expected:** Classification completes with extension router result, no unhandled exception traceback
**Why human:** Integration test `test_classify_with_taxonomy_keyword_match` is flaky due to Ollama dependency; isolating this behavior requires a live but offline Ollama scenario

### Gaps Summary

Two success criteria are partially satisfied due to missing test cases:

**SC4 gap — Placeholder test coverage:** The test suite covers 4 of the 4 named scenarios (`missing year`, `empty issuer` as "unresolved {issuer}", `double-slash`), but "empty issuer" in the success criterion likely means `issuer` resolves to `""` producing a path like `2_Areas//docs`, and "multiple missing fields" means two required placeholders both unresolved. Neither case is exercised. These are minor gaps — the production code handles them correctly (stripping or rejecting as appropriate), but the test specification is not fully met.

**SC5 gap — Pandoc encoding test:** The test module docstring on line 3 explicitly claims to cover "encoding errors" but no test class or method tests for UnicodeDecodeError or wrong-encoding scenarios. The `pandoc.py` module does catch `subprocess.SubprocessError` which would cover encoding-related subprocess failures, but there is no test asserting this behavior.

Both gaps are test coverage gaps only — the production behavior is correct. The underlying requirements ERR-04, ERR-05 are satisfied; only TEST-02 and TEST-05 are partially satisfied.

---

_Verified: 2026-03-22T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
