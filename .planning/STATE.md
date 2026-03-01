# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01)

**Core value:** Files are classified correctly and transparently — users understand why, and failures surface loudly.
**Current focus:** Phase 6 — Extension Routing (v1.1 Inbox Throughput)

## Current Position

Phase: 6 of 7 (Extension Routing)
Plan: 3 of 3 in current phase (COMPLETE)
Status: In Progress
Last activity: 2026-03-01 — Completed plan 06-03: ExtensionRouterClassifier wired into pipeline as Signal 5

Progress: [████████░░] 78% (v1.0 complete, v1.1 phase 6/7 complete with all 3 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: 5.9 minutes
- Total execution time: 0.45 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-bug-fixes | 1 | 6 min | 6 min |
| 02-code-quality | 2 | 13 min | 6.5 min |
| 03-test-coverage | 3 | 18 min | 6 min |
| 04-user-features | 2 | 19 min | 9.5 min |

**Recent Trend:**
- Last 5 plans: 5-12 min
- Trend: stable

| 05-content-extraction | 3 | 12 min | 4 min |
| 06-extension-routing | 3 | 21 min | 7 min |

*Updated after each plan completion*
| Phase 06-extension-routing P02 | 5 | 1 tasks | 1 files |
| Phase 06-extension-routing P03 | 8 | 3 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Peek archive manifest (not extract) — extraction is slow, risky; filenames inside give strong signal
- [Phase 05-content-extraction]: Use stdlib zipfile for ZIP (no extraction, no new dependency); py7zr as optional extra for 7Z with graceful ImportError fallback
- Extension catch-all routing for media/exotic types — content unreadable; extension is definitive
- [Phase 06-extension-routing]: ExtensionRoutingConfig with PARA_FILES_EXT_ROUTING_ env prefix; confidence 0.97-0.98 for known groups, 0.80 for catch-all; empty extension returns None so pipeline continues
- [Phase 06-extension-routing P02]: No file mocking needed for pure-logic classifiers — FileMetadata constructed directly; test class per ROUTE-* requirement for 1-to-1 traceability
- [Phase 06-extension-routing P03]: ExtensionRouterClassifier runs unconditionally (no config guard) — deterministic and low-cost, no reason to make it optional
- [Phase 04-user-features]: Run all classifiers (not first-match-return) so every signal is recorded
- [Phase 04-user-features]: signals field has default_factory=list for backward compatibility
- [Phase 04-user-features]: classify --dry-run suppresses OCR rename only (no file moves)
- [Phase 05-content-extraction]: Use openpyxl read_only+data_only for xlsx/xlsm; xlrd for legacy .xls; odfpy for .ods — all lazy imports with graceful fallback
- [Phase 05-content-extraction]: Extract helper functions (_extract_*_content) to meet ruff complexity limits; PLR0911 per-file ignore for dispatch function
- [Phase 05-content-extraction]: No file format parser mocking in tests — all tests use real openpyxl/odfpy/zipfile file creation for genuine contract verification

### Pending Todos

None yet.

### Blockers/Concerns

- Deferred: pipeline.py:274 has pre-existing TRY003/EM102 ruff errors (out of scope — confirmed pre-existing before Plan 04-01)
- Deferred: pre-existing mypy unused-ignore errors in isbn_lookup.py, mlx_encoder.py, geolocation.py, pdf_metadata.py (out of scope — existed before plan 06-01)

## Session Continuity

Last session: 2026-03-01
Stopped at: Completed 06-extension-routing-03-PLAN.md (ExtensionRouterClassifier wired into pipeline as Signal 5)
Resume file: None
