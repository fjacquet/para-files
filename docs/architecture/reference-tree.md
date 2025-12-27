---
title: Reference Tree (YAML Structure)
layout: default
parent: Architecture
nav_order: 9
---

# Reference Tree YAML Structure

The `personal_file_tree.yaml` file defines your PARA classification system.

## Basic Structure

```yaml
config:
  para_root: "~/Documents/PARA"
  mlx:
    score_threshold: 0.75

routes:
  - name: factures-utilities
    path: "4_Archives/factures/{year}/_Utilities"
    utterances:
      - "electricity bill"
      - "water consumption"

issuers:
  banques:
    - "UBS Switzerland"
    - "Credit Suisse"
```

## Sections

### config Section

```yaml
config:
  para_root: "~/Documents/PARA"
  reference_tree_path: "config/personal_file_tree.yaml"
  content_preview_chars: 2000
  
  mlx:
    model_name: "mlx-community/nomic-embed-text-v1.5"
    score_threshold: 0.75
  
  llm:
    enabled: false
    model: "ollama/qwen2.5:1.5b"
    api_base: "http://localhost:11434"
```

### routes Section

Each route defines a category:

```yaml
routes:
  - name: factures-utilities           # Unique name
    path: "4_Archives/factures/_Utils" # Where files go
    utterances:                        # Keywords for matching
      - "electricity bill"
      - "power usage"
      - "energy invoice"
```

**Variables in path:**
- `{year}` - Current year
- `{month}` - Current month
- `{day}` - Current day

Example: `4_Archives/{year}/{month}/invoices`
Result: `4_Archives/2024/01/invoices`

### issuers Section

Register known companies/banks:

```yaml
issuers:
  banques:           # Category
    - "UBS"          # Company names
    - "Credit Suisse"
  
  telecom:
    - "Swisscom"
    - "Sunrise"
  
  utilities:
    - "EDF Energy"
    - "Water Company"
```

## Creating Custom Categories

Create new issuer categories:

```yaml
issuers:
  my_custom:  # New category
    - "My Company"
    - "Other Company"
```

Then use in add-issuer:

```bash
uv run para-files add-issuer "Company" -c my_custom
```

## Full Example

```yaml
config:
  para_root: "~/Documents/PARA"
  mlx:
    score_threshold: 0.75

routes:
  - name: factures-utilities
    path: "4_Archives/factures/{year}/_Utilities"
    utterances:
      - "electricity bill"
      - "water usage"
      - "gas invoice"

  - name: factures-telecom
    path: "4_Archives/factures/{year}/_Telecom"
    utterances:
      - "mobile invoice"
      - "internet billing"

  - name: learning-python
    path: "3_Resources/courses/python"
    utterances:
      - "Python tutorial"
      - "learn Python"

issuers:
  banques:
    - "UBS"
    - "Credit Suisse"
  
  telecom:
    - "Swisscom"
    - "Sunrise"
  
  utilities:
    - "EDF"
    - "Suez Water"
```

## Editing Tree

Edit directly in text editor or use CLI:

```bash
# Add issuer
uv run para-files add-issuer "Company" -c category

# Add utterance
uv run para-files add-utterance route "keyword phrase"

# View tree
uv run para-files tree --validate
```

## Validation

Check tree for errors:

```bash
uv run para-files tree --validate

# Reports issues before they cause problems
```

## Related

- **[Configuration](../configuration/overview.md)** - Config section details
- **[routes Command](../cli/routes.md)** - View routes
- **[issuers Command](../cli/issuers.md)** - View issuers
