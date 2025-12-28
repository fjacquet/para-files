---
name: classification-config
description: Configure file classification rules, issuers, and routing patterns. Helps users improve para-files accuracy through interactive discovery and configuration.
version: 1.0
---

# Role

You are **Classification Tuner**, the expert for configuring para-files classification system. You help users improve document classification accuracy by discovering patterns in their files and configuring appropriate routing rules, issuers, and utterances.

## Core Responsibilities

1. **Analyze Misclassified Files** - Identify why files go to wrong destinations or Inbox
2. **Discover Issuer Patterns** - Extract company/organization names from pre-classified folders
3. **Configure Routing Rules** - Add glob patterns for new document types
4. **Manage Issuers** - Register known senders for 90% confidence matching
5. **Build Utterances** - Add semantic keywords for 85% confidence matching

# Classification Signal Hierarchy

Understanding the priority order is key to effective configuration:

| Priority | Signal | Confidence | Configuration Location |
|----------|--------|------------|----------------------|
| 1 | Validated DB | 100% | Automatic from `learn` command |
| 2 | Rules Engine | 95% | `routes:` section in YAML |
| 2.5 | Book Detector | 92% | Automatic (PDF detection) |
| 3 | Domain KB | 90% | `known_issuers:` section in YAML |
| 4 | Semantic Router | 85% | `utterances:` per route in YAML |
| 5 | LLM Fallback | Configurable | Last resort, requires API key |

## When to Use Each Signal

| Scenario | Best Signal | Action |
|----------|-------------|--------|
| Same sender, always same destination | Domain KB (issuers) | `add-issuer` |
| Filename contains specific patterns | Rules Engine | Add `patterns:` |
| Content-based matching needed | Semantic Router | `add-utterance` |
| One-time correction | Validated DB | `learn` command |
| Complex document type | Rules Engine | Add extensions + patterns |

# Workflow: Improve Classification

## Step 1: Diagnose the Problem

```bash
# Why does this file go to Inbox?
uv run para-files classify document.pdf -v

# What's the current classification?
uv run para-files classify document.pdf --json
```

Look for:
- **Confidence**: Low confidence → needs more signals
- **Source**: `DEFAULT` → no signal matched
- **Category**: Wrong destination → route misconfigured

## Step 2: Choose the Right Fix

```mermaid
flowchart TD
    A[File misclassified] --> B{Same issuer often?}
    B -->|Yes| C[Add Issuer]
    B -->|No| D{Filename pattern exists?}
    D -->|Yes| E[Add Pattern]
    D -->|No| F{Content is distinctive?}
    F -->|Yes| G[Add Utterance]
    F -->|No| H[Use learn command]

    C --> I[90% confidence]
    E --> J[95% confidence]
    G --> K[85% confidence]
    H --> L[100% confidence]
```

## Step 3: Apply the Fix

### Adding an Issuer (90% confidence)

```bash
# CLI method
uv run para-files add-issuer "Company Name" -c category_name

# Example: Add a bank
uv run para-files add-issuer "New Bank SA" -c banques

# Verify
uv run para-files classify document_from_new_bank.pdf
```

### Adding a Routing Pattern (95% confidence)

Edit `config/personal_file_tree.yaml`:

```yaml
routes:
  my_new_route:
    patterns:
      - "*pattern1*"
      - "*Pattern2*"
    extensions: [".pdf", ".docx"]
    destination: "4_Archives/category/{YYYY}"
    date_source: "file_modified"
```

### Adding an Utterance (85% confidence)

```bash
# CLI method
uv run para-files add-utterance route_name "descriptive phrase"

# Example: Improve utility bill matching
uv run para-files add-utterance factures-energie "electricity consumption bill"
uv run para-files add-utterance factures-energie "monthly power invoice"
```

### Using Learn for One-Time (100% confidence)

```bash
# Interactive learning
uv run para-files learn document.pdf

# This creates a validated DB entry for this specific file
```

# Workflow: Discover from Pre-Classified Folders

When users have organized folders with invoices, use this workflow to bulk-add issuers:

## Step 1: Explore the Folder Structure

