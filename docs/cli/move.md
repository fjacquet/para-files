---
title: move Command
layout: default
parent: CLI Reference
nav_order: 3
---

# move Command

Classify files and move them to their PARA destinations.

## Basic Usage

```bash
# Single file
uv run para-files move document.pdf

# Multiple files
uv run para-files move file1.pdf file2.docx file3.txt

# All PDFs in folder
uv run para-files move ~/Downloads/*.pdf
```

## Essential Options

### `--dry-run`

Preview where files will go WITHOUT moving them:

```bash
# Always do this first!
uv run para-files move *.pdf --dry-run
```

Output shows destination but doesn't move files.

### `--copy`

Copy files instead of moving:

```bash
# Create copy in PARA, keep original
uv run para-files move document.pdf --copy
```

### `--conflict`

Handle duplicate filenames. Options:

- `skip` - Don't move if file exists at destination
- `overwrite` - Replace existing file
- `rename` - Add number suffix (file.pdf → file_1.pdf)
- `rename_with_date` - Add date prefix (2024-01-15_file.pdf)

```bash
# Don't overwrite existing files
uv run para-files move *.pdf --conflict skip

# Rename duplicates
uv run para-files move *.pdf --conflict rename
```

### `--skip-unclassifiable`

Don't warn about files that go to Inbox (0_Inbox):

```bash
uv run para-files move *.pdf --skip-unclassifiable
```

## Advanced Options

### `--date-prefix`

Add date prefix to moved files:

```bash
# file.pdf → 2024-01-15_file.pdf
uv run para-files move *.pdf --date-prefix
```

### `--cleanup-empty`

Remove empty directories after moving:

```bash
uv run para-files move ~/Downloads/*.pdf --cleanup-empty
```

## Output Formats

### Text Output (Default)

```bash
uv run para-files move *.pdf
# Shows: File → Destination (Status)
```

### JSON Output

```bash
uv run para-files move *.pdf --json
# Structured results for scripting
```

### Verbose

```bash
uv run para-files move *.pdf -v
# Shows detailed info including confidence, source signal, etc.
```

## Examples

### Safe Move Workflow

```bash
# 1. Always preview first
uv run para-files move ~/Downloads/*.pdf --dry-run

# 2. Check output carefully

# 3. If satisfied, actually move
uv run para-files move ~/Downloads/*.pdf
```

### Batch Move with Options

```bash
# Move, rename duplicates, clean up empty dirs
uv run para-files move ~/Downloads/*.pdf --conflict rename --cleanup-empty

# Copy instead of move (keeps original)
uv run para-files move ~/Downloads/*.pdf --copy
```

### Handle Duplicates

```bash
# Skip files if they already exist at destination
uv run para-files move *.pdf --conflict skip

# Rename duplicates with date
uv run para-files move *.pdf --conflict rename_with_date
```

### Unclassifiable Files

```bash
# Files with low confidence go to 0_Inbox
# Suppress warnings about them
uv run para-files move *.pdf --skip-unclassifiable
```

## How move Works

1. **Classifies** each file (using 6-signal pipeline)
2. **Determines** destination folder
3. **Creates** destination folders if they don't exist
4. **Moves** (or copies) the file
5. **Reports** success/failure

## Related Commands

- **[classify](classify.md)** - Preview classifications without moving
- **[scan](scan.md)** - Preview all classifications in a directory
- **[init](init.md)** - Pre-create PARA folder structure

## Troubleshooting

**"File already exists"?**
Use `--conflict rename` or `--conflict overwrite`

**"Permission denied"?**
Check folder permissions. You need write access to destination.

**Files went to Inbox?**
Low confidence classification. See [Troubleshooting](../troubleshooting/files-going-to-inbox.md).
