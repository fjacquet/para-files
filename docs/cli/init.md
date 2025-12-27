---
title: init Command
layout: default
parent: CLI Reference
nav_order: 13
---

# init Command

Pre-create PARA folder structure from your reference tree.

## Basic Usage

```bash
# Create PARA folders at default location
uv run para-files init

# Create at specific location
uv run para-files init /path/to/para
```

## Options

### `--subfolders`

Include route-specific subfolders:

```bash
uv run para-files init --subfolders

# Creates not just PARA top-level folders
# But also route-specific subfolders defined in your reference tree
```

### `--dry-run`

Preview what would be created without creating:

```bash
uv run para-files init --dry-run

# See folder structure that would be created
```

## What Gets Created

Default (without `--subfolders`):

```
PARA/
  0_Inbox/
  1_Projects/
  2_Areas/
  3_Resources/
  4_Archives/
```

With `--subfolders`:

```
PARA/
  0_Inbox/
  1_Projects/
  2_Areas/
  3_Resources/
    livres/
    articles/
  4_Archives/
    factures/
    contracts/
```

## Examples

### Create Basic Structure

```bash
# At default PARA_ROOT
uv run para-files init

# Check what was created
ls -la ~/Documents/PARA/
```

### Preview First

```bash
uv run para-files init --dry-run

# See what would be created
# Then run without --dry-run to create
```

### Create with All Subfolders

```bash
uv run para-files init --subfolders

# Creates full folder tree from reference tree
```

### Create at Custom Location

```bash
uv run para-files init /custom/location/PARA

# Creates structure there instead
```

## Important Note

**The `move` command automatically creates folders as needed.**

You only need `init` if you want to:

- Pre-create folder structure before moving files
- See the folder layout before using the system
- Organize folders manually

## Related Commands

- **[move](move.md)** - Auto-creates folders as it moves
- **[Task: Set Up PARA](../tasks/set-up-para-folder.md)** - Full setup guide
