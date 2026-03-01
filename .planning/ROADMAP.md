# Roadmap: para-files Technical Debt & Quality Cleanup

## Overview

This milestone eliminates known bugs, tightens code quality, fills test coverage gaps, and ships the missing user-facing features. Each phase delivers a coherent, verifiable improvement to the classification pipeline. The project is already functional — these phases make it correct, observable, and trustworthy.

## Phases

- [x] **Phase 1: Bug Fixes** - Eliminate silent failures and incorrect behavior in the classification pipeline (completed 2026-02-28)
- [x] **Phase 2: Code Quality** - Replace defensive anti-patterns with explicit, typed error handling (completed 2026-02-28)
- [x] **Phase 3: Test Coverage** - Validate pipeline resilience and edge cases with automated tests (completed 2026-02-28)
- [x] **Phase 4: User Features** - Expose classification transparency and dry-run safety to users (completed 2026-02-28)
- [ ] **Phase 5: Content Extraction** - Pipeline reads inside Excel, ODS, and ZIP/7Z files for semantic classification
- [ ] **Phase 6: Extension Routing** - Media, security, script, and exotic files route to sensible folders by extension
- [ ] **Phase 7: Inbox Processing UX** - One-shot command processes the entire inbox with progress display and post-run summary

## Phase Details

### Phase 1: Bug Fixes

**Goal**: The classification pipeline handles real-world input correctly without silent fallbacks
**Depends on**: Nothing (first phase)
**Requirements**: BUG-01, BUG-02, BUG-03
**Success Criteria** (what must be TRUE):

  1. A file named `document.PDF` is classified correctly (not skipped due to uppercase extension)
  2. OCR renaming only triggers when confidence exceeds 0.7 — a bank statement header does not rename the file
  3. A technical specification or source code file with high symbol density receives a real embedding, not a zero vector
**Plans**: 1 plan

Plans:

- [x] 01-bug-fixes-01-PLAN.md — Fix extension normalization, OCR confidence threshold, and MLX encoder zero-vector

### Phase 2: Code Quality

**Goal**: Failures surface with specific context instead of being silently swallowed
**Depends on**: Phase 1
**Requirements**: QUAL-01, QUAL-02, QUAL-03
**Success Criteria** (what must be TRUE):

  1. A network timeout in ISBN lookup produces a log entry naming the exception type, not a silent pass
  2. Placeholder cleanup (`{year}`, `{issuer}`, `{location}`) runs from a single function across all classifiers — no duplication
  3. ISBN enrichment failures are logged with the specific enrichment step that failed (description vs. cover URL)
**Plans**: 2 plans

Plans:

- [ ] 02-01-PLAN.md — Centralize placeholder cleanup into placeholder_resolver.py (QUAL-02)
- [ ] 02-02-PLAN.md — Replace silent ISBN enrichment and PDF page extraction failures with targeted log messages (QUAL-01, QUAL-03)

### Phase 3: Test Coverage

**Goal**: Automated tests verify pipeline resilience in the three highest-risk scenarios
**Depends on**: Phase 2
**Requirements**: TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):

  1. A test proves the pipeline classifies a file when one classifier raises an unhandled exception — no crash, next classifier runs
  2. A test proves concurrent bookstore workers moving files to the same destination resolve conflicts without data loss or silent failure
  3. Tests cover overlapping glob patterns, Unicode filenames, and special-character filenames in the rules engine
**Plans**: 3 plans

Plans:

- [ ] 03-01-PLAN.md — Strengthen pipeline classifier exception isolation tests (TEST-01)
- [ ] 03-02-PLAN.md — Add concurrent bookstore ISBN deduplication and FileMover conflict tests (TEST-02)
- [ ] 03-03-PLAN.md — Add Unicode filenames, special-character filenames, and overlapping pattern tests to rules engine (TEST-03)

### Phase 4: User Features

**Goal**: Users can preview classification results and understand which signal drove the decision
**Depends on**: Phase 3
**Requirements**: FEAT-01, FEAT-02, FEAT-03
**Success Criteria** (what must be TRUE):

  1. Running `classify --dry-run` prints the predicted destination for each file without moving anything
  2. Running `classify --verbose` (or `scan --verbose`, `move --verbose`) shows which classifier matched and its confidence score
  3. JSON output for any classified file includes a `signals` array listing each classifier's result (source, score, matched)
