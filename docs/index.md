---
title: Home
layout: home
nav_order: 1
---

# para-files

**macOS-only (Apple Silicon)** intelligent file classification system using MLX-powered semantic routing.

Implements the **PARA method** (Projects, Areas, Resources, Archives) with a deterministic 5-signal classification pipeline.

## Features

- **MLX Embeddings**: Fast, local semantic matching using `nomic-embed-text-v1.5`
- **5-Signal Pipeline**: Cascading classification with configurable confidence thresholds
- **PARA Method**: Organize files into Projects, Areas, Resources, and Archives
- **CLI Interface**: Simple commands for classify, move, scan, and learning
- **Extensible**: Add custom routes, issuers, and utterances via YAML

## Quick Start

```bash
# Install
git clone https://github.com/fjacquet/para-files.git
cd para-files
uv sync --all-extras

# Configure
export PARA_FILES_PARA_ROOT="/path/to/your/para/folder"

# Classify files
uv run para-files classify document.pdf
uv run para-files move *.pdf --dry-run
```

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Documentation

- [Architecture](architecture.html) - Understand the 5-signal classification pipeline
- [CLI Reference](cli.html) - Full command reference
- [Configuration](configuration.html) - Configure PARA roots, models, and thresholds
- [API Reference](api.html) - Python API documentation

## License

[MIT License](https://github.com/fjacquet/para-files/blob/main/LICENSE)
