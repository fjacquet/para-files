# Codebase Concerns

**Analysis Date:** 2025-03-22

## Tech Debt

**Broad Exception Handling (BLE001 suppression):**
- Issue: Multiple locations use bare `except Exception` with `# noqa: BLE001` suppression
- Files: `src/para_files/pipeline.py` (line 273), `src/para_files/classifiers/llm_classifier.py` (line 171), `src/para_files/cli/scan_cmd.py` (line 81), `src/para_files/encoders/ollama_encoder.py` (lines 83, 92), `src/para_files/utils/pandoc.py` (line 120), `src/para_files/utils/ocr.py` (lines 183, 297), `src/para_files/utils/isbn_lookup.py` (line 78), and others
- Impact: Suppresses legitimate linting warnings that could indicate insufficient error handling. Makes it harder to understand and trace failures. Can hide unexpected exceptions during development.
- Fix approach: Gradually replace with specific exception types. Start with classifiers (pipeline.py) and external service calls (ocr.py, pandoc.py, isbn_lookup.py). Catch `TimeoutExpired`, `FileNotFoundError`, `OSError`, `ImportError` explicitly where applicable.

**Placeholder Resolution Cleanup:**
- Issue: Multiple classifiers implement pattern resolution with `clean_unreplaced_placeholders()` fallback
- Files: `src/para_files/classifiers/rules_engine.py` (line 254), `src/para_files/classifiers/semantic_classifier.py` (line 89), `src/para_files/classifiers/taxonomy_classifier.py` (line 505)
- Impact: Placeholders like `{year}`, `{issuer}`, `{technology}` are removed if not resolved, leading to path like `3_Resources/documentation/` (missing technology). Silent failures make debugging harder.
- Fix approach: Implement placeholder validation before cleaning. Log warning when placeholders are removed. Consider requiring all placeholders to be resolvable or fail classification gracefully.

**macOS Vision Framework Dependency:**
- Issue: OCR features require Apple Vision Framework (macOS-only), but cross-platform execution is not tested
- Files: `src/para_files/utils/ocr.py` (lines 59-64, imports Cocoa/Quartz/Vision), `src/para_files/pipeline.py` (uses extract_metadata)
- Impact: On non-macOS systems, OCR gracefully returns `None`, but this untested code path could mask errors. Vision Framework import directly hardcodes macOS requirement.
- Fix approach: Add platform detection in CI/CD. Create separate test suite for macOS-only features. Document clearly that OCR is macOS-only.

**pyobjc Framework Dependencies:**
- Issue: Three pyobjc packages in dependencies for macOS-only Vision Framework
- Files: `pyproject.toml` (lines 29-31): `pyobjc-framework-vision>=12.1`, `pyobjc-framework-quartz>=12.1`, `pyobjc-framework-cocoa>=12.1`
- Impact: Installation fails on Linux/Windows. Users on non-macOS must work around dependency errors or install only core features.
- Fix approach: Make pyobjc packages optional dependencies (already handled with `[ocr]` extra). Update CI/CD to skip OCR tests on non-macOS runners. Add setup instructions for platform-specific installation.

## Known Bugs

**LLM Response Parsing Complexity:**
- Symptoms: LLM classifier uses regex to extract JSON from markdown code blocks and nested braces
- Files: `src/para_files/classifiers/llm_classifier.py` (lines 290-295)
- Trigger: LLM returns JSON with nested braces, markdown formatting, or escaped quotes
- Workaround: The fallback regex `\{[^{}]*"category"[^{}]*\}` only matches single-level braces; complex responses fail silently and return `None`
- Fix approach: Use proper JSON parsing with error recovery. Try parsing directly, then fall back to regex extraction if invalid. Add test cases for malformed LLM responses.

**ISBN Lookup Service Failures Silent:**
- Symptoms: ISBN lookup tries multiple services (openl, wiki, goob) but fails gracefully
- Files: `src/para_files/utils/isbn_lookup.py` (lines 72-80)
- Trigger: isbnlib service timeout, network error, or invalid ISBN
- Workaround: Returns `None` on all errors; no distinction between "invalid ISBN" and "service unavailable"
- Fix approach: Add retry logic with exponential backoff. Return partial BookInfo even if metadata lookup fails (e.g., if ISBN itself is valid). Add metrics for service failure rates.

**Placeholder Resolution in Taxonomy Paths:**
- Symptoms: Paths like `4_Archives/{year}/` become `4_Archives/` if year extraction fails
- Files: `src/para_files/classifiers/taxonomy_classifier.py` (lines 488-505), `clean_unreplaced_placeholders()` utility
- Trigger: Document has no year metadata and no year in content
- Workaround: Silently strips unresolved placeholders, creating overly broad categories
- Fix approach: Track which placeholders failed to resolve. Log warnings. Option: require certain placeholders (year) or fail classification instead of silently creating wrong paths.

