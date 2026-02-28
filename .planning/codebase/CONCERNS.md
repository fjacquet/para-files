# Codebase Concerns

**Analysis Date:** 2026-02-28

## Tech Debt

**Broad Exception Handling with noqa Suppressions:**

- Issue: Widespread use of bare `except Exception` blocks with `# noqa: BLE001` suppressions across critical paths, masking potential bugs
- Files: `src/para_files/classifiers/mlx_llm_classifier.py`, `src/para_files/utils/isbn_lookup.py`, `src/para_files/sutils/pdf_metadata.py`, `src/para_files/utils/exiftool.py`, `src/para_files/utils/pandoc.py`, `src/para_files/pipeline.py`, `src/para_files/cli/scan_cmd.py`, `src/para_files/cli/classify_cmd.py`, `src/para_files/cli/move_cmd.py`, `src/para_files/cli/bookstore_cmd.py`
- Impact: Makes debugging harder, hides unexpected failures, reduces observability. A single noqa suppression is reasonable; this pattern is applied 20+ times across the codebase
- Fix approach: Categorize exceptions by type (timeout, API unavailable, invalid format) and handle each appropriately. Create specific exception types for classifiable errors. Reserve bare Exception for true fallback cases with explicit logging

**Placeholder Cleanup Pattern:**

- Issue: Multiple classifiers independently implement placeholder cleanup logic (`{year}`, `{issuer}`, `{location}`) rather than using a centralized utility
- Files: `src/para_files/classifiers/rules_engine.py` (lines 255, 293, 314), `src/para_files/classifiers/semantic_classifier.py` (line 88), `src/para_files/classifiers/taxonomy_classifier.py` (line 504)
- Impact: Duplication increases maintenance burden. Inconsistencies in placeholder handling could lead to malformed paths. Each classifier has slightly different regex patterns
- Fix approach: Create `para_files/utils/placeholder_resolver.py` with `resolve_placeholders()` and `cleanup_unresolved_placeholders()` utilities. Refactor all classifiers to use centralized functions

**Silent Failures in Optional Enrichment:**

- Issue: Description and cover URL extraction in `src/para_files/utils/isbn_lookup.py` (lines 102-103, 110-111) silently fail with bare `pass` statements
- Files: `src/para_files/utils/isbn_lookup.py`
- Impact: When external APIs fail (Google Books, Open Library), the application degrades silently without logging details. Makes it hard to understand why metadata is incomplete
- Fix approach: Replace `pass` with targeted exception logging that indicates which enrichment step failed. Add metrics to track enrichment success rates

## Known Bugs

**MLX Encoder Fallback Token Handling:**

- Symptoms: Text that tokenizes inefficiently (high number/symbol density) can exceed model limits even after truncation, falling back to zero vectors
- Files: `src/para_files/encoders/mlx_encoder.py` (lines 86-98)
- Trigger: Classify documents with technical specifications, source code, chemical formulas, or license plates
- Workaround: Currently returns hardcoded `[[0.0] * 768 for _ in texts]` which masks semantic information. Document specifies max_chars=1000 (~2 tokens/char) but real tokenization can vary
- Long-term fix: Implement adaptive truncation based on actual token count (requires model.tokenize() call) or switch to more robust encoder with built-in truncation

**File Extension Case Sensitivity:**

- Symptoms: Media files with uppercase extensions (.PDF, .EPUB, .CHM) won't be properly detected
- Files: `src/para_files/utils/file_utils.py` (line 160), `src/para_files/pipeline.py` (line 267)
- Trigger: File with extension `.PDF` instead of `.pdf`
- Workaround: macOS HFS+ is case-insensitive by default, so this rarely manifests, but code assumes lowercase
- Fix approach: Standardize to `file_path.suffix.lower()` check in all location-sensitive code

**OCR Rename Confidence Threshold Too Low:**

- Symptoms: Generic PDFs may be renamed based on incidental text, not true document title
- Files: `src/para_files/config.py` (line 184) - default min_confidence=0.3 is lenient
- Trigger: Scan a PDF of a bank statement with "Annual Report" in the header text
- Impact: OCR metadata extracted in `src/para_files/utils/ocr_metadata.py` relies on confidence scoring, but threshold is low enough to rename files on weak signals
- Recommendation: Increase default min_confidence to 0.7 or higher, make it configurable per environment

