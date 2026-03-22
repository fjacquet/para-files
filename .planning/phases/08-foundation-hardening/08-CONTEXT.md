# Phase 8: Foundation Hardening — Context

**Created:** 2026-03-22
**Phase goal:** The codebase handles errors explicitly — no broad exception swallowing, no silent placeholder failures, no unused dependencies polluting the environment.

## Decisions

### 1. Error Strictness (BLE001 Remediation)

**43 `except Exception` sites across 19 files.** Tiered policy by module role:

| Module role | Policy | Example |
|-------------|--------|---------|
| **Classifiers** (pipeline.py, llm_classifier.py) | Catch specific types (ValueError, TimeoutError, ConnectionError, etc.) + re-raise unknown | `except (ValueError, json.JSONDecodeError) as e:` |
| **External tools** (exiftool, pandoc, chm_metadata, ocr) | Catch specific types + log warning + return empty result | `except subprocess.SubprocessError as e: logger.warning(...); return None` |
| **Content extractors** (file_utils: PDF, DOCX, XLSX, etc.) | Same as external tools — warn + return empty | Non-critical; pipeline continues without content |
| **CLI parallel workers** (inbox_cmd, move_cmd, scan_cmd) | **Keep broad `except Exception`** at worker boundary | These are fault isolation boundaries; re-raising kills the batch |
| **isbn_lookup.py** | Catch specific types per API call | Distinguish network errors from parse errors |

**Why:** Classifiers are pipeline-critical and should surface unexpected failures. Tools/extractors are best-effort — a failure shouldn't block classification. CLI workers need broad catch to prevent one file from killing a batch of 800.

### 2. Placeholder Resolution Policy

**Current behavior:** `clean_unreplaced_placeholders()` silently strips `{year}`, `{issuer}`, `{technology}` from paths.

**New policy:**
- **Required placeholders:** `{issuer}`, `{technology}` — if unresolved, **reject the classification** (return None) and log a warning
- **Optional placeholder:** `{year}` — can be stripped cleanly (paths are valid without year)

**Why:** A path like `2_Areas/Assurance//` (empty issuer) is worse than no classification. Year is genuinely optional — many document types don't need it.

**Affected files:** `rules_engine.py:255`, `semantic_classifier.py:89`, `taxonomy_classifier.py:505`

### 3. Subprocess Safety (Extension Allowlist)

**Validate file extensions before spawning subprocess calls.** Per-tool allowlists:

| Tool | Allowed extensions | Reject behavior |
|------|-------------------|-----------------|
| **pandoc** | `.docx`, `.doc`, `.rtf`, `.odt`, `.html`, `.epub` | Log warning, return None |
| **exiftool** | All extensions accepted | No restriction (metadata tool) |
| **chm_metadata** | `.chm` only | Log warning, return None |

**5 subprocess sites** with `noqa: S603`: `chm_metadata.py:60`, `file_utils.py:529`, `exiftool.py:260`, `pandoc.py:107`, `pandoc.py:206`

**Why:** Prevents misuse and limits attack surface. Exiftool is safe for all file types by design.

### 4. Dependency Removal — DEFERRED

**Decision:** Keep `semantic-router` dependency as-is.

`semantic-router` provides `DenseEncoder` base class used by `OllamaEncoder`. While it's a thin Pydantic `BaseModel` wrapper, the user opted to keep the dependency in place. **DEP-01 removed from Phase 8 scope.**

## Code Context

### BLE001 sites by file (43 total)

```
pipeline.py (1), llm_classifier.py (1), ollama_encoder.py (3)
isbn_lookup.py (6), pandoc.py (2), ocr.py (2), chm_metadata.py (4)
file_utils.py (7), pdf_metadata.py (4), epub_metadata.py (2)
exiftool.py (1), geolocation.py (1), technology_extractor.py (2)
classify_cmd.py (2), scan_cmd.py (1), move_cmd.py (2), inbox_cmd.py (1), bookstore_cmd.py (1)
```

### Placeholder resolution call sites

- `rules_engine.py:255` — calls `clean_unreplaced_placeholders()`
- `semantic_classifier.py:89` — calls `clean_unreplaced_placeholders()`
- `taxonomy_classifier.py:505` — calls `clean_unreplaced_placeholders()`

### Subprocess call sites

- `chm_metadata.py:60` — `subprocess.run(["chm_lib", ...])`
- `file_utils.py:529` — `subprocess.run(["pandoc", ...])`
- `exiftool.py:260` — `subprocess.run(["exiftool", ...])`
- `pandoc.py:107` — `subprocess.run(["pandoc", ...])`
- `pandoc.py:206` — `subprocess.run(["pandoc", ...])`

## Scope Changes

- **DEP-01 removed:** Keep semantic-router dependency (user decision)
- **DEP-02 retained:** macOS OCR test isolation with platform skip markers

## Next Steps

Run `/gsd:plan-phase 8` to create the execution plan.
