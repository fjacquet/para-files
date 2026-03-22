# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-22)

**Core value:** Files are classified correctly and transparently — users understand why, and failures surface loudly.
**Current focus:** Milestone v1.2 — Reliability & Performance

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-22 — Milestone v1.2 started

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Pipeline short-circuit: break after first classifier match instead of running all 6
- LLM timeout: 15s default via PARA_FILES_LLM_TIMEOUT, graceful Ctrl+C handling
- Migrated from MLX to litellm/Ollama for embeddings and LLM

### Pending Todos

None yet.

### Blockers/Concerns

- Deferred: pipeline.py:274 has pre-existing TRY003/EM102 ruff errors (out of scope — confirmed pre-existing before v1.1)
- Deferred: pre-existing mypy unused-ignore errors in isbn_lookup.py, mlx_encoder.py, geolocation.py, pdf_metadata.py

## Session Continuity

Last session: 2026-03-22
Stopped at: Defining v1.2 requirements
Resume file: None