## Security Considerations

**Subprocess Calls Without Complete Validation:**

- Risk: `subprocess.run()` calls in `src/para_files/utils/pandoc.py`, `src/para_files/utils/exiftool.py`, `src/para_files/utils/chm_metadata.py`, `src/para_files/utils/file_utils.py` use `# noqa: S603` (shell safety), but file paths come from user input indirectly
- Files: `src/para_files/utils/pandoc.py` (line 107), `src/para_files/utils/exiftool.py` (line 260), `src/para_files/utils/chm_metadata.py` (line 60), `src/para_files/utils/file_utils.py` (line 479)
- Current mitigation: All subprocess calls use list arguments (not shell=True), paths are Path objects, noqa annotations are present. Timeout is enforced (5-30 seconds)
- Recommendations:
  - Document the noqa suppressions with specific rationale
  - Add explicit path.exists() check before subprocess execution
  - Consider sandboxing external tools if expanding to untrusted file inputs

**SQLite Thread Safety:**

- Risk: Geolocation cache in `src/para_files/utils/geolocation.py` uses `check_same_thread=False` on SQLite connection (line 121)
- Files: `src/para_files/utils/geolocation.py`
- Current mitigation: Uses threading.RLock() for synchronization (line 92, 134)
- Recommendations:
  - Document why check_same_thread=False is necessary
  - Consider using connection pooling if caching becomes a bottleneck
  - Monitor concurrent access patterns in real usage

**ISBN Validation Assumes Trusted Source:**

- Risk: ISBN lookup integrates with external APIs (Open Library, Google Books, Wikipedia) with minimal validation
- Files: `src/para_files/utils/isbn_lookup.py` (lines 74-80)
- Current mitigation: Results are validated with `isbnlib.is_isbn10()` and `isbnlib.is_isbn13()`. Multiple services are tried for robustness
- Recommendations:
  - Log which service returns metadata for debugging
  - Add timeout enforcement (currently relies on isbnlib defaults)
  - Consider caching results to reduce external API calls

## Performance Bottlenecks

**MLX Model Loading on Initialization:**

- Problem: First classification triggers MLX model load (768-dim embeddings), which blocks for 5-15 seconds on cold start
- Files: `src/para_files/encoders/mlx_encoder.py` (lines 52-58), `src/para_files/classifiers/semantic_classifier.py` (lazy initialization)
- Current behavior: Uses double-check locking pattern (correct), but single model instance is global
- Improvement path:
  - Consider pre-warming model on pipeline init in long-running services
  - Add CLI progress indicator during first-time load (currently silent)
  - Document that first run takes longer

**Parallel ISBN Lookup in Bookstore Command:**

- Problem: `src/para_files/cli/bookstore_cmd.py` (lines 678-688) uses ThreadPoolExecutor for concurrent file processing, but ISBN lookup itself is sequential per file
- Files: `src/para_files/cli/bookstore_cmd.py`
- Bottleneck: Each file → ISBN extraction → API lookup (network I/O), but number of workers is capped at --workers flag (default 4)
- Current bottleneck is network latency, not CPU
- Improvement path:
  - Batch ISBN lookups to reduce API calls
  - Add request caching (currently no in-process cache for bookstore runs)
  - Consider async/await instead of ThreadPoolExecutor for I/O-bound operations

**Redundant EXIF Extraction in File Metadata:**

- Problem: Both `extract_file_metadata()` (line 139-153 in `src/para_files/utils/file_utils.py`) and individual metadata extractors call exiftool
- Files: `src/para_files/utils/file_utils.py`, `src/para_files/utils/exiftool.py`
- Impact: When classifying many files, exiftool is invoked multiple times per file if used by multiple classifiers
- Improvement path:
  - Cache EXIF results in FileMetadata (already extracted once)
  - Add option to skip EXIF if not needed for classification
  - Profile actual impact (may be negligible with 65KB buffer caching)

