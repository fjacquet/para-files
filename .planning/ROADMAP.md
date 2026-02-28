# Roadmap: para-files Technical Debt & Quality Cleanup

## Overview

This milestone eliminates known bugs, tightens code quality, fills test coverage gaps, and ships the missing user-facing features. Each phase delivers a coherent, verifiable improvement to the classification pipeline. The project is already functional — these phases make it correct, observable, and trustworthy.

## Phases

- [x] **Phase 1: Bug Fixes** - Eliminate silent failures and incorrect behavior in the classification pipeline (completed 2026-02-28)
- [x] **Phase 2: Code Quality** - Replace defensive anti-patterns with explicit, typed error handling (completed 2026-02-28)
- [ ] **Phase 3: Test Coverage** - Validate pipeline resilience and edge cases with automated tests
- [ ] **Phase 4: User Features** - Expose classification transparency and dry-run safety to users

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
**Plans**: TBD

### Phase 4: User Features

**Goal**: Users can preview classification results and understand which signal drove the decision
**Depends on**: Phase 3
**Requirements**: FEAT-01, FEAT-02, FEAT-03
**Success Criteria** (what must be TRUE):

  1. Running `classify --dry-run` prints the predicted destination for each file without moving anything
  2. Running `classify --verbose` (or `scan --verbose`, `move --verbose`) shows which classifier matched and its confidence score
  3. JSON output for any classified file includes a `signals` array listing each classifier's result (source, score, matched)
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Bug Fixes | 1/1 | Complete    | 2026-02-28 |
| 2. Code Quality | 2/2 | Complete   | 2026-02-28 |
| 3. Test Coverage | 0/? | Not started | - |
| 4. User Features | 0/? | Not started | - |
