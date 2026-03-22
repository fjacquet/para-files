# ADR-011: Performance Optimizations — Adaptive Threading, Hash Cache, Centralized Truncation

**Date**: 2026-03-22
**Status**: Accepted
**Deciders**: Frederic Jacquet

---

## Context

Three independent performance bottlenecks identified during v1.2 testing:

1. **Thread pool overhead dominates for small batches.** The `move` command always spins up a `ThreadPoolExecutor` regardless of file count. For inbox tasks processing 1–4 files, the thread pool setup and teardown cost more than the classification itself.

2. **Redundant SHA256 hashing.** `_compute_file_hash()` in `mover.py` is called by `files_are_identical()` on every deduplication check. When a batch contains repeated files (e.g., comparing source against existing destination), the same file may be hashed multiple times even within one batch run.

3. **Duplicate content truncation constants.** `semantic_classifier.py` defined `MAX_CONTENT_LENGTH = 2000` locally, duplicating `DEFAULT_CONTENT_PREVIEW_CHARS = 2000` from `config.py`. Any change to the truncation limit would need updating in two places; a mismatch could cause different classifiers to truncate at different lengths silently.

## Decisions

### PERF-01: Thread pool threshold

Add `SINGLE_THREAD_THRESHOLD = 5` to `move_cmd.py`. If `len(expanded_files) < SINGLE_THREAD_THRESHOLD`, force `max_workers = 1` regardless of the configured value.

**Why 5?** The threshold matches the observed crossover point where thread pool overhead equals classification latency for small batches. It is not parameterized — keeping it as a hard constant avoids configuration complexity for a minor tuning knob.

**Observable:** `--verbose` output logs "single-threaded mode (< 5 files)" when the threshold applies.

### PERF-02: Module-level hash cache

Add `_hash_cache: dict[tuple[str, float], str] = {}` at module level in `mover.py`. Cache key: `(str(path), path.stat().st_mtime)`.

**Why a plain dict over `functools.lru_cache`?** `lru_cache` requires a hashable function signature and manages eviction via LRU ordering. The cache key here is a composite `(path, mtime)` — plain dict is more explicit about the key structure and avoids `lru_cache` size limits. Mtime changes on write automatically invalidate the key without explicit TTL management.

**Why no size bound?** Batch move operations don't hash thousands of unique files. The cache lives for the process lifetime; a new process starts fresh.

### PERF-03: Centralized content truncation

Remove `MAX_CONTENT_LENGTH = 2000` from `semantic_classifier.py`. All classifiers (book detector, rules engine, semantic classifier, LLM classifier) now import and use `DEFAULT_CONTENT_PREVIEW_CHARS` from `para_files.config`.

**Why centralize?** A single constant in `config.py` guarantees all classifiers truncate at the same boundary. It is also configurable via the `PARA_FILES_*` env var prefix. Grep for `content[:N]` with a hard-coded integer should return zero hits after this change.

## Consequences

- Small-batch `move` operations (< 5 files) run in the caller's thread, avoiding thread pool overhead
- Deduplication checks within a batch hit the hash cache on the second lookup; mtime invalidation is automatic
- Any future change to content truncation length requires updating only `DEFAULT_CONTENT_PREVIEW_CHARS` in `config.py`
- `SINGLE_THREAD_THRESHOLD` is intentionally not exposed in config — it is an implementation detail, not a user-tunable setting