**Geolocation Cache Lock Contention:**

- Problem: Uses RLock for all cache access, serializing concurrent lookups
- Files: `src/para_files/utils/geolocation.py` (lines 92, 134)
- Impact: Only relevant if many files have GPS coordinates (uncommon)
- Improvement path:
  - Benchmark concurrent access patterns
  - Consider read-write lock if reads dominate
  - Add cache hit rate metrics

## Fragile Areas

**Book Detector Classification Heuristics:**

- Files: `src/para_files/classifiers/book_detector.py`
- Why fragile: Detection relies on multiple exclusion patterns (FINANCIAL, TAX, INSURANCE, TRANSPORT, TELECOM) to avoid false positives. Each pattern is regex-based and regex matchers are brittle:
  - Line 71: Swiss IBAN pattern `CH\d{2}\s*\d{4}\s*\d{4}` doesn't account for formatting variations
  - Line 88: AVIS D'ECRITURES pattern is specific to French documents
  - Line 138-142: Museum/event patterns overlap with travel patterns
- Safe modification: When adding exclusion patterns, test against real documents from that domain. Avoid relying on single-keyword matching. Consider domain-specific classifiers instead
- Test coverage: `tests/test_book_detector.py` has tests for major exclusions but not exhaustive coverage of edge cases

**Taxonomy Classification Path Resolution:**

- Files: `src/para_files/classifiers/taxonomy_classifier.py` (lines 444-504)
- Why fragile: Path resolution uses simple string replacement with placeholders (`{year}`, `{issuer}`). If metadata extraction fails to populate a placeholder, unresolved placeholders are removed with regex cleanup
- Safe modification: Every path change should verify placeholder resolution produces valid paths. Test with missing metadata (no year, no issuer) to ensure graceful degradation
- Test coverage: `tests/test_taxonomy_classifier.py` covers basic path building but not all placeholder scenarios

**Rules Engine Pattern Matching:**

- Files: `src/para_files/classifiers/rules_engine.py`
- Why fragile: Uses glob patterns, glob syntax has special characters that may conflict with actual filenames. Complex rule interactions (multiple patterns on same file) could lead to unexpected behavior
- Safe modification: When adding new rules, verify they don't match unintended files. Test with Unicode filenames, spaces, and special characters
- Test coverage: `tests/test_rules_engine.py` covers basic patterns but not comprehensive edge cases with special characters

**File Mover Deduplication:**

- Files: `src/para_files/mover.py` (lines 46-61)
- Why fragile: Uses SHA256 hash for duplicate detection with 65KB buffer reads. If two different files happen to have identical first 65KB, they're treated as duplicates
- Safe modification: Current approach works for typical classification use case but could misidentify truncated PDFs as duplicates. Document limitations and consider full-file hashing for critical operations
- Risk: Low for current use case (file classification) but could be high if used for archival deduplication

## Scaling Limits

**In-Memory Embedding Cache:**

- Current capacity: All document category embeddings loaded into memory in `SemanticClassifier._category_embeddings` dict
- Limit: With 9,187 Thema codes (from config/thema.json) + document types, memory usage could exceed available headroom on resource-constrained systems
- Scaling path: Implement lazy-load cache with LRU eviction, or pre-compute embeddings offline and load on-demand. Current design is fine for typical usage (<100MB for 10K embeddings)

**Concurrent File Processing:**

- Current capacity: `ThreadPoolExecutor` with max_workers=4 (default in `src/para_files/cli/classify_cmd.py`, `src/para_files/cli/bookstore_cmd.py`)
- Limit: Four parallel threads saturate CPU and I/O on typical machines. Increasing workers beyond machine core count creates contention
- Scaling path: If processing thousands of files, implement batch processing or switch to async/await for I/O-bound operations. Add worker count recommendations in CLI

**Reference Tree Size:**

- Current capacity: `ReferenceTree` loads entire YAML file into memory in `src/para_files/reference_tree.py`
- Limit: Typical YAML is <1MB but could grow if used for complex organizational hierarchies
- Scaling path: For very large organizations, implement lazy loading of subtrees or switch to database backend

