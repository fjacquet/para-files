---
title: Classify Multiple Files
layout: default
parent: Tasks
nav_order: 3
---

# Classify Multiple Files

Classify a batch of files at once without moving them.

## Basic Batch Classification

```bash
# Classify all PDFs
uv run para-files classify *.pdf

# Classify multiple file types
uv run para-files classify *.pdf *.docx *.xlsx

# Classify from specific folder
uv run para-files classify ~/Downloads/*.pdf
```

## View Results

### Text Output

```bash
uv run para-files classify *.pdf

# Shows each file and its category
```

### JSON Output

Save results for processing:

```bash
uv run para-files classify *.pdf --json > results.json

# Each file's category is JSON formatted
```

### Verbose Output

See details for all files:

```bash
uv run para-files classify *.pdf -v

# Shows confidence and signal source for each
```

## Use Cases

### Preview Folder Before Moving

```bash
# Check what would happen to all Downloads files
uv run para-files classify ~/Downloads/*.pdf

# Review output before moving
```

### Process Large Directory

```bash
# Classify everything in a folder
uv run para-files classify ~/Archive/**/*.pdf

# Get overview of what needs organizing
```

### Export Classifications

```bash
# Save classifications for records
uv run para-files classify *.pdf --json > classifications.json

# Use elsewhere (import to spreadsheet, etc.)
```

## Patterns

### All PDFs in Downloads

```bash
uv run para-files classify ~/Downloads/*.pdf
```

### All Documents

```bash
uv run para-files classify ~/Downloads/*.{pdf,docx,xlsx,pptx}
```

### Recursive (Subdirectories)

```bash
# Use scan command instead for directories
uv run para-files scan ~/Downloads --recursive
```

## Next Steps

- **[Move Multiple Files](move-files.md)** - Actually move them
- **[Scan Directory](../cli/scan.md)** - Preview a whole directory
- **[Classify Command](../cli/classify.md)** - Full reference