## Security Considerations

**Subprocess Calls in File Utils:**
- Risk: Uses `subprocess.run(..., shell=False)` with `# noqa: S603` suppression for CLI tools
- Files: `src/para_files/utils/file_utils.py` (line 529 - exiftool call), `src/para_files/utils/pandoc.py` (line 107), `src/para_files/utils/chm_metadata.py` (line 60)
- Current mitigation: `shell=False` prevents shell injection. File paths are not user-controlled (files come from filesystem walking).
- Recommendations: Remove `# noqa: S603` and use `shlex.quote()` if file paths ever become user-input. Add input validation for file extensions before passing to subprocess. Consider using Python libraries instead of CLI tools where possible (e.g., pypdf instead of exiftool).

**LLM Output Validation:**
- Risk: LLM classifier sanitizes category paths but regex extraction could be bypassed by clever prompting
- Files: `src/para_files/classifiers/llm_classifier.py` (lines 250-274)
- Current mitigation: Validates path doesn't start with `/`, `~`, or contain `:\` (Windows paths). Rejects non-PARA prefixes.
- Recommendations: Add URL decoding check (could bypass validation with `%2F` or `%5C`). Test adversarial LLM responses. Consider allowlist instead of blocklist for PARA categories.

**External Service Availability:**
- Risk: Ollama/litellm embedding calls timeout at 15s, but no circuit breaker for degraded service
- Files: `src/para_files/config.py` (line 147 - timeout), `src/para_files/classifiers/semantic_classifier.py`, `src/para_files/encoders/ollama_encoder.py`
- Current mitigation: Graceful fallback to next classifier if timeout occurs.
- Recommendations: Implement circuit breaker pattern if Ollama fails 5+ times. Cache embeddings to avoid redundant calls. Add health check endpoint for Ollama availability.

## Performance Bottlenecks

**Content Truncation Inconsistency:**
- Problem: Multiple code paths truncate content to different lengths before processing
- Files: `src/para_files/encoders/ollama_encoder.py` (line 32 - 1000 chars, line 33 - 700 fallback), `src/para_files/classifiers/semantic_classifier.py` (line 33 - 2000 chars), `src/para_files/pipeline.py` (line 369 - 5000 chars for OCR rename)
- Cause: No centralized limit; each classifier/encoder uses its own truncation strategy
- Improvement path: Define MAX_CONTENT_CHARS in config, respect it consistently. Currently, semantic classifier processes 2000 chars while encoder truncates to 1000, creating inefficiency.

**File Hashing for Duplicate Detection:**
- Problem: `files_are_identical()` computes SHA256 for both files on every comparison
- Files: `src/para_files/mover.py` (lines 30-61)
- Cause: No caching of hash results; if file appears multiple times, hashing is repeated
- Improvement path: Cache hashes by file path + modification time. For move operations, compute hash once and reuse.

**Parallel Processing Executor Defaults:**
- Problem: Thread executor defaults to `max_workers` without limiting based on file count
- Files: `src/para_files/cli/scan_cmd.py` (line 115), `src/para_files/cli/move_cmd.py` (ThreadPoolExecutor usage)
- Cause: For small file counts (<5), threading overhead may exceed benefit
- Improvement path: Calculate optimal `max_workers = min(file_count, cpu_count())`. Skip threading entirely if file_count < 5.

**Ollama Encoder Fallback Chain:**
- Problem: Encoder tries 4 progressively truncated encodes on failure (1000→700→400→200→100 chars)
- Files: `src/para_files/encoders/ollama_encoder.py` (lines 74-94)
- Cause: If Ollama is down, exhausts all retries (4 API calls) before giving up
- Improvement path: Check Ollama availability once at startup. If down, skip semantic classifier entirely rather than retry on every file.

## Fragile Areas

**Book Detector Classification:**
- Files: `src/para_files/classifiers/book_detector.py` (728 lines)
- Why fragile: Complex multi-signal detection with many exclusion patterns. Financial documents, tax forms, insurance statements, and transport tickets all have ISBN-like numbers that can trigger false positives.
- Safe modification: Add new exclusion patterns at end of `FINANCIAL_EXCLUSION_PATTERNS`, `TAX_EXCLUSION_PATTERNS`, etc. Test thoroughly with French administrative documents (high false positive rate). Consider feature flags to disable book detection for specific patterns.
- Test coverage: Tests exist (`test_book_detector.py`) but don't cover all exclusion patterns. Missing tests for edge cases like invalid ISBNs (all zeros, check digit fails).

