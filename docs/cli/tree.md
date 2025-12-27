---
title: tree Command
layout: default
parent: CLI Reference
nav_order: 6
---

# tree Command

Display and validate your reference tree structure.

## Basic Usage

```bash
# Show tree structure
uv run para-files tree

# Validate for errors
uv run para-files tree --validate
```

## Options

### `--validate`

Check reference tree for errors:

```bash
uv run para-files tree --validate

# Reports:
# - Missing routes
# - Invalid paths
# - Syntax errors
# - Warnings
```

### `--issuers`

List all known issuers (banks, companies):

```bash
uv run para-files tree --issuers

# Shows issuers organized by category
```

### `--rules`

Show all routing rules:

```bash
uv run para-files tree --rules

# Shows glob patterns and special rules
```

### `-v, --verbose`

Show detailed information:

```bash
uv run para-files tree --issuers -v
# Shows all issuers including less common ones
```

## Examples

### View Structure

```bash
uv run para-files tree
```

Output:

```
PARA Structure:
  0_Inbox
  1_Projects
  2_Areas
  3_Resources
  4_Archives
```

### Validate Configuration

```bash
uv run para-files tree --validate

# Check for issues before moving lots of files
```

### See All Issuers

```bash
uv run para-files tree --issuers

# Output:
# Issuers by category:
#
# banques:
#   - UBS Switzerland
#   - Credit Suisse
#   - BCGE
#
# telecom:
#   - Swisscom
#   - Sunrise
```

### Review All Rules

```bash
uv run para-files tree --rules

# Shows pattern-based rules for classification
```

## What tree Does

Shows your reference tree configuration:

- PARA folder structure
- All routes (categories)
- All issuers (companies/banks/etc)
- All routing rules
- Configuration

Useful for:

- Understanding your current setup
- Validating before big operations
- Finding issues
- Learning what you've configured

## Related Commands

- **[routes](routes.md)** - List just the routes/categories
- **[issuers](issuers.md)** - List just the issuers
- **[add-issuer](add-issuer.md)** - Register new issuer
- **[add-utterance](add-utterance.md)** - Improve matching
