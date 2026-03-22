# Requirements: para-files

**Defined:** 2026-03-22
**Core Value:** Files are classified correctly and transparently — users understand why, and failures surface loudly.

## v1.2 Requirements

Requirements for Reliability & Performance milestone. Each maps to roadmap phases.

### LLM Reliability

- [ ] **LLM-01**: LLM classifier times out after configurable threshold (default 15s)
- [ ] **LLM-02**: Ctrl+C during LLM call exits gracefully without RuntimeError crash
- [x] **LLM-03**: Pipeline short-circuits after first classifier match
- [x] **LLM-04**: LLM response parsing uses proper JSON parsing with regex fallback, not regex-only
- [x] **LLM-05**: LLM output validation adds URL-decoding check and uses allowlist for PARA categories

### Error Handling

- [x] **ERR-01**: Replace broad `except Exception` (BLE001) in pipeline.py with specific exception types
- [x] **ERR-02**: Replace broad `except Exception` in classifiers with specific types
- [x] **ERR-03**: Replace broad `except Exception` in utilities (ocr, pandoc, isbn_lookup) with specific types
- [x] **ERR-04**: Placeholder resolution rejects classification when critical placeholders are unresolved (not silent strip)
- [x] **ERR-05**: Subprocess calls (exiftool, pandoc, chm) validate file extensions before execution

### Service Resilience

- [ ] **SVC-01**: Ollama circuit breaker — skip semantic/LLM classifiers after N consecutive failures
- [x] **SVC-02**: Embedding results cached by content hash to avoid redundant Ollama calls
- [ ] **SVC-03**: Ollama health check at pipeline init — disable semantic/LLM if server unreachable
- [ ] **SVC-04**: Ollama encoder stops retry chain immediately on connection error (not 4 retries when server is down)
- [x] **SVC-05**: ISBN lookup distinguishes "invalid ISBN" from "service unavailable" and retries on transient errors

### Classification Accuracy

- [ ] **ACC-01**: Book detector reduces false positives on French financial documents
- [ ] **ACC-02**: Book detector tests: invalid ISBNs, all-zero, IBAN-like patterns
- [ ] **ACC-03**: Rules engine tests: date extraction edge cases (1989, 2041), pattern shadowing
- [ ] **ACC-04**: Reference tree YAML validates structure with Pydantic on load (fail fast on invalid)
- [ ] **ACC-05**: Unclassifiable files (no classifier match) go to `6_unclassified` instead of `0_Inbox`

### Move Safety

- [ ] **MOV-01**: Batch move tracks completed moves and offers rollback on failure
- [ ] **MOV-02**: Move operation validates destination permissions before starting batch

### Performance

- [ ] **PERF-01**: Thread pool sizing adapts to file count — skip threading for < 5 files
- [ ] **PERF-02**: File hash caching in mover (by path + mtime)
- [ ] **PERF-03**: Centralized content truncation config (MAX_CONTENT_CHARS) respected by all classifiers/encoders

### Dependency Hygiene

- [x] **DEP-01**: ~~Remove unused semantic-router dependency~~ — DEFERRED (user decision: keep dependency)
- [x] **DEP-02**: macOS OCR tests isolated with platform skip markers in CI

### Test Coverage

- [ ] **TEST-01**: Pipeline tests: classifier order matters, disabled classifiers, partial failures
- [x] **TEST-02**: Placeholder resolution tests: missing year, empty issuer, multiple missing, double-slash
- [ ] **TEST-03**: Concurrent threading tests: thread crash, timeout under load
- [x] **TEST-04**: LLM response format tests: string confidence, trailing spaces, nested JSON, incomplete JSON
- [x] **TEST-05**: Pandoc integration tests: broken install, timeout, wrong encoding

## Future Requirements

Deferred to v1.3+. Tracked but not in current roadmap.

### Learning & Adaptation

- **LEARN-01**: Integrate FeedbackTracker into classification pipeline for incremental learning
- **LEARN-02**: Confidence adjustment based on historical correction rates

### Flexibility

- **FLEX-01**: Category aliases/synonyms for PARA path refactoring
- **FLEX-02**: YAML reference tree lazy-loading and indexing for large rule sets

## Out of Scope

| Feature | Reason |
|---------|--------|
| Incremental learning from corrections | Large scope — requires pipeline architecture changes, defer to v1.3 |
| Category aliases/synonyms | Large scope — requires reference tree redesign, defer to v1.3 |
| YAML tree lazy-loading | Low impact — current tree size is manageable |
| Async/await refactor | Large scope — current threading model is sufficient |
| Mobile / non-desktop support | Desktop CLI tool |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LLM-01 | Phase 9 | Pending |
| LLM-02 | Phase 9 | Pending |
| LLM-03 | Phase 9 | Complete |
| LLM-04 | Phase 9 | Complete |
| LLM-05 | Phase 9 | Complete |
| ERR-01 | Phase 8 | Complete |
| ERR-02 | Phase 8 | Complete |
| ERR-03 | Phase 8 | Complete |
| ERR-04 | Phase 8 | Complete |
| ERR-05 | Phase 8 | Complete |
| SVC-01 | Phase 9 | Pending |
| SVC-02 | Phase 9 | Complete |
| SVC-03 | Phase 9 | Pending |
| SVC-04 | Phase 9 | Pending |
| SVC-05 | Phase 9 | Complete |
| ACC-01 | Phase 10 | Pending |
| ACC-02 | Phase 10 | Pending |
| ACC-03 | Phase 10 | Pending |
| ACC-04 | Phase 10 | Pending |
| ACC-05 | Phase 10 | Pending |
| MOV-01 | Phase 10 | Pending |
| MOV-02 | Phase 10 | Pending |
| PERF-01 | Phase 11 | Pending |
| PERF-02 | Phase 11 | Pending |
| PERF-03 | Phase 11 | Pending |
| DEP-01 | Phase 8 | Deferred (keep semantic-router) |
| DEP-02 | Phase 8 | Complete |
| TEST-01 | Phase 11 | Pending |
| TEST-02 | Phase 8 | Complete |
| TEST-03 | Phase 11 | Pending |
| TEST-04 | Phase 9 | Complete |
| TEST-05 | Phase 8 | Complete |

**Coverage:**

- v1.2 requirements: 32 total (1 deferred)
- Mapped to phases: 32
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-22*
*Last updated: 2026-03-22 after Phase 8 context discussion*
