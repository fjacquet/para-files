---
title: routes Command
layout: default
parent: CLI Reference
nav_order: 7
---

# routes Command

List all available routes (categories) in your reference tree.

## Basic Usage

```bash
# List all routes
uv run para-files routes

# Show utterances for each route
uv run para-files routes --utterances
```

## Options

### `--utterances`
Show semantic matching keywords for each route:

```bash
uv run para-files routes --utterances

# Output:
# factures-utilities:
#   - "electricity bill"
#   - "water consumption"
#   - "power usage invoice"
#
# factures-telecom:
#   - "mobile plan invoice"
#   - "internet billing"
```

## Examples

### List All Routes

```bash
uv run para-files routes

# Output:
# Available routes:
# - factures-utilities
# - factures-telecom
# - factures-cloud
# - factures-mobilite
# - invoices-business
# ... etc
```

### View Semantic Matching Keywords

```bash
uv run para-files routes --utterances

# See what keywords match each route
# Helps understand why files are classified a certain way
```

## Understanding Routes

A "route" is a category that files can be classified into.

Each route has:
- **Name**: How you reference it (e.g., `factures-utilities`)
- **Path**: Where files go in PARA (e.g., `4_Archives/factures/{year}/_Utilities`)
- **Utterances**: Keywords that match it semantically

## Using Routes

Routes are used by:
- `classify` - Shows which route matches
- `move` - Determines destination folder
- `learn` - Asks you which route is correct
- `add-utterance` - Adds keywords to a route

## Examples

### Check Available Routes Before Learning

```bash
# See what routes exist
uv run para-files routes

# Then use them when learning:
uv run para-files learn file.pdf
# > What should it be? (use route name from above)
```

### Understand Why Files Match

```bash
# See utterances for a route
uv run para-files routes --utterances

# Look for the route your files are matching
# This helps understand the semantic matching
```

## Related Commands

- **[tree](tree.md)** - See complete tree structure
- **[add-utterance](add-utterance.md)** - Add matching keywords
- **[test-route](test-route.md)** - Debug a specific route
- **[Task: Add Custom Routes](../tasks/add-custom-routes.md)** - Create new routes