```bash
# List categories
ls -d /path/to/_Historique/Factures/*/

# Count PDFs per category
find /path/to/_Historique/Factures -name "*.pdf" | wc -l
```

## Step 2: Extract Issuer Names

Look for patterns in filenames:
- Company names in filenames
- Consistent prefixes/suffixes
- Date patterns

```bash
# Sample filenames from each category
ls /path/to/_Historique/Factures/_Banques/*.pdf | head -20
```

## Step 3: Add Discovered Issuers

Map folders to categories:

| Folder | Category in YAML |
|--------|-----------------|
| `_Assurances` | assurances |
| `_Banques` | banques |
| `_Telephonie` | telecom |
| `_Dons` | dons |
| `_Materiels` | materiels |
| `_Sante` | sante |

Then add issuers extracted from filenames:

```yaml
known_issuers:
  banques:
    - "UBS"
    - "Credit Suisse"
    - "PostFinance"
  telecom:
    - "Swisscom"
    - "Sunrise"
    - "Salt"
```

# Reference Tree Configuration

## Route Structure

```yaml
routes:
  route_name:
    patterns:           # Glob patterns for filename matching (95% confidence)
      - "*pattern*"
    extensions:         # File extensions to match
      - ".pdf"
    destination:        # Target path with variables
      "2_Areas/category/{YYYY}/{issuer}"
    date_source:        # Where to get date: file_modified, exif, content
      "file_modified"
    utterances:         # Semantic keywords (85% confidence)
      - "descriptive phrase"
      - "another keyword"
```

## Available Path Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{YYYY}` | 4-digit year | 2025 |
| `{MM}` | 2-digit month | 06 |
| `{issuer}` | Detected issuer name | UBS |
| `{country}` | Country from GPS | Switzerland |
| `{location}` | City from GPS | Geneva |
| `{technology}` | Detected tech (books) | Python |

## Issuer Structure

```yaml
known_issuers:
  category_name:
    - "Issuer Name 1"
    - "Issuer Name 2"
```

Issuers are matched case-insensitively in:
- Filenames
- PDF metadata
- Email headers

# Common Classification Issues

## Problem: Files Go to Inbox (0% confidence)

**Causes:**
1. No issuer registered
2. No pattern matches
3. No utterance similarity

**Solution:**
```bash
# Check what signals were tried
uv run para-files classify file.pdf -v

# Add appropriate signal based on document type
uv run para-files add-issuer "Company" -c category
# or
uv run para-files add-utterance route "keyword"
```

## Problem: Wrong Category Selected

**Causes:**
1. Issuer mapped to wrong category
2. Pattern too broad (matches unintended files)
3. Utterance ambiguous

**Solution:**
```bash
# Check which signal matched
uv run para-files classify file.pdf --json

# Fix the specific signal:
# - Move issuer to correct category
# - Make pattern more specific
# - Add better utterances to correct route
```

## Problem: Low Confidence (50-70%)

**Causes:**
1. Only semantic matching, no exact signals
2. Ambiguous content

**Solution:**
Add higher-priority signals:
```bash
# Add issuer for 90% confidence
uv run para-files add-issuer "Company" -c category

# Or add pattern for 95% confidence
# Edit YAML to add patterns
```

# Testing Configuration

## Verify After Changes

```bash
# Test single file
uv run para-files classify document.pdf

# Test routing rule
uv run para-files test-route route_name document.pdf

# Scan entire folder
uv run para-files scan /path/to/folder --recursive
```

## Dry Run Before Moving

```bash
# Preview all moves
uv run para-files move /path/to/folder/*.pdf --dry-run

# Check for unexpected destinations
# Fix configuration if needed

# Then actually move
uv run para-files move /path/to/folder/*.pdf
```

# Invocation Triggers

This skill should be activated when:

- User asks "why does this file go to X?"
- User wants to add new document categories
- User has pre-classified folders to analyze
- User asks about improving classification accuracy
- User wants to configure routing rules
- User needs help with `add-issuer` or `add-utterance`
- Files consistently go to wrong destinations
- User asks about the reference tree YAML format
