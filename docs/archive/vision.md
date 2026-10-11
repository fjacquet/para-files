---
title: Product Vision & Opportunities
layout: default
nav_order: 11
---

# Product Vision & Opportunities

**Date**: 2026-03-01
**Status**: Brainstorm — unsorted, unfiltered

---

## The deeper insight

para-files isn't a "file mover." It's a **personal document intelligence system**. The classification pipeline is just the engine. The real value is what you build on top of it.

Right now, para-files answers: **"Where does this file go?"**

The bigger questions it could answer:

- "What documents am I missing?"
- "What can I safely delete?"
- "Give my accountant everything she needs"
- "What happens to my files if I'm not around?"
- "Is my financial life complete and organized?"

---

## I. Life-event features

### Tax season mode

Every January, a Swiss resident needs: 12 monthly bank statements, salary certificate, insurance summaries, donation receipts, mortgage statement, pension fund statement.

`para-files tax-prep 2025` would:

- Scan the PARA tree for all 2025 financial documents
- Check against a country-specific checklist (Switzerland: Lohnausweis, Steuererklärung, 3a Bescheinigung...)
- **Flag what's missing** ("No October bank statement from BCV found")
- Generate a ready-to-send folder for the accountant or fiduciary

This alone would justify the tool for most Swiss/French taxpayers.

### Recurring document tracker

The system sees a bank sends a statement every month. An insurer sends a summary every December. An employer sends a salary certificate every January.

It builds a **calendar of expected documents** and alerts when something is late: "PostFinance: no statement received for November. Last one was October 12."

