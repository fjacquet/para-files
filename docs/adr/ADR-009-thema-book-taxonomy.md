# ADR-009: Thema v1.6 for Book Subject Classification

**Date**: 2024-06-01
**Status**: Accepted
**Deciders**: Frédéric Jacquet

---

## Context

Technical books (PDFs, EPUBs, CHMs, MOBIs) are a significant portion of files requiring classification. Books need to be routed not just as "books" but into meaningful subject sub-folders:

```
3_Resources/livres/
  U_Informatique/
    UB_Programmation/
    UY_Intelligence_Artificielle/
  P_Mathematiques/
  J_Sciences_Sociales/
```

Options for subject taxonomy:
- **Custom keyword mapping** — ad hoc, incomplete, not standardized
- **Dewey Decimal Classification** — very granular, not designed for digital use
- **Library of Congress Subject Headings (LCSH)** — authoritative but complex
- **Thema** — international standard for book trade, designed for digital workflows

## Decision

Use **Thema v1.6** (9,187 subject codes) as the canonical book classification taxonomy, loaded from `config/thema.json`.

## Rationale

### Industry Standard

Thema is maintained by EDItEUR and is the international standard used by publishers and book retailers for metadata exchange. ISBN lookup APIs (Google Books, Open Library) often return Thema-aligned subjects.

### Hierarchical Structure

Thema codes are hierarchical: `U` → `UB` → `UBJ` (Python), allowing classification at the appropriate granularity. The path builder uses at most 2 levels for readable folder names.

### Hybrid Path Naming

Folder names combine the code and a short human-readable label:

```
U_Informatique/UB_Programmation
```

This makes folders both machine-sortable (by code prefix) and human-readable without opening a codebook.

### Accent Removal

Thema descriptions use accented French characters (standard ISO). Path components have accents removed (`é→e`, `ç→c`) to ensure filesystem compatibility:

```
"Arts : généralités" → "Arts_generalites"
```

### Scope

The `thema.json` covers 9,187 codes but the system uses only the top 2 levels (single letter + 2-letter codes) for path construction, giving ~200 practical categories.

## Consequences

- `config/thema.json` must be bundled with the package distribution.
- `ThemaTaxonomy` loads and indexes the JSON at startup.
- Subject detection uses keyword matching against Thema code descriptions — not ML classification.
- Books without a detectable Thema subject default to `G` (Reference/General) rather than `U` (Computing).
- The `bookstore` command lists classified books with their Thema codes for user review.
- Adding new subject keywords requires editing `book_detector.py`'s keyword mapping, not the Thema JSON itself.