**Rules Engine Pattern Matching:**
- Files: `src/para_files/classifiers/rules_engine.py` (665 lines)
- Why fragile: Glob patterns from YAML are applied in order. A too-broad pattern early in the list can shadow more specific patterns. Date extraction uses hardcoded MIN_YEAR=1990, MAX_YEAR=2040.
- Safe modification: When adding routing rules, ensure more specific patterns come first. Test date extraction edge cases (1989, 2041, invalid dates like 1970). Use rule precedence documentation.
- Test coverage: Rules engine has tests but missing coverage for date extraction edge cases and pattern shadowing scenarios.

**Taxonomy Classifier with Placeholders:**
- Files: `src/para_files/classifiers/taxonomy_classifier.py` (638 lines)
- Why fragile: Placeholder resolution (`{year}`, `{issuer}`, `{technology}`) is spread across the classifier and utility function. If placeholder format changes, resolution breaks silently.
- Safe modification: Keep placeholder names in `KNOWN_PLACEHOLDERS` constant. Any new placeholders must be added there. Test that unresolved placeholders are stripped cleanly (no double slashes).
- Test coverage: Tests exist but don't cover all placeholder combinations. Missing: what if both year and issuer are missing? What if issuer contains slashes?

**LLM Classifier Response Parsing:**
- Files: `src/para_files/classifiers/llm_classifier.py` (341 lines)
- Why fragile: JSON extraction uses regex with multiple fallbacks. If LLM changes output format even slightly, parsing could fail silently and classifier returns None.
- Safe modification: When updating system prompt, test LLM output format. Add tests for each fallback path (markdown blocks, nested braces, escaped quotes). Consider stricter format requirements in system prompt.
- Test coverage: Some tests exist (`test_llm_classifier.py`) but missing: what if LLM returns confidence as string "0.9" instead of 0.9? What if category contains quotes or newlines?

**Reference Tree YAML Loading:**
- Files: `src/para_files/reference_tree.py`
- Why fragile: Uses `yaml.safe_load()` without schema validation. Invalid YAML structure silently fails or creates wrong routing_rules dict.
- Safe modification: Add Pydantic models for ReferenceTree YAML structure. Validate structure on load, fail fast if invalid. Currently errors are caught but logged at debug level.
- Test coverage: Tests exist but don't cover malformed YAML (missing `routing_rules` key, wrong types, duplicate rule names).

## Scaling Limits

**Threading Overhead for Small Batches:**
- Current capacity: ThreadPoolExecutor with default `max_workers`
- Limit: For <5 files, threading overhead (context switching, queue management) exceeds benefit
- Scaling path: Add adaptive worker pool sizing. Calculate optimal based on file count. Disable threading for <5 files.

**Embeddings Not Cached:**
- Current capacity: All embeddings computed per-request from Ollama
- Limit: For large repeated datasets, duplicate content re-computed repeatedly
- Scaling path: Implement optional embedding cache (Redis or SQLite). Hash content, check cache before calling Ollama. Invalidate on classifier config changes.

**YAML Reference Tree Size:**
- Current capacity: Entire routing_rules dict loaded into memory at startup
- Limit: If reference tree grows to thousands of rules, startup time and memory usage increase linearly
- Scaling path: Lazy-load rules only when needed. Index rules by type (extension, issuer, technology) for fast lookup.

**ISBN Lookup Service Dependency:**
- Current capacity: isbnlib tries 3 services in sequence (openl, wiki, goob)
- Limit: If services are slow or unavailable, book detection blocks for 30+ seconds per file
- Scaling path: Implement async ISBN lookups. Cache results by ISBN. Add timeout per service (not global). Consider local ISBN database instead of online services.

## Dependencies at Risk

**isbnlib Package:**
- Risk: External library with slow metadata service calls. If service goes down, book detection fails silently.
- Impact: Books aren't detected (fallback to rules engine or semantic classifier, lower confidence).
- Migration plan: Bundle offline ISBN database (flat file) as fallback. Or use Google Books API directly (faster, better control over timeouts). Or remove ISBN lookup entirely and rely on PDF metadata extraction.

**semantic-router Package:**
- Risk: Dependency for semantic classifier, but embeddings now come from Ollama, not MLX. semantic-router has minimal usage and adds complexity.
- Impact: If semantic-router breaks or becomes unmaintained, semantic classifier fails.
- Migration plan: Consider removing semantic-router dependency. Implement manual cosine similarity (10 lines of code). Current implementation in `src/para_files/classifiers/semantic_classifier.py` already computes similarity manually; semantic-router isn't actively used.

