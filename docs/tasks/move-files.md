---
title: Move Files to PARA
layout: default
parent: Tasks
nav_order: 4
---

# Move Files to PARA Folders

Move classified files to their PARA destinations.

## Basic Move

```bash
# Single file
uv run para-files move document.pdf

# Multiple files
uv run para-files move *.pdf

# Entire folder
uv run para-files move ~/Downloads/*.pdf
```

## CRITICAL: Always Preview First

```bash
# ALWAYS do this before moving!
uv run para-files move *.pdf --dry-run

# Review where files would go
# Check for any issues
# Only if satisfied, run without --dry-run
```

## Safe Move Workflow

```bash
# Step 1: Preview
uv run para-files move ~/Downloads/*.pdf --dry-run
# → Review output carefully

# Step 2: Move with options
uv run para-files move ~/Downloads/*.pdf --conflict rename

# Step 3: Verify
ls -la ~/Documents/PARA/
```

## Handling Duplicates

Files that already exist at destination:

```bash
# Skip them
uv run para-files move *.pdf --conflict skip

# Rename (add number suffix)
uv run para-files move *.pdf --conflict rename

# Rename with date prefix
uv run para-files move *.pdf --conflict rename_with_date

# Overwrite (careful!)
uv run para-files move *.pdf --conflict overwrite
```

## Copy Instead of Move

Keep original file:

```bash
uv run para-files move document.pdf --copy

# File is copied to PARA
# Original stays in Downloads
```

## Cleanup After Moving

```bash
# Move files and clean up empty directories
uv run para-files move *.pdf --cleanup-empty
```

## Examples

### Move Downloads

```bash
# Preview first
uv run para-files move ~/Downloads/*.pdf --dry-run

# Then move
uv run para-files move ~/Downloads/*.pdf
```

### Move with Conflict Handling

```bash
uv run para-files move *.pdf --conflict rename --cleanup-empty
```

### Suppress Warnings

```bash
# Don't warn about files going to Inbox
uv run para-files move *.pdf --skip-unclassifiable
```

## Troubleshooting

**Files went to Inbox (0_Inbox)?**
Classification confidence too low. See [Troubleshooting](../troubleshooting/files-going-to-inbox.md).

**"Permission denied"?**
Check write permissions on PARA folder.

**"File already exists"?**
Use `--conflict` option to handle duplicates.

## Next Steps

- **[Manage Issuers](manage-issuers.md)** - Improve matching
- **[Learn from Files](learn-from-files.md)** - Fix misclassifications
- **[move Command](../cli/move.md)** - Full reference
