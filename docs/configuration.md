---
title: Configuration
layout: default
nav_order: 5
has_children: true
---

# Configuration

para-files can be configured via environment variables (`.env` file) and YAML configuration.

## Configuration Methods

| Method | File | Best For |
|--------|------|----------|
| Environment variables | `.env` | Paths, model settings, API keys |
| YAML config | `personal_file_tree.yaml` | Routes, categories, issuers |

## Quick Setup

```bash
# Initialize configuration
para-files init

# View current configuration
para-files config
```

## Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `PARA_ROOT` | `~/Documents` | Root folder for PARA structure |
| `MLX_MODEL_NAME` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `CONFIDENCE_THRESHOLD` | `0.7` | Minimum confidence for classification |

## Configuration Files

- **[Overview](configuration/overview.md)** - How configuration works
- **[Environment Variables](configuration/env-file.md)** - `.env` file reference
- **[YAML Config](configuration/yaml-config.md)** - Route and category configuration
- **[PARA Root](configuration/para-root.md)** - Setting up your PARA folder
- **[MLX Model](configuration/mlx-model.md)** - Embedding model configuration
- **[LLM Fallback](configuration/llm-fallback.md)** - AI fallback settings
- **[Paths](configuration/paths.md)** - Path configuration options
