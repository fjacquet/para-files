---
title: Using .env File
layout: default
parent: Configuration
nav_order: 2
---

# Using .env File

The easiest way to configure para-files is with a `.env` file.

## Create .env File

In your para-files project directory:

```bash
cat > .env << EOF
PARA_FILES_PARA_ROOT=~/Documents/PARA
PARA_FILES_MLX_SCORE_THRESHOLD=0.75
EOF
```

Then use para-files normally:

```bash
uv run para-files classify file.pdf

# Automatically reads .env file
```

## Common .env Entries

### Minimal Setup

```bash
PARA_FILES_PARA_ROOT=~/Documents/PARA
```

### Standard Setup

```bash
# Required
PARA_FILES_PARA_ROOT=~/Documents/PARA

# Optional: customize embedding sensitivity
PARA_FILES_MLX_SCORE_THRESHOLD=0.75

# Optional: reference tree location
PARA_FILES_REFERENCE_TREE_PATH=config/personal_file_tree.yaml
```

### Full Setup (With LLM)

```bash
# Core
PARA_FILES_PARA_ROOT=~/Documents/PARA
PARA_FILES_REFERENCE_TREE_PATH=config/personal_file_tree.yaml

# MLX Embedding Model
PARA_FILES_MLX_MODEL_NAME=mlx-community/nomic-embed-text-v1.5
PARA_FILES_MLX_SCORE_THRESHOLD=0.75

# LLM Fallback (Optional)
PARA_FILES_LLM_ENABLED=true
PARA_FILES_LLM_MODEL=ollama/qwen2.5:1.5b
PARA_FILES_LLM_API_BASE=http://localhost:11434
PARA_FILES_LLM_CONFIDENCE_THRESHOLD=0.6

# Parallel Processing
PARA_FILES_MAX_WORKERS=4  # default; 1=sequential

# Other
PARA_FILES_CONTENT_PREVIEW_CHARS=2000
```

## Expanding Paths

Use `~` for home directory:

```bash
# These work fine
PARA_FILES_PARA_ROOT=~/Documents/PARA
PARA_FILES_REFERENCE_TREE_PATH=~/config/tree.yaml
```

Or absolute paths:

```bash
# Also fine
PARA_FILES_PARA_ROOT=/Users/you/Documents/PARA
PARA_FILES_REFERENCE_TREE_PATH=/Users/you/Projects/para-files/config/tree.yaml
```

## Verify Settings Loaded

```bash
# Check that your settings are being used
uv run para-files config --show

# Should show your configured values
```

## .gitignore

If you have secrets or personal paths, ignore .env:

```bash
# In .gitignore
.env
.env.local
```

## Troubleshooting

**Settings not being used?**

```bash
# Make sure .env is in the right directory
pwd  # Current directory

# Check if settings are loaded
uv run para-files config --show

# Try absolute path in .env
PARA_FILES_PARA_ROOT=/Users/you/Documents/PARA
```

**Special characters in paths?**

```bash
# Quote paths with spaces or special characters
PARA_FILES_PARA_ROOT="/Users/My User/Documents/My PARA"
```

## Related

- **[Overview](overview.md)** - Configuration basics
- **[YAML Config](yaml-config.md)** - Alternative: config in YAML
