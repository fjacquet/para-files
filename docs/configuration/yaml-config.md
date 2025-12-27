---
title: YAML Configuration
layout: default
parent: Configuration
nav_order: 3
---

# YAML Configuration

Configure para-files in your `personal_file_tree.yaml` using a `config:` section.

## Basic Example

Add to the top of your YAML file:

```yaml
config:
  para_root: "~/Documents/PARA"
  mlx:
    model_name: "mlx-community/nomic-embed-text-v1.5"
    score_threshold: 0.75

routes:
  - name: factures-utilities
    # ... rest of your routes
```

## Full YAML Config Example

```yaml
config:
  para_root: "~/Documents/PARA"
  content_preview_chars: 2000
  reference_tree_path: "config/personal_file_tree.yaml"

  mlx:
    model_name: "mlx-community/nomic-embed-text-v1.5"
    score_threshold: 0.75

  llm:
    enabled: false
    # model: "ollama/qwen2.5:1.5b"
    # api_base: "http://localhost:11434"
    # confidence_threshold: 0.6

routes:
  - name: factures-utilities
    path: "4_Archives/factures/{year}/_Utilities"
    utterances:
      - "electricity bill"
      - "water usage"

  # ... more routes
```

## Configuration Sections

### Core Settings

```yaml
config:
  para_root: "~/Documents/PARA"
  reference_tree_path: "config/personal_file_tree.yaml"
  content_preview_chars: 2000
```

### MLX Embedding Model

```yaml
config:
  mlx:
    model_name: "mlx-community/nomic-embed-text-v1.5"
    score_threshold: 0.75
```

Adjust `score_threshold`:
- Lower (0.65) = more matches, more false positives
- Higher (0.85) = fewer matches, more misses
- Default (0.75) = balanced

### LLM Fallback (Optional)

```yaml
config:
  llm:
    enabled: false
    # Uncomment to enable:
    # model: "ollama/qwen2.5:1.5b"
    # api_base: "http://localhost:11434"
    # confidence_threshold: 0.6
```

## Configuration Priority

Settings are loaded in order (first found wins):

1. **Environment variables** (`PARA_FILES_*`) - Highest priority
2. **`.env` file** in current directory
3. **`config:` section** in YAML file
4. **Default values** - Lowest priority

Example: If you have both `.env` and YAML config, `.env` wins.

## Path Syntax

Use `~` for home directory:

```yaml
config:
  para_root: "~/Documents/PARA"
  reference_tree_path: "~/config/tree.yaml"
```

Or absolute paths:

```yaml
config:
  para_root: "/Users/you/Documents/PARA"
```

## Verify Configuration

```bash
# Check what's actually being used
uv run para-files config --show

# See which file is providing config
uv run para-files config --path
```

## When to Use YAML Config

**Good for:**
- Keeping all PARA settings in one file
- Sharing config via version control
- Complex setups with multiple settings

**Alternative:**
Use `.env` file if you prefer separate config file.

## YAML Syntax Rules

- Use quotes for paths: `para_root: "~/Documents/PARA"`
- Use proper indentation (2 spaces)
- No trailing colons in values
- Lists with `-` for arrays

## Related

- **[Overview](overview.md)** - Configuration basics
- **[Environment Variables](env-file.md)** - Using .env file
- **[Specific Settings](para-root.md)** - Individual setting details
