# ADR-001: Use PARA Method for File Organization

**Date**: 2024-01-01
**Status**: Accepted
**Deciders**: Frédéric Jacquet

---

## Context

Users accumulate thousands of files across downloads, email attachments, scanned documents, and photos. Without a consistent organizational scheme, retrieval becomes time-consuming and files end up duplicated or lost.

Several organizational frameworks exist:
- **Flat folders** — no hierarchy, difficult at scale
- **Topic-based trees** — deep nesting, ambiguous placement
- **Date-based archives** — good for receipts, poor for resources
- **PARA method** (Tiago Forte) — four top-level buckets based on actionability

## Decision

Use the **PARA method** as the canonical file organization framework:

| Bucket | Number | Purpose |
|--------|--------|---------|
| Inbox | 0 | Unclassified files pending review |
| Projects | 1 | Active work with a defined outcome |
| Areas | 2 | Ongoing responsibilities (health, finance, home) |
| Resources | 3 | Reference material, books, docs |
| Archives | 4 | Completed projects, historical records, invoices |

## Rationale

- **Actionability-based**: PARA sorts by "how often will I need this?" rather than topic, which matches actual retrieval patterns.
- **Shallow hierarchy**: Limits nesting to 3–4 levels, preventing the "where did I put it?" problem of deep trees.
- **Well-known standard**: Documented by Tiago Forte in *Building a Second Brain*; users may already use it.
- **Automation-friendly**: The four buckets map cleanly to confidence thresholds and file types, enabling deterministic routing rules.
- **Inbox as safety net**: `0_Inbox` catches anything unclassified, ensuring no file is silently lost.

## Consequences

- All PARA destination paths start with `0_Inbox`, `1_Projects`, `2_Areas`, `3_Resources`, or `4_Archives`.
- The reference tree YAML (`personal_file_tree.yaml`) must define routes under these five buckets only.
- Users who prefer a different scheme cannot use this tool without forking the configuration model.
- The `init` command creates the five top-level folders plus common sub-paths.
