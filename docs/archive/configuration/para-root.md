---
title: PARA_ROOT Setting
layout: default
parent: Configuration
nav_order: 4
---

# PARA_ROOT Setting

Configure where your PARA folders are stored.

## What Is PARA_ROOT?

`PARA_ROOT` is the top-level directory containing your PARA folder structure:

```
PARA_ROOT/
  0_Inbox/
  1_Projects/
  2_Areas/
  3_Resources/
  4_Archives/
```

Files are organized into these top-level folders, which contain subfolders for routes.

## Set PARA_ROOT

### Via Environment Variable

```bash
export PARA_FILES_PARA_ROOT=~/Documents/PARA

uv run para-files classify file.pdf
```

### Via .env File

```bash
# In .env file
PARA_FILES_PARA_ROOT=~/Documents/PARA
```

### Via YAML Config

```yaml
# In personal_file_tree.yaml
config:
  para_root: "~/Documents/PARA"
```

## Examples

### Default Location

```bash
export PARA_FILES_PARA_ROOT=~/Documents/PARA
```

### Custom Location

```bash
export PARA_FILES_PARA_ROOT=/Volumes/ExternalDrive/PARA
```

### Different for Different Projects

```bash
# Project 1
PARA_FILES_PARA_ROOT=~/Projects/project1/PARA

# Project 2
PARA_FILES_PARA_ROOT=~/Projects/project2/PARA
```

## Create PARA Folder Structure

Once PARA_ROOT is set, create the folders:

```bash
# Auto-create on first move, or manually:
uv run para-files init

# Or init with subfolders
uv run para-files init --subfolders
```

## Verify Setting

```bash
# Check PARA_ROOT is set correctly
uv run para-files config --show

# Should show your PARA_ROOT
```

## Troubleshooting

**"PARA_ROOT not set" error?**

```bash
# Make sure it's exported
export PARA_FILES_PARA_ROOT=~/Documents/PARA

# Or add to .env file
echo 'PARA_FILES_PARA_ROOT=~/Documents/PARA' > .env
```

**Files going to wrong place?**

```bash
# Verify correct PARA_ROOT
uv run para-files config --show

# Check with dry-run before moving
uv run para-files move file.pdf --dry-run
```

**Path with spaces?**

```bash
# Quote the path
export PARA_FILES_PARA_ROOT="~/Documents/My PARA"

# Or in .env
PARA_FILES_PARA_ROOT="~/Documents/My PARA"
```

## Related

- **[Configuration Overview](overview.md)** - All configuration
- **[Getting Started](../getting-started/quick-setup.md)** - Initial setup
