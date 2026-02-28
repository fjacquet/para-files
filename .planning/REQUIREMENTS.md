# Requirements: para-files Technical Debt & Quality Cleanup

**Defined:** 2026-02-28
**Core Value:** Files are classified correctly and transparently — users understand why, and failures surface loudly.

## v1 Requirements

### Bug Fixes

- [x] **BUG-01**: File extension detection handles uppercase extensions (.PDF, .EPUB, .CHM) correctly
- [x] **BUG-02**: OCR rename default confidence threshold raised to 0.7 (was 0.3)
- [x] **BUG-03**: MLX encoder handles high token-density text without silently returning zero vectors

### Code Quality

- [ ] **QUAL-01**: All bare `except Exception` (BLE001) blocks replaced with typed handlers or improved fallback logging
- [ ] **QUAL-02**: Placeholder cleanup logic (`{year}`, `{issuer}`, `{location}`) centralized into `para_files/utils/placeholder_resolver.py`
- [ ] **QUAL-03**: Silent failures in ISBN enrichment (`pass` statements) replaced with targeted log messages

### Test Coverage

- [ ] **TEST-01**: Pipeline exception handling tested — classifiers that raise exceptions don't crash entire pipeline
- [ ] **TEST-02**: Concurrent bookstore processing conflict resolution tested (multiple workers, same destination)
- [ ] **TEST-03**: Rules engine edge cases tested (overlapping patterns, Unicode filenames, special characters)

### Missing Features

- [ ] **FEAT-01**: `classify` command supports `--dry-run` flag (preview classification without moving files)
- [ ] **FEAT-02**: `classify`, `move`, and `scan` commands support `--verbose` flag showing which classifier matched and its score
- [ ] **FEAT-03**: JSON output includes `signals` array with per-classifier results (source, score, matched)

## v2 Requirements

### Performance

- **PERF-01**: ISBN lookup results cached between runs to reduce external API calls
- **PERF-02**: EXIF metadata cached per-file to avoid redundant extraction across classifiers
- **PERF-03**: Bookstore command uses async/await for I/O-bound ISBN lookup

### Resilience

- **RESIL-01**: MLX model loadable from local path (fallback if registry unavailable)
- **RESIL-02**: ISBN lookup retries with exponential backoff on transient failures

## Out of Scope

| Feature | Reason |
|---------|--------|
| Geolocation cache read-write lock | Low impact — GPS files are rare in typical use |
| Embedding LRU eviction | Premature optimization — <100MB for 10K embeddings |
| Windows/Linux support | MLX requires Apple Silicon; platform constraint is intentional |
| SQLite connection pooling | RLock + check_same_thread=False is sufficient at current scale |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUG-01 | Phase 1 | Complete |
| BUG-02 | Phase 1 | Complete |
| BUG-03 | Phase 1 | Complete |
| QUAL-01 | Phase 2 | Pending |
| QUAL-02 | Phase 2 | Pending |
| QUAL-03 | Phase 2 | Pending |
| TEST-01 | Phase 3 | Pending |
| TEST-02 | Phase 3 | Pending |
| TEST-03 | Phase 3 | Pending |
| FEAT-01 | Phase 4 | Pending |
| FEAT-02 | Phase 4 | Pending |
| FEAT-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 after initial definition*
