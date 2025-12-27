---
title: Scan Directory Before Moving
layout: default
parent: Tasks
nav_order: 9
---

# Scan a Directory Before Moving

Preview all classifications for a folder without moving.

## Basic Scan

```bash
# Scan Downloads
uv run para-files scan ~/Downloads

# Scan recursively (subdirectories)
uv run para-files scan ~/Downloads --recursive
```

## See Results

Shows each file and where it would go.

## Useful For

- Preview before big move operation
- Check confidence levels
- Find unclassifiable files
- Get overview of what needs organizing

## Options

### Recursive Scan

```bash
uv run para-files scan ~/Downloads --recursive

# Scans all subdirectories too
```

### Filter by Extension

```bash
uv run para-files scan ~/Downloads --ext .pdf

# Only PDFs
```

### JSON Output

```bash
uv run para-files scan ~/Downloads --json

# Shows statistics: file counts per category, etc.
```

## Examples

### Preview Downloads

```bash
# What would happen to all my downloads?
uv run para-files scan ~/Downloads --recursive --json

# See how many go to each category
```

### Find Problem Files

```bash
# Which files might have issues?
uv run para-files scan ~/Downloads -v

# Verbose shows confidence for each
```

## Workflow

```bash
# 1. Scan to see what would happen
uv run para-files scan ~/Downloads --json

# 2. Review the output

# 3. If satisfied, move them
uv run para-files move ~/Downloads/*.pdf
```

## Related

- **[scan Command](../cli/scan.md)** - Full reference
- **[Move Files](move-files.md)** - Actually move them
- **[classify Command](../cli/classify.md)** - Single files