This shifts para-files from reactive (file what arrives) to proactive (notice what's missing).

### Retention advisor

Swiss law: tax documents = 10 years. Contracts = 5 years after expiry. Medical records = 20 years. Utility bills = 1 year.

`para-files retention-check` would:

- Scan Archives for expired documents
- Suggest safe deletions with legal justification
- Flag documents approaching expiry ("23 documents expire next month")
- **Never auto-delete** — just advise

The `retention` fields already exist in `documents.json`. This is data waiting to be used.

### Completeness dashboard

Not "how many files did I classify?" but **"is my document life complete?"**

- Property: deed, insurance, mortgage, tax assessment — all present?
- Vehicle: registration, insurance, service records, parking permit?
- Health: insurance card, vaccination records, prescriptions?
- Employment: contracts, salary certificates, pension statements?

This turns para-files into a **personal compliance engine**.

---

## II. Relationship intelligence

### Document linking

An invoice from Swisscom is *paid by* a bank statement from BCV. A rental contract is *related to* a property insurance policy. A flight booking is *part of* a vacation project.

If para-files understood these relationships:

- "Show me everything related to my apartment in Lausanne"
- "Which invoices from 2024 are unpaid?" (no matching bank statement found)
- "Show me the complete history of my car" (purchase, insurance, service, tax)

### Dossier assembly

`para-files dossier "apartment lausanne"` → automatically collects: rental contract, insurance policy, inventory list, landlord correspondence, deposit confirmation, utility contracts. All from scattered PARA locations into one coherent package.

### Timeline view

Every document has a date. Plot them: "Here's your financial life from 2020 to 2025." Zoom into a month. See gaps. See patterns. "You had 3 insurance claims in March 2024."

---

## III. Household & family dimension

### Multi-person routing

A household has shared AND personal documents:

- Shared: property deed, utility bills, home insurance
- Personal: salary certificates, medical records, individual bank accounts

`{person}` becomes a routing placeholder. "This bank statement is for Marie, not Fred" — detected from the name in the document.

### The inheritance folder

`para-files estate-prep` generates:

- Master inventory of all important documents
- Location guide: "Life insurance policy is in 4_Archives/assurances/..."
- Account list: banks, insurance, subscriptions (extracted from classified documents)
- Instructions for next-of-kin

---

## IV. Intelligent retrieval

### Semantic search across PARA

Classification creates rich metadata. Use it:

- "Find the plumber invoice from when we fixed the kitchen" → semantic search over all classified documents
- "Everything from UBS in 2024" → instant filter
- "Documents mentioning more than CHF 5,000" → amount-aware search

Spotlight searches filenames. para-files could search *meaning*.

### The `why` command (explainability as a feature)

`para-files why document.pdf` → full narrative:

> "This file was classified as a UBS bank statement because:
> - Downloaded from ubs.com (xattr origin)
> - Contains IBAN CH93 0024 3243... (UBS pattern)
> - Rules engine matched pattern 'relevé' + issuer 'UBS'
> - Confidence: 98%
> - Routed to: 4_Archives/banques/UBS/2025/"

Transparency *is* the feature. Users trust what they understand.

---

## V. Intake & capture

### Scanner companion

The "I just scanned 200 pages from my filing cabinet" workflow:

1. Scan everything into Inbox
2. `para-files ingest` → batch classify with progressive learning
3. First 20 files: asks a lot of questions ("Is this UBS or BCV?")
4. Next 50: asks less (patterns learned)
5. Last 130: almost fully automatic

This is the **paperless transition assistant** — a one-time life event that millions of people face.

### Mobile intake

Photograph a receipt at a restaurant → iCloud sync → appears in Inbox → classified and filed by the time you get home.

No app needed — just the standard iPhone camera + iCloud + para-files watching the inbox.

### Email attachment harvesting

"Download all attachments from my accountant's emails for the last year and classify them."

Mail.app AppleScript → extract attachments → para-files classify → done. Turns email into a document source.

---

## VI. Export & sharing

### Accountant package

`para-files export --for accountant --year 2025` generates:

- Folder with all financial documents, organized by category
- Index spreadsheet (Excel) with: filename, category, issuer, date, amount
- Cover letter template
- SHA256 checksums for integrity verification

### Insurance claim package

`para-files export --for "car insurance claim" --dates 2025-03-01:2025-03-15` gathers:

- Accident photos
- Police report
- Medical receipts
- Repair estimates
- All in a dated, indexed folder ready to send

### Backup verification

`para-files verify-backup /path/to/backup` compares the PARA tree against a backup and reports:

- Missing files
- Files modified since last backup
- New files not yet backed up

---

## VII. Country & profession templates

### Country packs

A Swiss resident's PARA tree is different from a French one. Tax categories, retention rules, issuer databases, document naming conventions — all vary by country.

- `para-files init --country switzerland` → Swiss-specific routes, issuers, retention rules
- `para-files init --country france` → French administration categories (CAF, impôts, CPAM...)
- `para-files init --country germany` → Finanzamt, Krankenkasse, etc.

### Profession packs

- **Freelancer**: client folders, project expenses, quarterly VAT, annual accounts
- **Landlord**: per-property expenses, tenant contracts, tax deductions
- **Academic**: papers by topic, grants, teaching materials, conference submissions
- **Photographer**: shoots by client, model releases, invoices, raw/edited separation

These could be **community-contributed YAML configs** shared as templates.

---

## VIII. Untapped content signals

### macOS native metadata (free, already computed)

| Signal | How | Impact |
|--------|-----|--------|
| **Spotlight metadata (`mdls`)** | `mdls -name kMDItemAuthors -name kMDItemContentType file` — macOS already indexed it | High — gives content type, authors, title for free |
| **Download origin (`xattr`)** | `com.apple.metadata:kMDItemWhereFroms` stores the URL the file was downloaded from | Huge — knowing a PDF came from `ubs.com` = instant issuer detection |
| **Finder tags** | Read existing color/text tags as input signal; write tags as output | Medium — users who already tag get a head start |
| **Quarantine flag** | `com.apple.quarantine` tells which app downloaded the file | Low — distinguishes "from Mail" vs "from Safari" |

The download origin xattr is probably the single highest-value signal not currently used. Every browser saves it.

### Document structure analysis

| Signal | How | Impact |
|--------|-----|--------|
| **Swiss QR-bill parsing** | Decode QR code in bottom-right of Swiss invoices — contains IBAN, creditor name, amount, reference | Huge for Swiss documents — structured data, zero ambiguity |
| **IBAN / account number extraction** | Regex for `CH[0-9]{2}\s?[0-9]{4}...` in text | High — maps directly to bank identity |
| **Table header detection in PDFs** | Find rows with "Date", "Amount", "Description" → financial document | High — distinguishes statements from letters |
| **Barcode/QR decoding** | zxing or pyzbar on first page image | Medium — boarding passes, tickets, parcels all have barcodes |
| **Amount + currency extraction** | Regex for CHF/EUR/USD + number patterns | Medium — confirms financial document type |
| **Address block extraction** | Detect structured addresses → identify issuer from address | Medium — works even when issuer name is in a logo |

### Richer file-type reading

| Signal | How | Impact |
|--------|-----|--------|
| **Email parsing (.eml, .msg)** | stdlib `email` module for .eml, `extract-msg` for .msg — gives From, To, Subject, Date, Body, Attachments | Huge — emails are self-classifying |
| **Email attachment extraction** | Pull attachments out of .eml/.msg and classify them separately | High — one email with 3 PDF invoices = 3 classified files |
| **EPUB full text** | PyMuPDF/ebooklib can extract chapter text, not just metadata | Medium — enables semantic classification of ebooks |
| **Apple iWork (.pages, .numbers, .key)** | Unzip (they're ZIP archives) → extract index.xml → parse | Medium — macOS-native formats should work on a macOS-only tool |
| **Audio speech-to-text** | macOS `SFSpeechRecognizer` via PyObjC — offline, free, on-device | Low-medium — voice memos become searchable |
| **Video keyframe OCR** | Extract 1 frame at 10s, OCR it — presentations/recordings have titles | Low — niche but enables routing of screen recordings |

---

## IX. Classification strategy improvements

### Pipeline architecture

| Strategy | Description | Impact |
|----------|-------------|--------|
| **Two-stage classification** | Stage 1: deterministic (rules, issuer DB) with 100% precision. Stage 2: probabilistic (semantic, LLM) with confidence bands | High — be aggressive on sure things, cautious on uncertain ones |
| **Multi-pass processing** | Pass 1: classify everything possible. Pass 2: use Pass 1 context ("5 of these 8 files are from UBS") | High — batch context is a strong signal |
| **Confidence bands** | GREEN (≥90% → auto-route), YELLOW (70-90% → suggest to user), RED (<70% → inbox) | High for UX — the "yellow zone" is where active learning happens |
| **Hierarchical classification** | First: which PARA bucket? (4-class). Then: which sub-folder? | Medium — simpler models are more accurate |
| **Parallel voting** | Run all classifiers simultaneously, pick the highest-confidence winner | Medium — catches cases where first-match is wrong |

### Signal intelligence

| Strategy | Description | Impact |
|----------|-------------|--------|
| **Temporal boosting** | Tax season (Jan-Apr) → boost tax document confidence | Medium — seasonal patterns are real |
| **Co-classification** | Files from the same batch are likely related | High — batch arrivals are common |
| **Issuer fingerprinting** | Build profiles per issuer: typical file size, page count, language, PDF creator | High — after 10 UBS statements, the 11th is obvious |
| **Language detection** | Auto-detect fr/de/en/it before keyword matching | Medium — prevents false matches across languages |
| **Negative signals** | "This is definitely NOT a book" as a first-class pipeline concept | Medium — reduces false positives |

---

## X. Learning & adaptation

| Improvement | Description | Impact |
|-------------|-------------|--------|
| **Implicit feedback capture** | When a user manually re-moves a file, that's a correction. Track it. No `learn` command needed. | Huge — passive learning without effort |
| **Teach-by-example mode** | `para-files teach ./correctly-sorted-folder/` — scan organized folders and learn patterns. Bootstrap from existing organization. | Huge — cold start eliminated |
| **Correction-based rule mining** | After N corrections, auto-generate rules: "every time you moved files from X to Y, the common pattern was Z" | High — self-improving system |
| **Confidence calibration** | Track predicted confidence vs actual accuracy. Adjust per category. | High — makes confidence scores meaningful |
| **Embedding fine-tuning** | After 100+ examples, fine-tune `nomic-embed-text` on personal vocabulary. MLX supports LoRA. | Medium-High — personalized embeddings |
| **Dynamic threshold per category** | "Insurance needs 0.9 to auto-route, photos need only 0.7" — learned from correction rates | Medium |

---

## XI. Post-classification features

| Improvement | Description | Impact |
|-------------|-------------|--------|
| **Standardized renaming for ALL types** | Invoices → `{YYYY-MM}_{Issuer}.pdf`, statements → `{YYYY-MM}_{Bank}_releve.pdf`, photos → `{YYYY-MM-DD}_{Location}.jpg` | Huge — uniform naming is the ultimate organization |
| **Finder tag injection** | Set macOS tags after move: category name as text tag, confidence as color | Medium — visible and searchable in Finder |
| **PDF metadata injection** | Set Title, Author, Subject, Keywords in PDF after classification | Medium — searchable by Spotlight and Preview |
| **Catalog/index generation** | After batch processing, output CSV/JSON/SQLite: file, category, issuer, date, confidence, signal | High — searchable file inventory |
| **Transaction log with undo** | Every move logged. `para-files undo` reverses the last batch. | High — safety net encourages bold usage |
| **Audit log** | Full decision log: timestamp, file, result, all signals, user action | High — enables learning, debugging, drift detection |

---

## XII. Integration & ecosystem

| Integration | Description | Impact |
|-------------|-------------|--------|
| **FSEvents watch daemon** | Watch `0_Inbox`, auto-classify on file arrival. Zero effort. | Huge |
| **Finder Quick Action** | Right-click → "Classify with para-files" | High |
| **Shortcuts.app action** | Expose classify/move as Shortcuts actions | Medium |
| **Raycast/Alfred extension** | Keyboard shortcut → classify selected file | Medium |
| **Mail.app rule integration** | Auto-save and classify email attachments | Medium |
| **Obsidian vault connector** | Link classified files to PKM notes | Low-Medium |

---

## XIII. Strategic positioning

### The privacy moat

Every competitor (Google Drive, Dropbox, iCloud) wants files in their cloud. para-files is **radically local**. Everything runs on the Mac. No API keys. No cloud AI. No telemetry.

In a world of increasing privacy awareness (GDPR, Swiss nDSG, CCPA), "your files never leave your device" is a genuine differentiator.

### The Apple ecosystem bet

Apple is investing heavily in on-device AI (Apple Intelligence, Neural Engine, Core ML). para-files is uniquely positioned:

- Already uses Apple Neural Engine (MLX)
- Already uses Vision Framework (OCR)
- Could use SFSpeechRecognizer (audio transcription)
- Could use NaturalLanguage.framework (entity extraction, language detection)
- Could use Apple's on-device LLM when available via API

Being "the best file organizer for Mac" is defensible because deep OS integration is hard to replicate cross-platform.

### The Second Brain connector

Tiago Forte's PARA method has a large community. para-files is the **physical implementation** of what they do manually. Connecting to Obsidian, Notion, or DEVONthink positions it as the import layer for personal knowledge management.

### The "scan once, organize forever" promise

The product pitch: **"Spend one weekend scanning your filing cabinet. Never file a document manually again."**

---

## XIV. Category transformation map

| Feature | Transforms para-files from... | Into... |
|---------|-------------------------------|---------|
| Tax prep mode | File organizer | Financial life assistant |
| Retention advisor | Static archive | Active compliance engine |
| Missing document alerts | Reactive tool | Proactive guardian |
| Document relationships | Flat file system | Knowledge graph |
| Household support | Personal tool | Family infrastructure |
| Estate prep | Current-state tool | Legacy planning tool |
| Semantic search | Classification tool | Personal search engine |
| Country/profession packs | Developer tool | Consumer product |
| Accountant export | Filing system | Professional workflow tool |
| Watch daemon | Manual CLI | Invisible infrastructure |

---

*Classification is the foundation. Everything above is the building.*
