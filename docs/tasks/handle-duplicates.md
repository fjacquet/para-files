---
title: Handle Duplicate Files
layout: default
parent: Tasks
nav_order: 8
---

# Handle Duplicate Files When Moving

Deal with files that already exist at destination.

## Conflict Options

When a file already exists, you have choices:

```bash
--conflict skip           # Don't move
--conflict overwrite      # Replace existing (careful!)
--conflict rename         # Rename: file.pdf → file_1.pdf
--conflict rename_with_date # Rename: 2024-01-15_file.pdf
```

## Skip Duplicates

```bash
uv run para-files move *.pdf --conflict skip

# Files that already exist stay where they are
# Other files are moved normally
```

**When to use:** You want to keep existing versions

## Rename to Keep Both

```bash
uv run para-files move *.pdf --conflict rename

# file.pdf → file_1.pdf
# file_1.pdf → file_2.pdf
# etc.
```

**When to use:** You want both versions

## Rename with Date

```bash
uv run para-files move *.pdf --conflict rename_with_date

# file.pdf → 2024-01-15_file.pdf
# Easier to see which is newer
```

**When to use:** You want chronological versions

## Overwrite (Careful!)

```bash
uv run para-files move *.pdf --conflict overwrite

# Replaces existing files (data loss!)
```

**When to use:** Almost never—very dangerous

## Workflow

```bash
# Step 1: Preview what would happen
uv run para-files move *.pdf --dry-run

# Step 2: Choose conflict strategy
# Step 3: Move with strategy
uv run para-files move *.pdf --conflict rename_with_date

# Step 4: Verify
ls -la ~/Documents/PARA/
```

## Examples

### Multiple Versions

```bash
# Keep all versions
uv run para-files move *.pdf --conflict rename_with_date

# Result: 2024-01-15_report.pdf, 2024-01-20_report.pdf, ...
```

### Clean Overwrite

```bash
# Keep only latest (if you're sure)
uv run para-files move *.pdf --conflict skip

# Move new files that don't exist yet
```

## Related

- **[move Command](../cli/move.md)** - Full reference
- **[Move Files Guide](move-files.md)** - Complete workflow
