---
title: Product Requirements Document
layout: default
nav_order: 10
---

# Product Requirements Document — para-files

**Version**: 1.1
**Date**: 2026-03-01
**Author**: Frédéric Jacquet
**Status**: Active

---

## 1. Product Overview

**para-files** is a macOS-only (Apple Silicon) intelligent file classification CLI that automatically organizes files into a structured PARA folder hierarchy. It uses a cascading 6-signal classification pipeline — from deterministic rules through MLX-powered semantic embeddings — to route documents, books, invoices, photos, and other files to their correct destination with high accuracy and full transparency.

### Core Value Proposition

> Files are classified correctly and transparently — users understand *why* a file was placed where it was, and failures surface loudly rather than silently misfiling.

---

## 2. Problem Statement

Knowledge workers accumulate thousands of files across email attachments, downloads, scanned documents, and synced cloud folders. Without an automated classification system:

- Files pile up in an undifferentiated inbox, making retrieval slow.
- Manual sorting is time-consuming, error-prone, and abandoned under load.
- Duplicate files are created across devices.
- Important financial documents, contracts, and records become unfindable.

Existing tools either require cloud services (with privacy implications), are platform-agnostic with poor Apple Silicon performance, or provide no semantic understanding of content.

---

## 3. Target Users

### Primary User: Personal Knowledge Worker on macOS

- Uses Apple Silicon Mac (M1–M4)
- Manages a personal PARA folder in iCloud Drive, OneDrive, or local filesystem
- Processes 100–1,000 files per session (downloads, email attachments, scans)
- Comfortable with CLI tools and YAML configuration
- Values privacy — no files leave the device

### Secondary User: Power User / Developer

- Wants to extend classification with custom routing rules
- May integrate `para-files` into automation scripts or Hazel/Folder Action workflows
- Needs programmatic output (JSON) for downstream processing

---

## 4. Goals and Non-Goals

### Goals

- **Automate** classification of common file types (PDFs, Office docs, books, photos, archives)
- **Minimize inbox residue** — after a run, ≥80% of files should be correctly moved
- **Preserve user trust** — high-confidence signals always win; never silently override a user-validated mapping
- **Explain decisions** — every classification has a traceable source (which signal matched, with what score)
- **Support learning** — users can correct mistakes; corrections are remembered permanently
- **Run offline** — no API keys, no internet required after initial model download

### Non-Goals

- Cross-platform support (Linux, Windows)
- GUI application
- Cloud storage integration beyond filesystem sync
- Real-time filesystem watching (daemon mode)
- Multi-user or enterprise deployment
- Automatic deletion of files

---

## 5. Features

### 5.1 Classification Pipeline (v1.0 — Complete)

The core 6-signal cascading pipeline classifies any file by trying each signal in order:

| Signal | Priority | Confidence | Description |
|--------|----------|------------|-------------|
| Validated DB | 1 | 100% | User-confirmed issuer → category mappings |
| Rules Engine | 2 | 95% | Glob patterns on filename, path, issuer |
| Book Detector | 3 | 92–100% | PDF/EPUB/CHM/MOBI detection via ISBN + metadata |
| Taxonomy Classifier | 4 | 90% | Issuer category matching from reference tree |
| Semantic Router | 5 | 85% | MLX embedding similarity to route utterances |
| LLM Fallback | 6 | Configurable | Optional Ollama-based AI classification |
| Inbox Fallback | — | 0% | Unclassified files land in `0_Inbox` |

**Acceptance criteria:**
- Each signal returns `ClassificationResult | None`
- A signal raising an exception is skipped; the pipeline continues
- The winning signal is recorded in `ClassificationResult.confidence.source`
- `--verbose` flag displays per-signal scores in the CLI output

### 5.2 CLI Commands (v1.0 — Complete)

| Command | Description |
|---------|-------------|
| `classify <file>` | Show predicted category without moving |
| `move <files>` | Move files to their PARA destinations |
| `scan <directory>` | Preview classifications for all files in a folder |
| `learn <file>` | Interactively correct a misclassification |
| `add-issuer <name> -c <cat>` | Register a new issuer permanently |
| `add-utterance <route> <phrase>` | Add a semantic matching phrase to a route |
| `tree` | Display the PARA folder tree |
| `routes` | List all configured routes |
| `issuers` | List all known issuers by category |
| `config` | Show current configuration values |
| `init` | Create the PARA folder structure |
| `clean` | Remove known junk files |
| `bookstore` | Scan and organize book files with ISBN lookup |
| `dedupe` | Find and remove duplicate files |
| `migrate` | Migrate files between PARA versions |
| `rescan` | Re-classify files already in PARA |

