---
title: test-route Command
layout: default
parent: CLI Reference
nav_order: 11
---

# test-route Command

Test and debug a specific route's configuration.

## Basic Usage

```bash
# Show route details
uv run para-files test-route route-name

# Example
uv run para-files test-route factures-utilities
```

## Output

```
Route: factures-utilities
Path: 4_Archives/factures/{year}/_Utilities
Utterances:
  - electricity bill
  - water consumption
  - power usage invoice
```

## With Options

### `--file PATH`

Test a specific file against the route:

```bash
uv run para-files test-route factures-utilities --file invoice.pdf

# Shows:
# - Does it match?
# - Confidence score
# - Why it matches/doesn't match
```

### `-v, --verbose`

Show detailed matching information:

```bash
uv run para-files test-route factures-utilities -v

# Shows more details about how semantic matching works
```

## Examples

### Check Route Configuration

```bash
uv run para-files test-route factures-utilities

# See what utterances are defined for this route
```

### Test a File Against a Route

```bash
uv run para-files test-route factures-utilities --file questionable_invoice.pdf

# Does this file match this route?
# What's the confidence?
```

### Debug Low Confidence

```bash
# File going to wrong category?
uv run para-files test-route factures-utilities --file problematic_file.pdf -v

# See why it's not matching better
```

## When to Use

**Use test-route when:**

- A file isn't matching any route
- Multiple routes seem to match
- You want to debug routing issues
- You're designing new routes

## Related Commands

- **[routes](routes.md)** - List all routes
- **[add-utterance](add-utterance.md)** - Improve route matching
- **[classify](classify.md)** - Classify files normally
- **[Task: Test Routing](../tasks/test-routing-rules.md)** - Full guide
