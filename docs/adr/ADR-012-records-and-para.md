# ADR-012: Records Retention Vault Alongside PARA

**Date**: 2026-10-11
**Status**: Accepted
**Deciders**: Frédéric Jacquet

---

## Context

ADR-001 adopted PARA (Tiago Forte): Projects, Areas, Resources and Archives, organized by actionability. In PARA, Archives hold what is no longer active. PARA says nothing about retention periods.

In practice para-files grew a second job. `4_Archives` became a vault for administrative records kept for Swiss legal retention periods (CO Art. 127/128): the taxonomy classifier prefixes folders with `10y_`, `5y_`, `2y_`, `ret_` or `ctr_`. The migration to prefixed folders was never finished, so legacy folders (`factures`, `banques`, `travail`, …) sit next to their prefixed twins.

The preliminary model bake-off (2026-10-11, see the redesign spec §2) showed that no classifier reaches 98% precision on the current tree, and that merging the twins alone lifts the old rules on records from 50% to 66% exact. Knowledge material (decks, notes, configs) stays at 26–36% for every method: only the owner knows what is actionable.

## Decision

1. **Mission:** records file themselves; everything else is suggested.
2. **`4_Archives` is the retention vault.** Retention is a property of a `record` leaf (`permanent`, `ret`, `10y`, `5y`, `2y`, `ctr`); non-permanent records live at `4_Archives/<retention>_<name>`. Legacy twins merge into their prefixed folder through a reviewed, journaled migration.
3. **Four content kinds, four policies:**

   | Kind | Policy |
   |---|---|
   | `record` | moved automatically when issuer, document type and year agree, at ≥ 98% measured precision |
   | `library` | books by ISBN; vendor documentation and courses by vendor/issuer match; otherwise suggested |
   | `media` | photos and videos by extension and EXIF year |
   | `knowledge` | always suggested, never moved automatically |

4. **`0_Inbox` is the main working source.** The owner files project material by hand.
5. **Secrets** (credentials, keys, recovery phrases) are never sent off the machine and never moved by the tool.

## Rationale

- Records are deterministic (issuer + document type + date) and recurring: 29 of 110 inbox files belong to 8 recurring families. They are where "never file manually" is realistic.
- Forte's PARA keeps actionability decisions with the person; automatic moves for knowledge material contradict that and measured poorly.
- Keeping retention in folder names preserves today's on-disk layout; moving retention into the tree data (instead of classifier code) makes it consistent and checkable.
- Rejected: PARA-pure Archives (records under `2_Areas` with retention as metadata), which would mean a far larger re-org; and keeping the tree as is, which keeps classification ambiguous.

## Consequences

- Amends ADR-001: `4_Archives` means "retention vault", not "completed projects".
- The redesign spec (`docs/superpowers/specs/2026-10-10-para-files-redesign-design.md`) carries the details: leaf `kind`/`retention`, band caps by kind, secrets guard, per-kind success criteria.
- A tree-cleanup plan (twin merge, literal `{technology}`/`{year}` folders, trailing spaces) is generated in Stage 1 and applied only once the journal and `undo` exist.
- Success is measured per kind; a single overall accuracy number is no longer the target.
