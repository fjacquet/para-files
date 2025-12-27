---
title: clean Command
layout: default
parent: CLI Reference
nav_order: 14
---

# clean Command

Remove junk files, empty directories, and temporary files from a directory.

## Basic Usage

```bash
# Clean directory recursively (default)
uv run para-files clean ~/Downloads

# Non-recursive
uv run para-files clean ~/Downloads --no-recursive
```

## What Gets Cleaned

**Apple temp files:**
- `.DS_Store`
- `._*` (AppleDouble shadow files)
- `.Spotlight-V100`
- `.Trashes`
- `.fseventsd`

**Windows temp files:**
- `Thumbs.db`
- `desktop.ini`
- `$RECYCLE.BIN`

**Editor backup files:**
- `*~` (Vim/Emacs)
- `.swp` (Vim swap)
- `.swo` (Vim swap)

**Empty directories:** (removed bottom-up)

## Options

### `--dry-run`
Preview what would be deleted:

```bash
# Always do this first!
uv run para-files clean ~/Downloads --dry-run
```

### `--nfo`
Also delete `.nfo` files (video metadata):

```bash
uv run para-files clean ~/Downloads --nfo
```

### `--no-empty-dirs`
Skip empty directory cleanup:

```bash
# Only clean junk files, leave empty dirs
uv run para-files clean ~/Downloads --no-empty-dirs
```

### `--log PATH`
Save cleanup log to JSON file:

```bash
uv run para-files clean ~/Downloads --log cleanup.json

# View what was deleted
cat cleanup.json
```

### `--json`
Output as JSON:

```bash
uv run para-files clean ~/Downloads --json
```

### `-v, --verbose`
Show detailed output:

```bash
uv run para-files clean ~/Downloads -v
```

## Examples

### Preview Before Cleaning

```bash
# Always preview first!
uv run para-files clean ~/Downloads --dry-run

# Review what would be deleted
```

### Clean Downloads Folder

```bash
uv run para-files clean ~/Downloads

# Removes .DS_Store, Thumbs.db, and empty directories
```

### Clean Recursively with Log

```bash
uv run para-files clean ~/Documents --log cleanup.json

# See what was cleaned
cat cleanup.json
```

### Clean Without Touching Empty Directories

```bash
uv run para-files clean ~/Downloads --no-empty-dirs

# Removes junk files only
```

### Include .nfo Files

```bash
uv run para-files clean ~/Videos --nfo

# Removes .nfo sidecar files (video metadata)
```

## Safe Workflow

```bash
# 1. Always preview first
uv run para-files clean ~/Downloads --dry-run

# 2. Review output carefully

# 3. If satisfied, clean with a log
uv run para-files clean ~/Downloads --log cleanup.json

# 4. Check the log
cat cleanup.json
```

## Troubleshooting

**"Permission denied"?**
You may not have write permission in that directory.

**"Nothing was cleaned"?**
The directory is already clean or doesn't contain junk files.

**Want to restore deleted files?**
Check your trash/recycle bin. `clean` permanently deletes.

## Related Commands

- **[move](move.md)** - Move files after cleaning
- **[Task: Organize Directory](../tasks/set-up-para-folder.md)** - Full workflow
