---
title: Configuration Overview
layout: default
parent: Configuration
nav_order: 1
---

# Configuration Overview

Configuration controls where files go, which ML model to use, and advanced settings.

## How Configuration Works

Settings are loaded in priority order (first found wins):

1. **Environment variables** - `PARA_FILES_*` prefix
2. **`.env` file** - In current directory or project root
3. **YAML config** - `config:` section in reference tree
4. **Default values** - Built-in defaults

This means you can override settings at any level.

## Essential Settings

You **must** set:
- `PARA_FILES_PARA_ROOT` - Where your PARA folders are

```bash
export PARA_FILES_PARA_ROOT=~/Documents/PARA
```

## Optional Settings

Common options:
- `PARA_FILES_MLX_SCORE_THRESHOLD` - Sensitivity (0.0-1.0)
- `PARA_FILES_REFERENCE_TREE_PATH` - Custom tree location
- `PARA_FILES_LLM_ENABLED` - Use AI fallback

## Configuration Methods

### 1. Environment Variables (Highest Priority)

```bash
export PARA_FILES_PARA_ROOT=~/Documents/PARA
export PARA_FILES_MLX_SCORE_THRESHOLD=0.80

uv run para-files classify file.pdf
```

### 2. .env File (Recommended)

Create `.env` in your project root:

```bash
PARA_FILES_PARA_ROOT=~/Documents/PARA
PARA_FILES_MLX_SCORE_THRESHOLD=0.75
```

### 3. YAML Config (In Reference Tree)

Add to `personal_file_tree.yaml`:

```yaml
config:
  para_root: "~/Documents/PARA"
  mlx:
    score_threshold: 0.75
  llm:
    enabled: false
```

## Available Settings

### Core
- **`PARA_ROOT`** - Required. PARA folder location
- **`REFERENCE_TREE_PATH`** - Path to YAML tree (default: config/personal_file_tree.yaml)
- **`VALIDATED_DB_PATH`** - Path to validated mappings JSON

### MLX Model
- **`MLX_MODEL_NAME`** - Model to use (default: mlx-community/nomic-embed-text-v1.5)
- **`MLX_SCORE_THRESHOLD`** - Minimum confidence (0.0-1.0, default: 0.75)

### LLM Fallback (Optional)
- **`LLM_ENABLED`** - Enable AI fallback (default: false)
- **`LLM_MODEL`** - Which model (default: ollama/qwen2.5:1.5b)
- **`LLM_API_BASE`** - API endpoint (e.g., http://localhost:11434)
- **`LLM_CONFIDENCE_THRESHOLD`** - Min LLM confidence (default: 0.6)

### Other
- **`CONTENT_PREVIEW_CHARS`** - How much of file to read (default: 2000)

## Check Current Config

```bash
# See all current settings
uv run para-files config --show

# See which file is being used
uv run para-files config --path
```

## Common Scenarios

### Quick Start (Minimal Config)

```bash
# Just set PARA_ROOT
export PARA_FILES_PARA_ROOT=~/Documents/PARA

uv run para-files classify file.pdf
```

### Stricter Confidence

```bash
# Only accept high-confidence classifications
export PARA_FILES_MLX_SCORE_THRESHOLD=0.85
```

### Custom Reference Tree Location

```bash
# Use tree from different location
export PARA_FILES_REFERENCE_TREE_PATH=~/.config/my_tree.yaml
```

### Enable LLM Fallback

```bash
export PARA_FILES_LLM_ENABLED=true
export PARA_FILES_LLM_API_BASE=http://localhost:11434
```

## Next Steps

- **[Environment Variables](env-file.md)** - Set via .env
- **[YAML Config](yaml-config.md)** - Configure in YAML
- **[Specific Settings](para-root.md)** - Detailed setting guides