**All move-type commands support `--dry-run`** for preview without side effects.

### 5.3 Book Detection and Classification (v1.0 — Complete)

Dedicated signal for PDF/EPUB/CHM/MOBI files:

- **ISBN extraction** — searches text content for ISBNs, validates with isbnlib
- **External lookup** — queries Google Books and Open Library for title/author/subject
- **Thema v1.6 taxonomy** — 9,187 subject codes used to build hierarchical paths
- **Path format**: `3_Resources/livres/{L1_Code_ShortName}/{L2_Code_ShortName}`
- **Parallel processing** — `bookstore` command uses configurable worker threads (default: 8)
- **File renaming** — books renamed to `Author - Title (Year).ext` format

### 5.4 Content Extraction (v1.1 — Partially Complete)

Extended content reading for non-PDF formats:

- **Excel/ODS** (✓ Complete): Sheet names and cell values extracted for semantic classification
- **ZIP/7Z** (Pending): Archive manifest (filenames inside) used as classification signal
- **Graceful fallback**: extraction failures fall through to the next signal, never crash

### 5.5 Extension-Based Routing (v1.1 — Pending)

Catch-all routing for file types where content is not extractable:

- **Video** (.3gp, .m4v, .mp4, .mov) → fixed media folder
- **Audio** (.m4a, .mp3) → fixed media folder
- **Images** (.gif, .tif, .psd) → fixed media folder
- **Security files** (.p7b, .asc, .kdbx) → dedicated security folder
- **Scripts** (.ps1, .css, .js, .sh) → scripts/dev folder
- **Exotic/unknown** → catch-all folder (not left in Inbox)

### 5.6 Inbox Processing UX (v1.1 — Pending)

One-shot inbox workflow:

- **Single command** processes the entire inbox directory
- **Conservative routing** — files the pipeline cannot classify confidently stay in Inbox
- **Progress display** — file count, current file, destination shown during processing
- **Post-run summary** — total processed, moved, stayed, breakdown by signal source

### 5.7 Feedback-Based Learning (v1.0 — Complete)

- `learn` command prompts the user to confirm or correct a classification
- Corrections stored in a persistent validated DB (SQLite)
- Validated DB is Signal 1 — confirmed mappings are never overridden by heuristics
- Supports batch learning after inbox processing runs

### 5.8 Configuration (v1.0 — Complete)

Four-level priority stack:

```
Environment variables (PARA_FILES_*) > .env file > YAML config section > Defaults
```

Key configuration options:

| Setting | Default | Description |
|---------|---------|-------------|
| `PARA_FILES_PARA_ROOT` | `~/Documents/PARA` | Root of PARA folder tree |
| `mlx.model_name` | `nomic-text-v1.5` | MLX embedding model |
| `mlx.score_threshold` | `0.75` | Minimum semantic similarity score |
| `llm.enabled` | `false` | Enable LLM fallback |
| `llm.model` | `ollama/qwen2.5:1.5b` | LLM model for fallback |

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Metric | Target |
|--------|--------|
| Single file classification (rules engine hit) | < 50ms |
| Single file classification (semantic match) | < 300ms (model warm) |
| Single file classification (book + ISBN lookup) | < 3s (network dependent) |
| Bookstore parallel throughput | ≥ 8 books/minute |
| MLX model load time (cold) | < 5s |
| Inbox batch (100 files, no ISBN) | < 30s |

### 6.2 Accuracy

| Signal | Target Precision |
|--------|-----------------|
| Validated DB | 100% (user-confirmed) |
| Rules Engine | ≥ 95% |
| Book Detector (with ISBN) | ≥ 99% |
| Book Detector (metadata only) | ≥ 85% |
| Semantic Router | ≥ 80% |
| Overall (mixed inbox) | ≥ 80% correctly classified |

### 6.3 Reliability

- No file is deleted without explicit user instruction
- `--dry-run` must never move files under any circumstances
- Pipeline exceptions are isolated — one bad file does not block processing of others
- PARA root is validated to exist before any move operation

### 6.4 Observability