**litellm Package:**
- Risk: Wrapper around multiple LLM providers. If litellm API changes or has bugs, both embedding and LLM fallback break.
- Impact: Semantic and LLM classifiers depend on litellm. If litellm fails, pipeline falls back to rules engine + extension router.
- Migration plan: Pin litellm version strictly. Monitor changelogs. Consider thin wrapper to allow swapping providers. Currently uses Ollama directly, so downgrade risk is low.

**pyobjc Packages (macOS):**
- Risk: Python bindings to Apple frameworks. Break on macOS version changes or when Apple deprecates Vision/Quartz APIs.
- Impact: OCR fails on newer macOS versions.
- Migration plan: Monitor Apple framework changes. Keep pyobjc up-to-date. Test on multiple macOS versions in CI. Consider alternative OCR library (tesseract, pytesseract) as fallback.

## Missing Critical Features

**No Dry-Run Mode Validation:**
- Problem: Dry-run shows what would happen but doesn't validate the entire operation (e.g., permission issues). File might appear moveable in dry-run but fail on actual move.
- Blocks: Users can't be 100% confident in batch operations before executing.
- Fix: Execute dry-run by actually copying files to temp dir, then delete. Or run permission checks + simulate file size checks.

**No Batch Rollback:**
- Problem: If move operation fails halfway through a batch, no rollback mechanism exists.
- Blocks: Users can't safely move many files at once.
- Fix: Implement transaction-like behavior. On first failure, stop and offer to rollback previous moves. Or use file versioning (keep copies of moved files until batch completes).

**No Incremental Learning from User Corrections:**
- Problem: `learner.py` exists but feedback isn't integrated into classifier pipeline
- Blocks: System can't improve over time based on user corrections.
- Fix: Integrate FeedbackTracker into classification pipeline. Use feedback to retrain or weight classifiers differently. Add confidence adjustment based on historical correction rates.

**No Category Aliases or Synonyms:**
- Problem: PARA paths are exact. If user later changes folder structure, old classifications become invalid.
- Blocks: Can't refactor PARA structure without re-classifying everything.
- Fix: Add alias support to reference tree. Let users map old categories to new ones. Patch old classifications on load.

## Test Coverage Gaps

**Untested Classifier Combinations:**
- What's not tested: Pipeline initializes classifiers in specific order. Tests don't verify what happens if classifier order changes or if certain classifiers are disabled.
- Files: `src/para_files/pipeline.py` (classifier initialization order), but tests don't disable classifiers selectively
- Risk: Changing classifier priority could break existing classifications silently (tests wouldn't catch it).
- Priority: High - classifier order is critical to deterministic behavior.

**Missing Edge Cases in Book Detector:**
- What's not tested: Invalid ISBNs (check digit fails), all-zero ISBNs, ISBN-like numbers in financial documents (IBAN with ISBN pattern)
- Files: `src/para_files/classifiers/book_detector.py` (exclusion patterns), `tests/test_book_detector.py`
- Risk: Financial documents could be misclassified as books if exclusion patterns miss edge cases.
- Priority: High - false positives are worse than false negatives for book detection.

**No Tests for Placeholder Resolution Failures:**
- What's not tested: What happens when `{year}` can't be extracted? When `{issuer}` is empty? Multiple missing placeholders?
- Files: `src/para_files/utils/placeholder_resolver.py`, `src/para_files/classifiers/taxonomy_classifier.py`
- Risk: Silent failures create wrong paths like `3_Resources/documentation//` (double slash).
- Priority: Medium - currently handled with cleanup, but fragile.

**Concurrent Threading Under Load:**
- What's not tested: What if classifier threads crash or timeout under concurrent file processing?
- Files: `src/para_files/cli/scan_cmd.py` (line 115), `src/para_files/cli/move_cmd.py` (ThreadPoolExecutor)
- Risk: Thread crashes could be silent or leave partial results.
- Priority: Medium - threading is used but not stress-tested.

**LLM Response Format Variations:**
- What's not tested: LLM returns confidence as string, category with trailing spaces, nested JSON, or incomplete JSON
- Files: `src/para_files/classifiers/llm_classifier.py` (lines 276-341)
- Risk: Parsing fails silently on valid-but-unexpected formats.
- Priority: Medium - LLM is unpredictable and current parsing is regex-based (fragile).

**Pandoc Integration Failures:**
- What's not tested: What if pandoc is installed but broken? What if it hangs despite timeout? What if output encoding is wrong?
- Files: `src/para_files/utils/pandoc.py`
- Risk: Silent failures return empty content, causing wrong classifications.
- Priority: Low - graceful fallback exists, but coverage is incomplete.

---

*Concerns audit: 2025-03-22*