## Dependencies at Risk

**mlx-embedding-models Registry Dependency:**

- Risk: Model availability depends on mlx-community maintaining registry. If registry disappears or models are removed, deployment breaks
- Impact: Semantic classifier requires model from registry (nomic-text-v1.5), no built-in fallback
- Files: `src/para_files/encoders/mlx_encoder.py` (line 57)
- Migration plan:
  - Add option to load models from local path
  - Document how to mirror models locally
  - Implement fallback to simpler embedding if registry unavailable

**isbnlib Service Dependencies:**

- Risk: ISBN metadata lookup depends on multiple services (Open Library, Google Books, Wikipedia). Any service can change API or go offline
- Impact: If Open Library API changes, ISBN enrichment silently fails (line 78-79 in `src/para_files/utils/isbn_lookup.py`)
- Files: `src/para_files/utils/isbn_lookup.py`
- Migration plan:
  - Add configuration to enable/disable specific services
  - Implement retry logic with exponential backoff
  - Cache results locally to reduce dependency on external APIs
  - Consider alternative ISBN services (ISBN.org, WorldCat)

**pyobjc Framework Dependencies:**

- Risk: Tight coupling to macOS Vision Framework for OCR. Windows/Linux users cannot use this feature
- Impact: Project is documented as macOS-only, but breaking isolation could happen if OCR features are accessed on unsupported platforms
- Files: `src/para_files/utils/ocr.py`
- Mitigation: Runtime checks for availability, graceful fallback. Current approach is good

## Missing Critical Features

**No Caching for Expensive Operations:**

- Problem: ISBN lookups, EXIF extraction, PDF text extraction are repeated for same file if pipeline runs multiple times
- Blocks: Batch processing or incremental classification workflows
- Recommended feature: Add optional file hash-based cache for classification results and metadata

**No Dry-Run Mode for Classification Pipeline:**

- Problem: Can test individual classifiers but not full pipeline behavior without file moves
- Blocks: Testing complex classification flows in production directories
- Recommended feature: Add `--dry-run` to classify command to preview results without moving files (already exists in move command)

**No Confidence Explainability:**

- Problem: Classification returns confidence score but no explanation of which signals matched
- Blocks: Understanding why a file was classified certain way
- Recommended feature: Add optional verbose mode that shows which classifier(s) matched and their individual scores

## Test Coverage Gaps

**MLX Encoder Fallback Behavior:**

- What's not tested: Behavior when text exceeds token limit even after fallback truncation (returns zero vectors)
- Files: `src/para_files/encoders/mlx_encoder.py` (lines 86-98)
- Risk: Zero vector fallback could cause semantic classifier to have unpredictable behavior
- Priority: Medium - affects accuracy but rare edge case

**Exception Handling in Classifiers:**

- What's not tested: How pipeline behaves when individual classifiers raise exceptions (e.g., network timeout in ISBN lookup during book detection)
- Files: `src/para_files/pipeline.py` (lines 206-208)
- Risk: If exception handling is broken, entire pipeline fails instead of gracefully moving to next classifier
- Priority: High - affects robustness

**Concurrent Bookstore Processing with Conflicts:**

- What's not tested: How conflict resolution works when multiple workers try to move files to same destination simultaneously
- Files: `src/para_files/cli/bookstore_cmd.py` (lines 678-688)
- Risk: Race conditions could cause duplicate files or failed moves
- Priority: High - only manifests in high-concurrency scenarios

**File Mover Edge Cases:**

- What's not tested: Behavior with very long paths (>255 chars on some filesystems), special characters in filenames, symlinks, hard links
- Files: `src/para_files/mover.py`
- Risk: Move operations could fail silently with cryptic error messages
- Priority: Medium - affects edge case scenarios

**Rules Engine Pattern Complexity:**

- What's not tested: Interaction between multiple overlapping patterns, complex path resolution with nested placeholders
- Files: `src/para_files/classifiers/rules_engine.py`
- Risk: Unexpected behavior when rules overlap or interact
- Priority: Medium - depends on complexity of actual rules configured

---

*Concerns audit: 2026-02-28*
