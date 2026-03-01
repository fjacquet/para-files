# Requirements: para-files

**Defined:** 2026-02-28
**Core Value:** Files are classified correctly and transparently — users understand why, and failures surface loudly.

## v1.0 Requirements (Complete)

### Bug Fixes

- [x] **BUG-01**: File extension detection handles uppercase extensions (.PDF, .EPUB, .CHM) correctly
- [x] **BUG-02**: OCR rename default confidence threshold raised to 0.7 (was 0.3)
- [x] **BUG-03**: MLX encoder handles high token-density text without silently returning zero vectors

### Code Quality

- [x] **QUAL-01**: All bare `except Exception` (BLE001) blocks replaced with typed handlers or improved fallback logging
- [x] **QUAL-02**: Placeholder cleanup logic (`{year}`, `{issuer}`, `{location}`) centralized into `para_files/utils/placeholder_resolver.py`
- [x] **QUAL-03**: Silent failures in ISBN enrichment (`pass` statements) replaced with targeted log messages

### Test Coverage

- [x] **TEST-01**: Pipeline exception handling tested — classifiers that raise exceptions don't crash entire pipeline
- [x] **TEST-02**: Concurrent bookstore processing conflict resolution tested (multiple workers, same destination)
- [x] **TEST-03**: Rules engine edge cases tested (overlapping patterns, Unicode filenames, special characters)

### Missing Features

- [x] **FEAT-01**: `classify` command supports `--dry-run` flag (preview classification without moving files)
- [x] **FEAT-02**: `classify`, `move`, and `scan` commands support `--verbose` flag showing which classifier matched and its score
- [x] **FEAT-03**: JSON output includes `signals` array with per-classifier results (source, score, matched)

## v1.1 Requirements

### Content Extraction

- [x] **XTRCT-01**: Excel files (.xlsx, .xls, .xlsm) yield extractable text (sheet names + first N cell values) for semantic classification
- [x] **XTRCT-02**: ODS files (.ods) yield extractable text for semantic classification
- [x] **XTRCT-03**: ZIP/7Z archive manifests (list of internal filenames) are read and used as classification signal
- [x] **XTRCT-04**: Content extraction failures are handled gracefully — fall through to next signal, never crash

### Extension Routing

- [x] **ROUTE-01**: Media video files (.3gp, .m4v, .mp4, .mov) without a better match route to a fixed media folder
- [x] **ROUTE-02**: Media audio files (.m4a, .mp3) route to a fixed media folder when unmatched
- [x] **ROUTE-03**: Image files (.gif, .tif, .tiff, .psd) route to a fixed media folder when unmatched
- [x] **ROUTE-04**: Security/cert files (.p7b, .asc, .kdbx) route to a dedicated security folder
- [x] **ROUTE-05**: Script files (.ps1, .css, .js, .sh) route to a dedicated scripts/dev folder
- [x] **ROUTE-06**: Exotic/unknown extensions route to a dedicated catch-all folder rather than staying in Inbox

### Inbox Processing UX

- [ ] **UX-01**: A single command processes the entire inbox directory — classifying and moving all files it can confidently route
- [ ] **UX-02**: Files the pipeline cannot classify are left in Inbox (not moved to a wrong location)
- [ ] **UX-03**: Progress is displayed during bulk processing (file count, current file, destination)
- [ ] **UX-04**: A post-run summary shows: total files processed, moved count, stayed-in-inbox count, breakdown by signal source

## v2 Requirements

### Performance

- **PERF-01**: ISBN lookup results cached between runs to reduce external API calls
- **PERF-02**: EXIF metadata cached per-file to avoid redundant extraction across classifiers
- **PERF-03**: Bookstore command uses async/await for I/O-bound ISBN lookup

### Resilience

- **RESIL-01**: MLX model loadable from local path (fallback if registry unavailable)
- **RESIL-02**: ISBN lookup retries with exponential backoff on transient failures

### Deeper Archive Handling

- **ARCH-01**: Recurse into ZIP and extract text from contained documents for richer classification
- **ARCH-02**: Cache archive manifest results to avoid re-reading on rescan

### Batch Learning

- **LEARN-01**: After inbox processing, prompt user to review low-confidence moves and feed corrections into the learned DB

## Out of Scope

| Feature | Reason |
|---------|--------|
| Archive extraction before classification | Slow, risky, destructive for inbox workflow |
| OCR of Excel charts/images | Complexity vs gain ratio too low |
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
| QUAL-01 | Phase 2 | Complete |
| QUAL-02 | Phase 2 | Complete |
| QUAL-03 | Phase 2 | Complete |
| TEST-01 | Phase 3 | Complete |
| TEST-02 | Phase 3 | Complete |
| TEST-03 | Phase 3 | Complete |
| FEAT-01 | Phase 4 | Complete |
| FEAT-02 | Phase 4 | Complete |
| FEAT-03 | Phase 4 | Complete |
| XTRCT-01 | Phase 5 | Complete |
| XTRCT-02 | Phase 5 | Complete |
| XTRCT-03 | Phase 5 | Complete |
| XTRCT-04 | Phase 5 | Complete |
| ROUTE-01 | Phase 6 | Complete |
| ROUTE-02 | Phase 6 | Complete |
| ROUTE-03 | Phase 6 | Complete |
| ROUTE-04 | Phase 6 | Complete |
| ROUTE-05 | Phase 6 | Complete |
| ROUTE-06 | Phase 6 | Complete |
| UX-01 | Phase 7 | Pending |
| UX-02 | Phase 7 | Pending |
| UX-03 | Phase 7 | Pending |
| UX-04 | Phase 7 | Pending |

**Coverage:**
- v1.0 requirements: 12 total — all Complete ✓
- v1.1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-03-01 after milestone v1.1 initialization*
