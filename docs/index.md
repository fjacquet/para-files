---
title: Documentation
layout: home
nav_order: 1
---

# para-files Documentation

Welcome to para-files! This documentation is organized by how you want to use it.

## I want to

### Get Started

- **[Installation](getting-started/installation.md)** - Install para-files and verify it works
- **[Quick Setup](getting-started/quick-setup.md)** - Configure in 5 minutes
- **[Classify My First File](getting-started/first-file.md)** - Run your first classification

### Use para-files

- **[CLI Overview](cli/overview.md)** - What commands are available
- **[Task Guides](tasks/)** - How-to guides for common tasks:
  - [Set up PARA folder](tasks/set-up-para-folder.md)
  - [Classify files](tasks/classify-single-file.md)
  - [Move files to categories](tasks/move-files.md)
  - [Manage issuers & routes](tasks/manage-issuers.md)
  - [Learn from your files](tasks/learn-from-files.md)

### Configure para-files

- **[Configuration Overview](configuration/overview.md)** - How configuration works
- **[Environment Variables](configuration/env-file.md)** - Set via .env file
- **[YAML Config](configuration/yaml-config.md)** - Configure in personal_file_tree.yaml

### Understand How It Works

- **[Architecture Overview](architecture/overview.md)** - The big picture
- **[6-Signal Pipeline](architecture/overview.md#the-6-signals)** - How files are classified
- **[Reference Tree](architecture/reference-tree.md)** - YAML structure explained
- **[MLX Embeddings](architecture/signal-4-semantic.md)** - Semantic matching details

### Troubleshoot Issues

- **[Files going to Inbox](troubleshooting/files-going-to-inbox.md)** - Wrong classifications
- **[Low confidence scores](troubleshooting/confidence-too-low.md)** - Adjusting thresholds
- **[Model download issues](troubleshooting/model-download-slow.md)** - Caching & performance

### Develop & Extend

- **[Developer Guide](CLAUDE.md)** - Building & contributing (in CLAUDE.md)
- **[Python API](advanced/programmatic-usage.md)** - Use para-files in your code
- **[Product Requirements (PRD)](prd.md)** - Goals, features, and success metrics
- **[Product Vision & Opportunities](vision.md)** - Future features and strategic direction
- **[Architecture Decision Records (ADR)](adr/README.md)** - Key design decisions and rationale

## Quick Commands Reference

```bash
# Classify
uv run para-files classify document.pdf

# Move to PARA folders
uv run para-files move *.pdf --dry-run

# Add a bank
uv run para-files add-issuer "My Bank" -c banques

# Interactive learning
uv run para-files learn document.pdf
```

[Full CLI Reference →](cli/overview.md)

## Key Features

- **6-Signal Pipeline**: Validated DB → Rules → Book Detection → Domain KB → Semantic Router → LLM
- **MLX Embeddings**: Fast local semantic matching on Apple Neural Engine
- **PARA Method**: Organize into Projects, Areas, Resources, Archives
- **Extensible**: Add custom routes, issuers, and utterances via YAML
- **Photo/Video Geotagging**: GPS-aware organization by location
- **Book Detection**: Technical book identification via ISBN/metadata

## System Requirements

- **macOS** with Apple Silicon (M1/M2/M3/M4)
- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** package manager
