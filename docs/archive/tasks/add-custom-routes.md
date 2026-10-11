---
title: Add Custom Routes
layout: default
parent: Tasks
nav_order: 10
---

# Add Custom Routes/Categories

Create custom categories beyond the default PARA structure.

## What Is a Route?

A route is a category where files go.

Default routes: `factures-utilities`, `factures-cloud`, etc.

You can add your own custom routes.

## Add Route to YAML

Edit `personal_file_tree.yaml`:

```yaml
routes:
  - name: invoices-personal
    path: "4_Archives/factures/personal"
    utterances:
      - "personal invoice"
      - "household bill"

  - name: learning-python
    path: "3_Resources/courses/python"
    utterances:
      - "Python tutorial"
      - "Python learning"
```

## Create Route with Utterances

```yaml
routes:
  - name: contracts-legal
    path: "3_Resources/contracts"
    utterances:
      - "legal agreement"
      - "contract document"
      - "terms and conditions"
```

## Use New Route

```bash
# Classify with new route
uv run para-files classify document.pdf

# Should match your custom route if content fits

# Or use in learning
uv run para-files learn document.pdf
# > What should it be? contracts-legal
```

## View Routes

```bash
# See all routes including custom ones
uv run para-files routes

# See utterances
uv run para-files routes --utterances
```

## Examples

### Custom Business Routes

```yaml
routes:
  - name: expenses-travel
    path: "1_Projects/expenses/travel"
    utterances:
      - "flight booking"
      - "hotel reservation"
      - "travel expense"
```

### Custom Learning Routes

```yaml
routes:
  - name: articles-ml
    path: "3_Resources/articles/machine-learning"
    utterances:
      - "machine learning article"
      - "neural networks"
      - "deep learning research"
```

## Path Variables

Use variables in paths:

```yaml
routes:
  - name: invoices
    path: "4_Archives/invoices/{year}/{month}"
    # Creates: 4_Archives/invoices/2024/01/
```

### Date Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{YYYY}` | 4-digit year | 2025 |
| `{MM}` | 2-digit month | 01 |
| `{DD}` | 2-digit day | 15 |
| `{year}` | 4-digit year (alias) | 2025 |

### Location Variables (for photos with GPS)

| Variable | Description | Example |
|----------|-------------|---------|
| `{country}` | Country name from GPS | Switzerland |
| `{location}` | City or region from GPS | Geneva |

Example for photos:

```yaml
routing_rules:
  photos:
    extensions: [".jpg", ".jpeg", ".png", ".heic"]
    destination: "4_Archives/photos/{YYYY}/{country}/{location}/{MM}"
    date_source: "exif"
    # Creates: 4_Archives/photos/2025/Switzerland/Geneva/06/
```

If GPS data is unavailable, the placeholders are removed automatically.

## Related

- **[Reference Tree](../architecture/reference-tree.md)** - YAML structure
- **[routes Command](../cli/routes.md)** - List routes
- **[add-utterance](../cli/add-utterance.md)** - Add keywords to routes
