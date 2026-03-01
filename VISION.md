# VISION.md — para-files

**Last updated**: 2026-03-01

---

## Mission

**Spend one weekend scanning your filing cabinet. Never file a document manually again.**

para-files is a personal document intelligence system for macOS. It classifies, names, routes, and watches over your files — so you can find what you need, know what's missing, and trust that nothing is lost.

---

## Core Principles

1. **Privacy first** — Every byte stays on your Mac. No cloud AI, no API keys, no telemetry. On-device MLX inference, on-device OCR, on-device everything.
2. **Transparency over magic** — Every decision is explainable. Users can always ask "why was this file put here?" and get a clear answer with signal sources and confidence scores.
3. **Safety over speed** — Never delete without consent. Never overwrite without warning. Dry-run by default for destructive operations. Undo is always possible.
4. **Progressive trust** — Start cautious (inbox fallback), earn confidence through corrections, become fully automatic over time. The system gets smarter as you use it.
5. **Shallow hierarchy** — PARA's four buckets keep things findable. No 8-level folder trees. No ambiguous placement decisions. Maximum 3-4 levels deep.

---

## Where We Are Today (v1.x)

para-files answers one question well: **"Where does this file go?"**

```
File arrives → Pipeline classifies → File moves to PARA destination
```

- 5-signal cascading pipeline (Rules → Books → Taxonomy → Semantic → LLM)
- Handles PDFs, Office docs, images, books, archives
- Swiss/French issuers, Thema book taxonomy, configurable YAML routing
- CLI with classify, move, scan, learn, bookstore commands
- ~80% inbox clearance on a mixed 800-file inbox

This is the **classification engine**. It works. What follows is what we build on top of it.

---

## Horizon 1 — Complete the Engine (v1.x → v2.0)

Finish inbox clearance and make the pipeline robust for daily use.

### Inbox zero workflow

A single command that processes the entire inbox — classifies, moves, renames — with progress display and a summary report. Files the system isn't confident about stay in inbox. Target: **95% of common file types routed automatically**.

### Untapped signals already on the Mac

| Signal | Value |
|--------|-------|
| **Download origin** (`xattr kMDItemWhereFroms`) | A PDF from `ubs.com` = instant issuer detection. Every browser saves this. Highest-value signal not currently used. |
| **Spotlight metadata** (`mdls`) | macOS already indexed content type, authors, title. Free metadata. |
| **Swiss QR-bill parsing** | QR code on Swiss invoices contains IBAN, creditor, amount, reference. Structured data, zero ambiguity. |
| **IBAN extraction** | Bank account numbers in text map directly to bank identity. |
| **Email parsing** (.eml, .msg) | From + Subject + Date = self-classifying files. Attachments can be extracted and classified separately. |

### Smarter classification

- **Confidence bands**: green (auto-route), yellow (suggest to user), red (inbox) — replaces binary route/inbox
- **Co-classification**: files from the same batch are likely related; if 5/8 are bank statements, the other 3 probably are too
- **Language detection**: auto-detect fr/de/en/it before keyword matching to prevent cross-language false matches

### Rename everything

Not just books. Every classified file gets a clean, standardized name:

- Invoices: `2025-03_Swisscom.pdf`
- Bank statements: `2025-02_UBS_releve.pdf`
- Photos: `2025-03-15_Lausanne.jpg`
- Contracts: `2025_Appartement_bail.pdf`

### Safety net

- **Transaction log**: every move recorded. `para-files undo` reverses the last batch.
- **Audit trail**: full decision log with timestamps, signals, scores, for debugging and learning.

---

## Horizon 2 — Know What's Missing (v2.x)

