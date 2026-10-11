# ADR-014: Model First; Pinned Rules Decide, Other Rules Are Hints

**Date**: 2026-10-11
**Status**: Accepted
**Deciders**: Project owner
**Amends**: [ADR-013](ADR-013-redesign-records-first.md)

---

## Context

The first real inbox run (153 files) showed that filename rules dominated: 111 files were decided by a filename glob at confidence 1.0, the model saw only 14 leftovers, and 85 of 122 suggestions went to a catch-all folder. A rule such as `*[Ii][Ss][Ee]*` matched "Viseca" and filed a card invoice as Cisco documentation. An evaluation of the 320 rules (5,313 globs) against the existing tree found 67 reliable rules (specific banks, statement types, publishers, photos) and 23 below 50% agreement (topic words and short fragments).

## Decision

1. The model reads every non-secret file first: name, type, metadata, text (including OCR), with rule, book-heuristic and issuer matches as hints.
2. Only a verified ISBN book or a rule marked `pin: true` (or `pin: exif` with an EXIF date) decides without the model.
3. With no key or no answer, the first hint is a yellow suggestion; hints never move a file alone.
4. Review goes folder by folder; the owner's decisions become examples in the prompt.

## Rationale

Content tells an invoice from a datasheet; a filename often does not. Rules stay where they are reliable (they are cheap and exact), and become context everywhere else. Safety is unchanged: secrets are never sent, the model stays yellow until a kind has 100 confirmed decisions, knowledge is never green, every move is journaled and undoable.

## Consequences

- About $5 per 1000 files sent to the model; the cache makes a preview followed by an apply cost one call per file.
- Unpinned rules no longer move files with `--apply` (breaking): the owner pins the rules they trust.
- `PARA_FILES_ISSUERS_GREEN` is removed.
