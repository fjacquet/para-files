# ADR-003: Cascading Classification Pipeline (First-Match Wins)

**Date**: 2024-01-01
**Status**: Accepted
**Deciders**: Frédéric Jacquet

---

## Context

File classification can be approached in several ways:

1. **Single classifier** — one model predicts the category for all files.
2. **Ensemble / voting** — multiple classifiers vote and the majority wins.
3. **Cascading pipeline** — classifiers are tried in confidence order; the first match wins.

The system needs to handle very different file types (invoices, photos, books, source code, spreadsheets) with varying amounts of signal available (filename only, full text, ISBN, EXIF data).

## Decision

Use a **cascading pipeline** where classifiers are sorted by confidence (highest first). The first classifier that returns a result above its threshold wins; lower-priority classifiers are not called.

```
Signal 1 (100%) → Signal 2 (95%) → Signal 3 (92%) → Signal 4 (90%) → Signal 5 (85%) → Signal 6 (LLM) → Inbox
```

## Rationale

### Determinism and Debuggability

Cascading pipelines are easy to trace: "this file was classified by the rules engine because rule `factures-edf` matched." Ensemble models produce opaque probability distributions that are harder to explain to users.

### Cost Tiering

Signals increase in computational cost as confidence decreases:
- **Signal 1 (Validated DB)**: O(1) dictionary lookup — free.
- **Signal 2 (Rules Engine)**: Glob pattern matching — microseconds.
- **Signal 3 (Book Detector)**: ISBN extraction + HTTP lookup — 100ms–2s.
- **Signal 4 (Taxonomy Classifier)**: MLX embedding — 50–200ms (cached model).
- **Signal 5 (LLM Fallback)**: Ollama inference — 1–5s.

The cascade ensures expensive classifiers run only when cheaper ones fail.

### Incremental Improvement

New classifiers can be inserted at any priority without changing other classifiers. The `ClassificationSource` enum registers each signal; the pipeline iterates them in order.

### User Trust

High-confidence results (validated DB, explicit rules) are never overridden by probabilistic signals. A user who has manually tagged an issuer will never see that issuer re-classified by a lower-ranked heuristic.

## Consequences

- Each classifier must implement a `classify(metadata: FileMetadata) -> ClassificationResult | None` interface.
- Classifiers returning `None` pass control to the next stage.
- `ClassificationResult.confidence.source` records which classifier won, enabling auditability.
- A classifier bug that returns a low-confidence match can block more accurate downstream classifiers — thresholds must be set carefully.
- The Inbox fallback at the end guarantees a result is always returned.
