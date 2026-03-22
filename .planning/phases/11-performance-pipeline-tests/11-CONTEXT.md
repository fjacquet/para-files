# Phase 11: Performance + Pipeline Tests - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Three performance improvements (adaptive threading, hash caching, centralized content truncation)
and two test suites (pipeline order/failure isolation, concurrent threading).

This phase does NOT add new classifiers, new CLI commands, or change classification logic.

</domain>

<decisions>
## Implementation Decisions

### Thread Pool Threshold (PERF-01)
- Add `SINGLE_THREAD_THRESHOLD = 5` as a module-level constant in `move_cmd.py`
- If `len(expanded_files) < SINGLE_THREAD_THRESHOLD`, force `max_workers = 1` regardless of config value
- The threshold check runs before `_move_files_parallel()` dispatch — observable in `--verbose` log output
- The config `max_workers` default (4) is unchanged; threshold overrides it for small batches only
- Success criterion: classifying fewer than 5 files shows "single-threaded" in `--verbose` output

### Hash Cache (PERF-02)
- Add a module-level `_hash_cache: dict[tuple[str, float], str]` in `mover.py`
- Cache key: `(str(path), path.stat().st_mtime)` — combines path identity with modification time
- `_compute_file_hash()` checks cache before computing; inserts on miss
- Cache is **not** cleared between calls — it is module-level and persists for the process lifetime
- This is acceptable: mtime changes invalidate the cache key naturally
- No explicit size bound — kept simple (batch moves don't hash thousands of unique files)
- `files_are_identical()` calls `_compute_file_hash()` which benefits automatically

### Content Truncation Centralization (PERF-03)
- `semantic_classifier.py` has a local `MAX_CONTENT_LENGTH = 2000` that duplicates `DEFAULT_CONTENT_PREVIEW_CHARS` from `config.py`
- Remove the local constant; import and use `DEFAULT_CONTENT_PREVIEW_CHARS` from `para_files.config`
- Rename all internal references in `semantic_classifier.py` to match
- Verify `llm_classifier.py`, `book_detector.py`, and the encoder all reference the same constant
- A grep for hard-coded `[:2000]` or `[:1000]` in classifiers/encoders should find zero hits after this fix

### Pipeline Test Coverage (TEST-01)
- New test file: `tests/test_pipeline_order.py`
- Tests use mock classifiers (same pattern as Phase 9's `test_llm_classifier.py::test_pipeline_short_circuit`)
- Required test cases:
  1. Classifier order: classifiers are called in registration order (Signal 1 before 2, etc.)
  2. First match wins: if Signal 2 matches, Signals 3–7 are never called
  3. Disabled classifiers: a classifier with `enabled=False` is skipped entirely
  4. Single classifier exception: one classifier raising an exception does not abort subsequent classifiers — remaining classifiers still run and the best result is returned

### Concurrent Threading Tests (TEST-03)
- New test file: `tests/test_concurrent_move.py`
- Tests use `tmp_path` fixture and real file system operations (no mocking of file I/O)
- Required test cases:
  1. Thread pool with simulated crash: one worker raises, other workers complete successfully, results are collected
  2. Load test with 10 files: all 10 results returned with no silent losses
  3. Verify `max_workers=1` path (single-threaded) produces same results as `max_workers=4` (parallel)

### Claude's Discretion
- Exact log message wording for "single-threaded mode" in `--verbose` output
- Whether to use `functools.lru_cache` or a plain dict for the hash cache (plain dict preferred for explicit key)
- Whether to also audit `book_detector.py` content slicing or just `semantic_classifier.py` (audit all)
- Whether `test_pipeline_order.py` imports the real pipeline or builds a minimal test harness

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements are fully captured in decisions above and in REQUIREMENTS.md.

### Requirements
- `.planning/REQUIREMENTS.md` — PERF-01, PERF-02, PERF-03, TEST-01, TEST-03 (performance and test requirements)

### Existing Code to Read Before Modifying
- `src/para_files/cli/move_cmd.py` — lines ~610-630: `max_workers` selection + parallel/sequential dispatch
- `src/para_files/mover.py` — `_compute_file_hash()` (line ~31), `files_are_identical()` (line ~48): understand current hash flow before adding cache
- `src/para_files/classifiers/semantic_classifier.py` — line 33: `MAX_CONTENT_LENGTH = 2000` local constant to remove; line 319: usage
- `src/para_files/config.py` — line 37: `DEFAULT_CONTENT_PREVIEW_CHARS = 2000` (the canonical value)
- `src/para_files/pipeline.py` — `classify()` method: understand classifier iteration order and exception handling

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/test_llm_classifier.py::test_pipeline_short_circuit`: existing mock-based pipeline test — reuse pattern for TEST-01 tests
- `threading.Lock()` in `pipeline.py`: existing thread-safety pattern to follow
- `tmp_path` fixture: already used extensively in `tests/test_mover.py` — same pattern for TEST-03

### Established Patterns
- Module-level constants in `move_cmd.py` (e.g., already has `_check_destination_permissions` pattern from Phase 10)
- `DEFAULT_CONTENT_PREVIEW_CHARS` imported from `para_files.config` — LLM classifier already does this correctly; semantic classifier needs the same treatment
- `ClassificationPipeline.__new__()` + `pipeline._classifiers = [...]` injection pattern: established in Phase 9 for mock-based pipeline tests

### Integration Points
- `move_cmd.py` lines ~615-625: the `if max_workers > 1 and len(expanded_files) > 1` gate is where the `SINGLE_THREAD_THRESHOLD` check inserts
- `mover.py` `_compute_file_hash()`: single insertion point for cache check+miss logic
- `semantic_classifier.py` line 319: single usage site for `MAX_CONTENT_LENGTH`

</code_context>

<specifics>
## Specific Ideas

- The thread pool threshold (< 5) matches the ROADMAP.md success criterion exactly — don't parameterize it
- Hash cache uses mtime as the invalidation signal — no explicit TTL needed since the cache lives for the process lifetime and mtime changes on write
- The PERF-03 audit should grep for any `content[:N]` where N is a hard-coded integer — if found, replace with `DEFAULT_CONTENT_PREVIEW_CHARS`

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-performance-pipeline-tests*
*Context gathered: 2026-03-22 via --auto mode*
