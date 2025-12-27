---
title: Classify Your First File
layout: default
parent: Getting Started
nav_order: 3
---

# Classify Your First File

A step-by-step walkthrough of your first classification.

## Prerequisites

You've already:
1. [Installed para-files](installation.md)
2. [Set up quick configuration](quick-setup.md) with `PARA_FILES_PARA_ROOT` set

## Let's Start

### 1. Find a Test File

Use any document you have:
```bash
# Example files to try
~/Downloads/invoice.pdf
~/Documents/receipt.jpg
~/Desktop/contract.docx
```

### 2. See the Classification

```bash
uv run para-files classify ~/Downloads/invoice.pdf
```

Output shows:
```
File: invoice.pdf
Category: 4_Archives/factures/2024
Confidence: 85% (Semantic Router)
```

This means:
- **Category**: Where the file would be moved
- **Confidence**: How sure para-files is (85%)
- **Source**: Which signal made the decision (Semantic Router = MLX embedding match)

### 3. Understand the Confidence Level

| Confidence | Source | Meaning |
|-----------|--------|---------|
| 100% | Validated DB | You've manually approved this classification before |
| 95% | Rules Engine | Matches a filename/path pattern |
| 92% | Book Detector | Identified as a technical book |
| 90% | Domain KB | Matches a known issuer (bank, company) |
| 85% | Semantic Router | Matched via ML embeddings |
| Variable | LLM Fallback | AI classification (if enabled) |

Lower confidence = less certain. High confidence = very sure.

### 4. Try Different Files

Test with various documents:

```bash
# Multiple files at once
uv run para-files classify *.pdf

# See detailed matching info
uv run para-files classify invoice.pdf -v  # Verbose mode

# Get JSON output (for scripts)
uv run para-files classify invoice.pdf --json
```

### 5. Preview Before Moving

Always preview first:

```bash
# See where it WOULD go (doesn't move anything)
uv run para-files move ~/Downloads/invoice.pdf --dry-run

# Output shows the destination
```

### 6. Actually Move a File

Once you're confident:

```bash
# Move single file
uv run para-files move ~/Downloads/invoice.pdf

# Check your PARA folder
ls -la ~/Documents/PARA/4_Archives/factures/2024/
```

## What Happened?

Para-files:
1. **Analyzed** the file (name, type, content preview)
2. **Ran through 6 signals** in order, stopping at the first match
3. **Found a match** at signal 4 (Semantic Router) with 85% confidence
4. **Moved** the file to the destination folder

## Next Steps

- **[All CLI Commands](../cli/overview.md)** - Learn every command
- **[Move Files Guide](../tasks/move-files.md)** - Advanced moving options
- **[Manage Issuers](../tasks/manage-issuers.md)** - Add your banks/companies
- **[Architecture](../architecture/overview.md)** - Understand the 6-signal pipeline

## Troubleshooting

**File went to Inbox (0_Inbox)?**
No signals matched. See [Files Going to Inbox](../troubleshooting/files-going-to-inbox.md).

**Confidence too low?**
See [Low Confidence Scores](../troubleshooting/confidence-too-low.md).

**Wrong category?**
You can improve matching by:
- Adding the issuer: `uv run para-files add-issuer "Company Name" -c category`
- Adding utterances: `uv run para-files add-utterance route "describe what this file is about"`
- Using [Interactive Learning](../tasks/learn-from-files.md)
