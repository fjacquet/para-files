---
title: scan Command
layout: default
parent: CLI Reference
nav_order: 4
---

# scan Command

Preview file classifications for an entire directory without moving files.

## Basic Usage

```bash
# Scan single directory
uv run para-files scan ~/Downloads

# Scan recursively (all subdirectories)
uv run para-files scan ~/Downloads --recursive
```

## Options

### `--recursive`

Scan subdirectories too:

```bash
# Scan Downloads and all subdirectories
uv run para-files scan ~/Downloads --recursive
```

### `--ext`

Filter by file extensions:

```bash
# Only PDFs
uv run para-files scan ~/Downloads --ext .pdf

# Multiple extensions
uv run para-files scan ~/Downloads --ext ".pdf,.docx,.xlsx"
```

### `--json`

Output as JSON with statistics:

```bash
uv run para-files scan ~/Downloads --json

# Shows count of files per category, confidence distribution, etc.
```

## Examples

### Preview Downloads Folder

```bash
# What would happen if I moved all these files?
uv run para-files scan ~/Downloads --recursive --json
```

Output shows:

- How many files would go to each category
- Average confidence score
- Any unclassifiable files

### Filter by File Type

```bash
# Only PDFs
uv run para-files scan ~/Downloads --ext .pdf

# Only office documents
uv run para-files scan ~/Downloads --ext ".pdf,.docx,.xlsx"

# Only images (for photo organization)
uv run para-files scan ~/Downloads --ext ".jpg,.png,.heic"
```

### Find Problem Files

```bash
# Scan recursively with verbose output
uv run para-files scan ~/Downloads --recursive -v

# Look for files with low confidence (< 70%)
```

## What scan Does

1. **Scans** directory (optionally recursive)
2. **Classifies** each file
3. **Reports** categories and confidence
4. **Does NOT move** anything

Perfect for:

- Previewing before batch moves
- Finding unclassifiable files
- Checking classification confidence
- Planning folder organization

## Next Steps

- **[move](move.md)** - Actually move files based on classifications
- **[classify](classify.md)** - Classify individual files
- **[Tasks: Batch Classify](../tasks/batch-classify.md)** - Guide for bulk operations
