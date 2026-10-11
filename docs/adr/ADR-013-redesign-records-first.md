# ADR-013: Records-First Redesign; Local AI Removed

**Date**: 2026-10-11
**Status**: Accepted
**Deciders**: Project owner
**Supersedes**: [ADR-010](ADR-010-ollama-litellm-migration.md)

---

## Context

The six-signal pipeline (rules, taxonomy, embeddings, extension router, local LLM) had grown to 18.8k lines, and it moved files with no reliable undo. On the owner's records, no signal reached the 98% precision needed to move files unattended. The local models (Ollama embeddings and a local LLM, ADR-010) were slow: 78 minutes for 206 files, with frequent server disconnects. They were also the least accurate signal (17% exact).

## Decision

1. Rebuild around a small core (`para_files.core`). It runs four signals: rules, ISBN books, issuers, and an optional cloud model through litellm and OpenRouter with zero data retention. Bands decide what moves: green moves with `--apply`, yellow needs the owner's confirmation, red stays.
2. Every move is journaled before it happens; `undo` reverses a run.
3. Remove local AI entirely: no Ollama, no embeddings, no local model server.
4. Delete the old pipeline, its CLI and the Stage 1 scripts. Thema folder names ship as package data (`para_files/data/thema_l1l2.json`).

## Rationale

The tree, not the model, was the bottleneck: merging twin folders helped more than any model did. A cloud model behind the owner's confirmations gives suggestions without unattended moves. Records with stable names (payslips, statements) are filed by rules, which are exact.

## Consequences

- No model runs on the machine. The fallback needs an OpenRouter key and is optional.
- Issuers and the model stay yellow until a kind has 100 confirmed decisions.
- The source shrank to about a third of its former size; every module is reachable from the CLI.
- ADR-010 is superseded. ADR-002 and ADR-004 stay superseded.
- ADR-005 and ADR-011 are superseded; ADR-009 is amended (Thema as package data).