**Plans**: 2 plans

Plans:

- [x] 04-01-PLAN.md — Add SignalResult type and collect all classifier signals in pipeline (FEAT-03 foundation)
- [x] 04-02-PLAN.md — Add classify --dry-run, verbose signal display, and signals in JSON output (FEAT-01, FEAT-02, FEAT-03)

### Phase 5: Content Extraction

**Goal**: The pipeline reads inside Excel, ODS, and ZIP/7Z files and uses their content as a classification signal
**Depends on**: Phase 4
**Requirements**: XTRCT-01, XTRCT-02, XTRCT-03, XTRCT-04
**Success Criteria** (what must be TRUE):

  1. An Excel file (.xlsx, .xls, .xlsm) whose sheet names and cell values describe a budget is classified to a finance folder, not left in Inbox
  2. An ODS file whose content describes a project plan is classified semantically, not treated as an opaque binary
  3. A ZIP archive containing filenames like `invoice_2024.pdf` and `contract.docx` routes to a documents folder based on the manifest
  4. A corrupted or password-protected Excel/ZIP file does not crash the pipeline — it falls through to the next signal and logs a warning
**Plans**: 3 plans

Plans:

- [ ] 05-01-PLAN.md — Add Excel (.xlsx, .xlsm, .xls) and ODS readers with graceful failure handling (XTRCT-01, XTRCT-02, XTRCT-04)
- [ ] 05-02-PLAN.md — Add ZIP/7Z archive manifest reader, add py7zr optional dependency (XTRCT-03, XTRCT-04)
- [ ] 05-03-PLAN.md — TDD test suite for all content extraction readers including graceful failure cases (XTRCT-01–04)

### Phase 6: Extension Routing

**Goal**: Media, security, script, and exotic files route to sensible permanent folders rather than staying in Inbox
**Depends on**: Phase 4
**Requirements**: ROUTE-01, ROUTE-02, ROUTE-03, ROUTE-04, ROUTE-05, ROUTE-06
**Success Criteria** (what must be TRUE):

  1. A `.3gp`, `.m4v`, `.mp4`, or `.mov` file with no other matching signal routes to the configured media/video folder
  2. A `.m4a` or `.mp3` file routes to the configured media/audio folder
  3. A `.gif`, `.tif`, or `.psd` file routes to the configured media/images folder
  4. A `.p7b`, `.asc`, or `.kdbx` file routes to the configured security folder
  5. A `.ps1`, `.css`, `.js`, or `.sh` file routes to the configured scripts/dev folder
  6. A file with an extension not handled by any other signal routes to a catch-all folder rather than remaining in Inbox
**Plans**: 3 plans

Plans:
- [ ] 06-01-PLAN.md — Add ExtensionRoutingConfig and ExtensionRouterClassifier (ROUTE-01–06)
- [ ] 06-02-PLAN.md — TDD test suite for ExtensionRouterClassifier (ROUTE-01–06)
- [ ] 06-03-PLAN.md — Wire ExtensionRouterClassifier into pipeline and regression tests (ROUTE-01–06)

### Phase 7: Inbox Processing UX

**Goal**: Users can drain their inbox in one command and see exactly what happened
**Depends on**: Phase 5, Phase 6
**Requirements**: UX-01, UX-02, UX-03, UX-04
**Success Criteria** (what must be TRUE):

  1. Running a single command against the inbox directory classifies and moves all confidently-matched files without any intermediate steps
  2. Files the pipeline cannot classify with sufficient confidence remain in Inbox — none are moved to a wrong location
  3. During processing, each file shows its name, destination, and running count in the terminal output
  4. After processing completes, the terminal prints a summary: total files processed, moved count, stayed-in-inbox count, and breakdown by signal source
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Bug Fixes | 1/1 | Complete    | 2026-02-28 |
| 2. Code Quality | 2/2 | Complete    | 2026-02-28 |
| 3. Test Coverage | 3/3 | Complete    | 2026-02-28 |
| 4. User Features | 2/2 | Complete    | 2026-02-28 |
| 5. Content Extraction | 2/3 | In Progress|  |
| 6. Extension Routing | 0/3 | Not started | - |
| 7. Inbox Processing UX | 0/TBD | Not started | - |