- All classification decisions logged at INFO level with signal source and confidence
- `--verbose` flag shows per-signal breakdown in CLI output
- JSON output mode includes `signals` array for programmatic consumption
- Errors logged at WARNING or ERROR level with exception type and message

### 6.5 Code Quality

- Python 3.12+ with strict mypy type checking
- Ruff linting (line length 100) and formatting
- Test coverage ≥ 79% (enforced in CI)
- All public functions have docstrings
- No bare `except Exception:` — typed exception handlers required

---

## 7. System Constraints

| Constraint | Value |
|-----------|-------|
| **Platform** | macOS, Apple Silicon (M1–M4) only |
| **Python version** | 3.12+ |
| **Package manager** | uv |
| **Internet required** | First run only (model download ~270MB); ISBN lookups optional |
| **Disk** | ~300MB for MLX model cache |
| **Memory** | ~500MB during active classification (MLX unified memory) |

---

## 8. User Stories

### Epic 1: Basic Classification

- **US-001**: As a user, I can run `para-files classify document.pdf` and see the predicted PARA category and which signal matched, so I can trust the result.
- **US-002**: As a user, I can run `para-files move *.pdf --dry-run` to preview where files will go before committing.
- **US-003**: As a user, I can run `para-files move *.pdf` to move files to their correct PARA folders automatically.

### Epic 2: Book Management

- **US-010**: As a user, I can run `para-files bookstore ~/Downloads` to have all books identified, renamed, and moved to `3_Resources/livres/` with subject sub-folders.
- **US-011**: As a user, books are organized by Thema subject (e.g., `UB_Programmation`, `JM_Psychologie`) so I can browse by topic.

### Epic 3: Learning

- **US-020**: As a user, I can run `para-files learn wrong_file.pdf` to correct a misclassification and ensure it never happens again for that issuer.
- **US-021**: As a user, I can run `para-files add-issuer "My Bank" -c banques` to register a new issuer permanently.

### Epic 4: Inbox Processing (v1.1)

- **US-030**: As a user, I can run a single command to process my entire inbox, moving everything that can be confidently classified and leaving the rest in place.
- **US-031**: As a user, I see a progress bar and a summary at the end showing how many files moved, how many stayed, and which signals were responsible.
- **US-032**: As a user, Excel files are classified by their content (sheet names, cell values) rather than just filename.
- **US-033**: As a user, ZIP archives are classified by listing their internal files, not just by filename.

### Epic 5: Configuration

- **US-040**: As a user, I can define custom routing rules in `personal_file_tree.yaml` using glob patterns and semantic utterances without editing Python code.
- **US-041**: As a user, I can set `PARA_FILES_PARA_ROOT` as an environment variable to change the root folder without editing any config file.

---

## 9. Roadmap

### v1.0 (Complete — 2025)

- 6-signal classification pipeline
- All core CLI commands
- Book detection with Thema taxonomy
- Feedback-based learning
- Filename sanitization
- Signal transparency (--verbose, JSON signals)

### v1.1 (Active — 2026-Q1)

- Excel/ODS content extraction ✓
- ZIP/7Z archive manifest reading
- Extension-based catch-all routing (media, security, scripts)
- One-shot inbox processing command with progress + summary

### v2.0 (Planned)

- ISBN lookup caching (reduce external API calls)
- Async bookstore processing
- MLX local model path support (offline mirror)
- Embedding LRU cache
- Batch learning UI (review low-confidence moves interactively)

---

## 10. Out of Scope

| Feature | Reason |
|---------|--------|
| Windows / Linux support | MLX requires Apple Silicon; intentional constraint |
| GUI application | CLI is the target interface; GUI adds complexity |
| Real-time filesystem watching | Hazel/Folder Actions cover this use case |
| Archive extraction before classification | Too slow and potentially destructive |
| Cloud service integration | Privacy constraint — no files leave the device |
| Multi-user / enterprise | Single-user personal tool by design |
| Automatic file deletion | Safety constraint — users must explicitly delete |

---

## 11. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Inbox clearance rate | ≥ 80% of files moved correctly | Manual review of 100-file sample |
| False positive rate | ≤ 5% (files moved to wrong folder) | Manual audit |
| Rule engine hit rate | ≥ 60% of files handled by rules (no ML needed) | `--verbose` signal stats |
| User corrections per 100 files | ≤ 5 (after learning phase) | `learn` command invocations |
| Classification latency (p95) | ≤ 500ms per file | CLI timing output |
