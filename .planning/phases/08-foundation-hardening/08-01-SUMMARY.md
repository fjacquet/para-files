---
phase: 08-foundation-hardening
plan: 01
subsystem: classification-pipeline
tags: [exception-handling, reliability, error-surfacing, BLE001]
dependency_graph:
  requires: []
  provides: [specific-exception-handling-pipeline, specific-exception-handling-llm, specific-exception-handling-encoder]
  affects: [pipeline.py, llm_classifier.py, ollama_encoder.py]
tech_stack:
  added: []
  patterns: [specific-exception-types, explicit-error-logging]
key_files:
  created: []
  modified:
    - src/para_files/pipeline.py
    - src/para_files/classifiers/llm_classifier.py
    - src/para_files/encoders/ollama_encoder.py
    - tests/test_pipeline.py
decisions:
  - id: EXC-01
    summary: "Encoder fallback chain uses (ConnectionError, TimeoutError, OSError, ValueError, RuntimeError) to cover litellm API errors and data issues"
  - id: EXC-02
    summary: "test_classifier_exception_handling updated to raise ValueError instead of bare Exception to reflect narrowed handler"
metrics:
  duration: "~8 minutes"
  completed: "2026-03-22"
  tasks_completed: 2
  files_modified: 4
---

# Phase 08 Plan 01: Exception Narrowing (BLE001 Elimination) Summary

**One-liner:** Replaced three bare `except Exception` (BLE001) suppressions in pipeline, LLM classifier, and Ollama encoder with specific exception type tuples to surface unexpected failures.

## What Was Done

Eliminated all `# noqa: BLE001` suppressions from the three pipeline-critical files by replacing broad `except Exception` clauses with precisely-typed exception tuples matching what each try-block's operations can actually raise.

## Tasks Completed

| Task | Name | Commit | Files Modified |
|------|------|--------|----------------|
| 1 | Narrow exceptions in pipeline.py and llm_classifier.py | 9732a86 | pipeline.py, llm_classifier.py, tests/test_pipeline.py |
| 2 | Narrow exceptions in ollama_encoder.py | 623b1b4 | ollama_encoder.py |

## Changes Made

### pipeline.py (line 274)

Added `import json` to support `json.JSONDecodeError` in the exception tuple.

Replaced:

```python
except Exception:  # noqa: BLE001
    logger.exception("Classifier {} failed", classifier.name)
```

With:

```python
except (ValueError, TypeError, KeyError, AttributeError, ConnectionError, TimeoutError, OSError, json.JSONDecodeError, RuntimeError) as e:
    logger.exception("Classifier {} failed: {}", classifier.name, e)
```

### llm_classifier.py (line 171)

Replaced in `classify()` method:

```python
except Exception:  # noqa: BLE001
    logger.exception("LLM classification failed")
```

With:

```python
except (ValueError, TypeError, KeyError, json.JSONDecodeError, ConnectionError, TimeoutError, OSError) as e:
    logger.exception("LLM classification failed: {}", e)
```

### ollama_encoder.py (3 sites)

All three `except Exception` clauses replaced:

- Fallback loop in `_encode_single`: `except (ConnectionError, TimeoutError, OSError, ValueError, RuntimeError) as e`
- Last-resort 100-char attempt: same types
- Batch retry in `__call__`: same types

## Verification

```
grep -c "noqa: BLE001" pipeline.py llm_classifier.py ollama_encoder.py
# → 0 matches in all three files

uv run pytest tests/test_pipeline.py tests/test_classifiers.py tests/test_encoders.py
# → 50 passed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_classifier_exception_handling to use ValueError**

- **Found during:** Task 1 verification
- **Issue:** Test raised bare `Exception("Test error")` which is no longer caught by narrowed handler, causing test failure
- **Fix:** Changed `mock_classifier.classify.side_effect = Exception("Test error")` to `ValueError("Test error")` — matches the new specific exception list and correctly tests the graceful-fallback behavior
- **Files modified:** tests/test_pipeline.py
- **Commit:** 9732a86

## Self-Check: PASSED

- [x] `src/para_files/pipeline.py` — modified, committed in 9732a86
- [x] `src/para_files/classifiers/llm_classifier.py` — modified, committed in 9732a86
- [x] `src/para_files/encoders/ollama_encoder.py` — modified, committed in 623b1b4
- [x] `tests/test_pipeline.py` — updated, committed in 9732a86
- [x] 50 tests pass (test_pipeline.py + test_classifiers.py + test_encoders.py)
- [x] Zero BLE001 suppressions in all three target files
