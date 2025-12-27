---
title: config Command
layout: default
parent: CLI Reference
nav_order: 12
---

# config Command

View current configuration settings.

## Basic Usage

```bash
# Show current configuration
uv run para-files config --show

# Show reference tree path
uv run para-files config --path
```

## Options

### `--show`

Display all current settings:

```bash
uv run para-files config --show

# Output:
# PARA_ROOT: /Users/you/Documents/PARA
# REFERENCE_TREE_PATH: config/personal_file_tree.yaml
# MLX_MODEL_NAME: mlx-community/nomic-embed-text-v1.5
# MLX_SCORE_THRESHOLD: 0.75
# LLM_ENABLED: false
# ... etc
```

### `--path`

Show where configuration is coming from:

```bash
uv run para-files config --path

# Output:
# Reference tree: /Users/you/Projects/para-files/config/personal_file_tree.yaml
# Environment: .env file / /Users/you/.zshrc
```

## Configuration Precedence

Settings are loaded in this order (highest priority first):

1. **Environment variables** (`PARA_FILES_*`)
2. **`.env` file** in current directory
3. **`config:` section** in YAML reference tree
4. **Default values** (built-in)

## Examples

### Check Current Settings

```bash
uv run para-files config --show

# Verify PARA_ROOT is set correctly before moving files
```

### Find Configuration Source

```bash
uv run para-files config --path

# Where is my config coming from?
```

## Common Settings

See [Configuration Guide](../configuration/overview.md) for:

- `PARA_FILES_PARA_ROOT` - Where to store PARA folders
- `PARA_FILES_MLX_MODEL_NAME` - Embedding model
- `PARA_FILES_MLX_SCORE_THRESHOLD` - Confidence threshold
- `PARA_FILES_LLM_ENABLED` - Enable AI fallback

## Troubleshooting

**"PARA_ROOT not set" error?**

```bash
uv run para-files config --show

# Check if PARA_FILES_PARA_ROOT is set
# If not, set it in .env or environment
```

**Wrong configuration being used?**

```bash
uv run para-files config --path

# See which file is being read
# Check precedence above
```

## Related Commands

- **[Configuration Guide](../configuration/overview.md)** - Full setup details
- **[Environment Variables](../configuration/env-file.md)** - How to set config
- **[YAML Config](../configuration/yaml-config.md)** - Configure in YAML
