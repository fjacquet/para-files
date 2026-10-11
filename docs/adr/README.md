# Architecture Decision Records

This directory contains the Architecture Decision Records (ADRs) for **para-files**.

ADRs document significant architectural choices — what was decided, why, and what the consequences are.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](ADR-001-para-method.md) | Use PARA Method for File Organization | Accepted (amended by ADR-012) |
| [ADR-002](ADR-002-apple-silicon-only.md) | Apple Silicon (macOS) Only Platform | Superseded by ADR-010 |
| [ADR-003](ADR-003-cascading-pipeline.md) | Cascading Classification Pipeline (First-Match Wins) | Accepted |
| [ADR-004](ADR-004-mlx-embeddings.md) | MLX Embeddings with nomic-embed-text-v1.5 | Superseded by ADR-010 |
| [ADR-005](ADR-005-yaml-config.md) | YAML Reference Tree for Routing Configuration | Accepted |
| [ADR-006](ADR-006-pydantic-validation.md) | Pydantic for Data Validation and Settings | Accepted |
| [ADR-007](ADR-007-typer-cli.md) | Typer for CLI Framework | Accepted |
| [ADR-008](ADR-008-uv-package-manager.md) | uv as Package Manager | Accepted |
| [ADR-009](ADR-009-thema-book-taxonomy.md) | Thema v1.6 for Book Subject Classification | Accepted |
| [ADR-010](ADR-010-ollama-litellm-migration.md) | Replace MLX with litellm/Ollama | Superseded by ADR-013 |
| [ADR-011](ADR-011-performance-optimizations.md) | Performance Optimizations | Accepted |
| [ADR-012](ADR-012-records-and-para.md) | Records Retention Vault Alongside PARA | Accepted |
| [ADR-013](ADR-013-redesign-records-first.md) | Records-First Redesign; Local AI Removed | Accepted |

## ADR Status Definitions

| Status | Meaning |
|--------|---------|
| **Proposed** | Under discussion, not yet implemented |
| **Accepted** | Decided and implemented |
| **Deprecated** | Was accepted, now superseded |
| **Superseded** | Replaced by a later ADR (link provided) |

## Adding a New ADR

1. Copy the template below as `ADR-NNN-short-title.md`
2. Fill in Context, Decision, Rationale, and Consequences
3. Add it to the index table above

### Template

```markdown
# ADR-NNN: Title

**Date**: YYYY-MM-DD
**Status**: Proposed | Accepted | Deprecated | Superseded by ADR-NNN
**Deciders**: Name(s)

---

## Context

[What is the problem? What forces are at play?]

## Decision

[What was decided?]

## Rationale

[Why was this decision made? What alternatives were rejected?]

## Consequences

[What are the positive and negative outcomes of this decision?]
```
