---
phase: 09-llm-service-reliability
plan: "02"
subsystem: classifiers
tags: [llm, parsing, tdd, reliability, coercion, url-decode, allowlist]
dependency_graph:
  requires: []
  provides: [hardened-llm-response-parsing, confidence-coercion, category-allowlist]
  affects: [src/para_files/classifiers/llm_classifier.py, tests/test_llm_classifier.py]
tech_stack:
  added: [urllib.parse.unquote]
  patterns: [JSON-first with regex fallback, static coercion method, allowlist validation]
key_files:
  created:
    - tests/test_llm_classifier.py
  modified:
    - src/para_files/classifiers/llm_classifier.py
decisions:
  - "_coerce_confidence is a @staticmethod to make it easily testable and emphasize it has no side effects"
  - "JSON-first strategy (json.loads on full text) before regex fallback — handles clean JSON responses efficiently"
  - "Allowlist check uses prefix matching (vc.split('{')[0]) to support template categories like 3_Resources/documentation/{technology}"
  - "Pre-existing test failures in test_circuit_breaker.py and test_isbn_lookup.py are out of scope (Ollama/urllib mock issues)"
metrics:
  duration: "~10 minutes"
  completed: "2026-03-22"
  tasks_completed: 2
  files_changed: 2
---

# Phase 09 Plan 02: LLM Response Parsing Hardening Summary

**One-liner:** JSON-first LLM response parsing with string/percentage/integer confidence coercion, URL-decode, and category allowlist validation.

## Objective

Harden LLM response parsing to prevent silent misclassification from malformed LLM output. Addressed string confidence values, URL-encoded category paths, and hallucinated categories outside the allowlist.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create LLM response parsing tests (RED) | 4e5a2dc | tests/test_llm_classifier.py |
| 2 | Update LLM classifier with all improvements (GREEN) | 991a67c | src/para_files/classifiers/llm_classifier.py |

## Changes Made

### src/para_files/classifiers/llm_classifier.py

1. **New import:** `from urllib.parse import unquote` for URL-decoding category paths.

2. **`__init__` update:** Added `self._valid_categories = set(valid_categories or [])` to store the allowlist for use in `_sanitize_category`.

3. **New `_coerce_confidence()` static method:** Handles all LLM confidence formats:
   - `0.8` (float) → `0.8`
   - `"0.8"` (string float) → `0.8`
   - `"80%"` (percentage string) → `0.8`
   - `"80"` (integer-as-string) → `0.8`
   - Values > 1.0 are divided by 100

4. **Rewritten `_parse_response()`:** JSON-first strategy:
   - Empty string returns `None` immediately
   - Strip markdown code blocks first
   - **Strategy 1:** `json.loads(text)` on full text (fast path for clean responses)
   - **Strategy 2:** Regex extraction `{[^{}]*"category"[^{}]*}` fallback for chatty responses
   - Uses `_coerce_confidence()` instead of `float()` for confidence parsing

5. **Updated `_sanitize_category()`:**
   - Calls `unquote(category)` to decode URL-encoded paths (`C%2B%2B` → `C++`)
   - Fixed Windows path check with explicit `len(category) > 1` guard
   - Allowlist check: rejects categories whose prefix doesn't match any valid category

### tests/test_llm_classifier.py

New test file with 17 test cases covering:
- Valid float confidence
- String confidence (`"0.85"`)
- Percentage confidence (`"80%"`)
- Integer-as-string confidence (`"80"`)
- Trailing spaces in category
- Nested JSON (text before/after JSON object)
- Markdown-wrapped JSON (triple backticks)
- Incomplete JSON (returns None, no crash)
- Empty string (returns None)
- Chatty LLM response (preamble before JSON)
- URL-encoded path (`C%2B%2B` → `C++`)
- Allowlist match accepted
- Allowlist rejection (category not in list)
- No-allowlist accepts any valid PARA prefix
- Absolute path rejection
- Windows path rejection
- Pipeline short-circuit (LLM-03): first classifier match stops iteration

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test using MagicMock as Confidence value**
- **Found during:** Task 1
- **Issue:** `test_pipeline_short_circuit` passed `MagicMock()` as `confidence=` to `ClassificationResult`, which Pydantic rejects (requires `Confidence` model instance)
- **Fix:** Changed to `Confidence(value=0.9, source=ClassificationSource.RULES_ENGINE)`
- **Files modified:** tests/test_llm_classifier.py
- **Commit:** 4e5a2dc

**2. [Rule 2 - Critical] Patched `_ensure_initialized` in pipeline short-circuit test**
- **Found during:** Task 1
- **Issue:** Pipeline `classify()` calls `_ensure_initialized()` which tries to load actual classifiers from config; test needs to bypass this
- **Fix:** Used `patch.object(ClassificationPipeline, "_ensure_initialized")` context manager
- **Files modified:** tests/test_llm_classifier.py
- **Commit:** 4e5a2dc

**3. [Rule 3 - Blocking] Fixed 5 ruff lint errors in production code**
- **Found during:** Task 2 verification
- **Issues:** E501 (line too long), SIM102 (nested if), ANN401 (Any type), C901 (complexity), RUF100 (unused noqa)
- **Fix:** Reformatted exception tuple, extracted `is_windows_path` variable, flattened allowlist check, added targeted noqa comments
- **Files modified:** src/para_files/classifiers/llm_classifier.py
- **Commit:** 991a67c

## Pre-existing Failures (Out of Scope)

Logged to deferred-items.md — not caused by this plan:

- `test_circuit_breaker.py::TestCheckOllamaHealth::test_returns_false_on_connection_error` — urllib mock issue
- `test_isbn_lookup.py::TestLookupIsbn::test_lookup_enrichment_failures` — Exception mock not caught
- `test_pipeline.py` Ollama timeout failures — no Ollama server in test environment

## Requirements Addressed

- **LLM-03:** Pipeline short-circuit verified by test (already working)
- **LLM-04:** String/percentage/integer confidence coercion implemented and tested
- **LLM-05:** Category allowlist validation implemented (with prefix matching for template paths)
- **TEST-04:** Comprehensive LLM response format edge case tests (17 tests)

## Self-Check: PASSED
