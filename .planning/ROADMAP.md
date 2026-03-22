# Roadmap: para-files

## Milestones

- ✅ **v1.1 Inbox Throughput** — Phases 1–7 (shipped 2026-03-01)
- 🚧 **v1.2 Reliability & Performance** — Phases 8–11 (in progress)

## Phases

<details>
<summary>✅ v1.1 Inbox Throughput (Phases 1–7) — SHIPPED 2026-03-01</summary>

- [x] Phase 1: Bug Fixes (1/1 plans) — completed 2026-02-28
- [x] Phase 2: Code Quality (2/2 plans) — completed 2026-02-28
- [x] Phase 3: Test Coverage (3/3 plans) — completed 2026-02-28
- [x] Phase 4: User Features (2/2 plans) — completed 2026-02-28
- [x] Phase 5: Content Extraction (3/3 plans) — completed 2026-03-01
- [x] Phase 6: Extension Routing (3/3 plans) — completed 2026-03-01
- [x] Phase 7: Inbox Processing UX (2/2 plans) — completed 2026-03-01

Full phase details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

### 🚧 v1.2 Reliability & Performance (In Progress)

**Milestone Goal:** Make the classification pipeline trustworthy — fix silent failures, add timeouts and circuit breakers, harden error handling, and improve throughput.

## Phase Details

### Phase 8: Foundation Hardening

**Goal**: The codebase handles errors explicitly — no broad exception swallowing, no silent placeholder failures, subprocess calls validated
**Depends on**: Phase 7 (v1.1 shipped)
**Requirements**: DEP-02, ERR-01, ERR-02, ERR-03, ERR-04, ERR-05, TEST-02, TEST-05
**Success Criteria** (what must be TRUE):

  1. Running `uv run para-files classify <file>` never swallows a specific exception silently — ruff BLE001 violations are zero in pipeline.py, all classifiers, and utilities
  2. Classifying a file whose template has an unresolved placeholder surfaces a warning instead of stripping the placeholder and silently returning a bad path
  3. Subprocess calls to exiftool, pandoc, and chm reject files with wrong extensions before execution, preventing misuse
  4. Placeholder resolution tests cover: missing year, empty issuer, multiple missing fields, double-slash paths — all pass
  5. Pandoc integration tests cover: broken install, timeout, wrong encoding — all pass
**Plans:** 2/3 plans executed

Plans:

- [ ] 08-01-PLAN.md — Narrow exceptions in pipeline, LLM classifier, and Ollama encoder (ERR-01, ERR-02)
- [ ] 08-02-PLAN.md — Narrow exceptions in utilities, subprocess extension validation, macOS test isolation (ERR-03, ERR-05, DEP-02)
- [ ] 08-03-PLAN.md — Placeholder resolution policy with required/optional distinction, placeholder and pandoc test suites (ERR-04, TEST-02, TEST-05)

### Phase 9: LLM + Service Reliability

**Goal**: Ollama-dependent classifiers never hang the pipeline, never crash on Ctrl+C, and recover gracefully when the Ollama server is absent or flaking
**Depends on**: Phase 8
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, SVC-01, SVC-02, SVC-03, SVC-04, SVC-05, TEST-04
**Success Criteria** (what must be TRUE):

  1. Classifying a file with Ollama responding slowly completes within 15 seconds (default timeout) and returns a non-LLM result rather than hanging
  2. Pressing Ctrl+C during `para-files inbox` exits cleanly without a RuntimeError traceback
  3. After a configured number of consecutive Ollama failures, semantic and LLM classifiers are skipped for remaining files in the batch — no further connection attempts
  4. Starting the pipeline with Ollama unreachable disables semantic/LLM at init rather than failing per-file
  5. LLM response format tests cover: string confidence, trailing spaces, nested JSON, incomplete JSON — all parse without exception
**Plans:** 2/3 plans executed

Plans:

- [ ] 09-01-PLAN.md — Circuit breaker, health check, encoder retry fix, Ctrl+C handling (SVC-01, SVC-03, SVC-04, LLM-01, LLM-02)
- [ ] 09-02-PLAN.md — LLM response parsing: JSON-first, confidence coercion, URL-decode, allowlist (LLM-03, LLM-04, LLM-05, TEST-04)
- [ ] 09-03-PLAN.md — Embedding cache and ISBN error distinction (SVC-02, SVC-05)

### Phase 10: Classification Accuracy + Move Safety

**Goal**: The book detector stops misclassifying French financial documents as books, the reference tree validates on load, and batch moves can be rolled back on failure
**Depends on**: Phase 9
**Requirements**: ACC-01, ACC-02, ACC-03, ACC-04, ACC-05, MOV-01, MOV-02
**Success Criteria** (what must be TRUE):

  1. Running `para-files classify` on a French financial PDF (IBAN-containing, no actual ISBN) returns a non-book classification
  2. Loading a malformed `personal_file_tree.yaml` causes an immediate startup error with a clear message, not a silent misconfiguration
  3. A failed batch move operation provides a rollback option that restores all already-moved files to their original locations
  4. Move operations validate destination write permissions before starting, rejecting the batch with a clear error if permissions are insufficient
  5. Files that no classifier can match are routed to `6_unclassified` (not `0_Inbox`) — `0_Inbox` is reserved for user-placed files awaiting triage
**Plans**: TBD

### Phase 11: Performance + Pipeline Tests

**Goal**: The pipeline adapts thread usage to file count, avoids redundant hashing and Ollama calls, and pipeline-level tests verify classifier ordering and failure isolation
**Depends on**: Phase 10
**Requirements**: PERF-01, PERF-02, PERF-03, TEST-01, TEST-03
**Success Criteria** (what must be TRUE):

  1. Classifying fewer than 5 files runs single-threaded with no thread pool overhead — observable via `--verbose` output
  2. Moving a set of files where some share content does not re-hash already-seen files (mtime + path cache hit)
  3. All classifiers and encoders respect MAX_CONTENT_CHARS — no classifier silently truncates at a different limit
  4. Pipeline tests confirm: classifier order is respected, disabled classifiers are skipped, a single classifier failure does not abort remaining classifiers
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Bug Fixes | v1.1 | 1/1 | Complete | 2026-02-28 |
| 2. Code Quality | v1.1 | 2/2 | Complete | 2026-02-28 |
| 3. Test Coverage | v1.1 | 3/3 | Complete | 2026-02-28 |
| 4. User Features | v1.1 | 2/2 | Complete | 2026-02-28 |
| 5. Content Extraction | v1.1 | 3/3 | Complete | 2026-03-01 |
| 6. Extension Routing | v1.1 | 3/3 | Complete | 2026-03-01 |
| 7. Inbox Processing UX | v1.1 | 2/2 | Complete | 2026-03-01 |
| 8. Foundation Hardening | 2/3 | In Progress|  | - |
| 9. LLM + Service Reliability | 2/3 | In Progress|  | - |
| 10. Classification Accuracy + Move Safety | v1.2 | 0/? | Not started | - |
| 11. Performance + Pipeline Tests | v1.2 | 0/? | Not started | - |
