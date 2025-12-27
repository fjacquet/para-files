---
title: CLI Overview
layout: default
parent: CLI Reference
nav_order: 1
---

# CLI Overview

para-files commands organize around what you want to do.

## Command Groups

### Classification & Movement
- **[classify](classify.md)** - Determine category for files
- **[move](move.md)** - Classify and move to PARA folders
- **[scan](scan.md)** - Preview classifications for a directory
- **[learn](learn.md)** - Interactive learning from files

### Configuration & System
- **[config](config.md)** - Show current configuration
- **[init](init.md)** - Pre-create PARA folder structure
- **[clean](clean.md)** - Remove junk files

### Reference Tree Management
- **[tree](tree.md)** - Display/validate reference tree
- **[routes](routes.md)** - List available categories
- **[issuers](issuers.md)** - List known companies/banks
- **[add-issuer](add-issuer.md)** - Register a company/bank
- **[add-utterance](add-utterance.md)** - Improve semantic matching
- **[test-route](test-route.md)** - Debug routing

## Common Patterns

### File Input
Most commands accept multiple files:
```bash
uv run para-files classify file1.pdf file2.docx file3.txt
uv run para-files move *.pdf
```

### Output Formats
Get results as text or JSON:
```bash
uv run para-files classify file.pdf          # Human readable
uv run para-files classify file.pdf --json   # Machine readable
```

### Verbosity
Add `-v` for detailed output:
```bash
uv run para-files classify file.pdf -v
```

### Reference Tree
All commands can use a custom reference tree:
```bash
uv run para-files classify file.pdf -r custom_tree.yaml
```

## Essential Commands

**First time?**
```bash
# Set up folder structure
uv run para-files init ~/Documents/PARA
```

**Classify files:**
```bash
# Single file
uv run para-files classify document.pdf

# Multiple files
uv run para-files classify *.pdf

# Preview results
uv run para-files classify *.pdf --json
```

**Move files:**
```bash
# Preview first
uv run para-files move *.pdf --dry-run

# Actually move
uv run para-files move *.pdf
```

**Manage your categories:**
```bash
# See all categories
uv run para-files routes

# Add a bank
uv run para-files add-issuer "My Bank" -c banques

# Add matching keywords
uv run para-files add-utterance factures-utilities "electricity bill"
```

**Learn interactively:**
```bash
# Improve matching for a file
uv run para-files learn misclassified_file.pdf
```

## Global Options

All commands support:
- `-r, --reference-tree PATH` - Use custom YAML reference tree
- `-v` - Verbose output
- `--json` - JSON output format

## Help

```bash
# Show all commands
uv run para-files --help

# Help for specific command
uv run para-files classify --help
uv run para-files move --help
```

## Next Steps

- Pick a command above and read its page for full details
- Or jump to [Task Guides](../tasks/) for how-to walkthroughs