Shift from reactive (file what arrives) to **proactive** (notice what's absent).

### Recurring document tracker

The system observes that UBS sends a statement every month, the employer sends a Lohnausweis every January, CSS sends a summary every December. It builds an **expected document calendar** and alerts when something is late.

> "PostFinance: no November statement found. Last received: October 12."

### Retention advisor

Swiss law requires keeping tax documents for 10 years, contracts for 5, medical records for 20. The `retention` field already exists in `documents.json`.

`para-files retention-check` scans Archives, identifies expired documents, and suggests safe deletions with legal justification. **Never auto-deletes.**

### Completeness dashboard

Not "how many files classified?" but **"is my document life complete?"**

- Tax filing 2025: 11/12 bank statements found. February is missing.
- Property: deed, insurance, mortgage — all present. Tax assessment — missing.
- Vehicle: registration found, insurance found, service records — 0 entries.

### Tax season mode

`para-files tax-prep 2025` gathers everything needed for a Swiss tax filing, checks against a country-specific checklist, flags gaps, and generates a ready-to-send folder.

---

## Horizon 3 — Understand Relationships (v3.x)

Files are not isolated. They are connected.

### Document graph

- An invoice from Swisscom is *paid by* a debit on the BCV statement
- A rental contract is *related to* a property insurance policy
- A flight booking is *part of* a vacation project folder

Build these links (semi-automatically via issuer, date proximity, shared references) and enable:

- `para-files dossier "apartment lausanne"` — assembles all related documents from across PARA
- "Which 2024 invoices have no matching bank debit?" — unpaid invoice detection
- Timeline view: plot all documents on a date axis, see gaps and patterns

### Semantic search across PARA

Spotlight searches filenames. para-files searches **meaning**:

- "Find the plumber invoice from the kitchen renovation"
- "Everything from UBS between March and June 2024"
- "Documents mentioning more than CHF 5,000"

Powered by the same MLX embeddings used for classification, applied to the full indexed PARA tree.

---

## Horizon 4 — Serve the Household (v4.x)

### Multi-person routing

`{person}` placeholder. "This bank statement is for Marie, not Fred" — detected from the name in the document. Shared documents (property, utilities) route to common folders.

### Export packages

- `para-files export --for accountant --year 2025` — all financial documents + index spreadsheet
- `para-files export --for "insurance claim"` — photos, reports, receipts, estimates in one dated folder
- `para-files export --for estate` — master inventory, location guide, account list for next-of-kin

### Country and profession templates

- `para-files init --country switzerland` — Swiss issuers, retention rules, tax categories
- `para-files init --country france` — CAF, impôts, CPAM, mutuelle
- `para-files init --profile freelancer` — client folders, VAT, project expenses
- Community-contributed YAML packs shared as templates

---

## Horizon 5 — Invisible Infrastructure

### Watch daemon

FSEvents-based monitoring of `0_Inbox`. Files classified and moved as they arrive. Zero manual intervention. The inbox empties itself.

### Mobile intake

Photograph a receipt → iCloud sync → Inbox → classified before you get home. No dedicated app needed — iPhone camera + cloud sync + daemon.

### Teach by example

`para-files teach ~/Documents/PARA/` — scan an already-organized folder tree, learn every pattern. Cold start problem eliminated. Existing organization becomes the training data.

### Implicit learning

When a user manually moves a file out of its classified destination, that's a correction. Track it automatically. No `learn` command needed. Over time, the system calibrates itself.

---

## Strategic Position

### The privacy moat

Every competitor wants files in their cloud. para-files is **radically local**. In a world of GDPR, Swiss nDSG, and growing privacy awareness, "your files never leave your device" is a genuine differentiator that cloud-first tools cannot match.

### The Apple ecosystem bet

Apple is investing in on-device AI (Apple Intelligence, Neural Engine, Core ML). para-files is already on this train:

- MLX for embeddings (Apple Neural Engine)
- Vision Framework for OCR
- Next: SFSpeechRecognizer for audio, NaturalLanguage.framework for entity extraction
- Future: Apple's on-device LLM via API when available

Deep macOS integration is hard to replicate cross-platform. "The best file organizer for Mac" is a defensible position.

### The Second Brain bridge

PARA has a built-in community (Tiago Forte, Building a Second Brain). para-files is the **physical automation** of what they do manually. Connecting to Obsidian, Notion, or DEVONthink positions it as the intake layer for personal knowledge management.

---

## What para-files Becomes

| Horizon | Question Answered | Product Category |
|---------|-------------------|------------------|
| **1 — Engine** | "Where does this file go?" | Intelligent file router |
| **2 — Awareness** | "What am I missing?" | Personal compliance engine |
| **3 — Intelligence** | "How are my documents related?" | Personal knowledge graph |
| **4 — Household** | "Is my family's paperwork in order?" | Family document platform |
| **5 — Invisible** | *(no question — it just works)* | Ambient personal infrastructure |

---

## Reference

- [Product Requirements (PRD)](docs/prd.md) — current features and acceptance criteria
- [Architecture Decision Records](docs/adr/README.md) — key design decisions
- [Opportunities Brainstorm](docs/vision.md) — full unfiltered idea inventory
- [Roadmap](.planning/ROADMAP.md) — current milestone execution plan

---

*Classification is the foundation. Everything above is the building.*
