---
title: Installation
layout: default
parent: Getting Started
nav_order: 1
---

# Installation

## System Requirements

- **macOS** with Apple Silicon (M1, M2, M3, M4, etc.)
- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** package manager (required)

> **Note**: para-files is macOS only because it uses MLX embeddings (Apple Neural Engine) and Vision Framework for OCR.

## Install via GitHub

```bash
# Clone repository
git clone https://github.com/fjacquet/para-files.git
cd para-files

# Install dependencies
uv sync --all-extras
```

## Verify Installation

Test that everything works:

```bash
# Should show version
uv run para-files --version

# Should show help
uv run para-files --help
```

## Next Steps

1. **[Quick Setup](quick-setup.md)** - Configure in 5 minutes
2. **[First Classification](first-file.md)** - Classify your first file
3. **[Full Configuration Guide](../configuration/overview.md)** - Advanced settings

## Troubleshooting

### "command not found: uv"
Install uv from https://docs.astral.sh/uv/getting-started/installation/

### "M1 chip required" error
This is expected if you're not on Apple Silicon. para-files only works on macOS with M1/M2/M3/M4.

### Python 3.12+ required
```bash
# Check your Python version
python3 --version

# If you need a newer version, use uv to manage it
uv python install 3.12
```

### Module not found errors
```bash
# Reinstall dependencies
uv sync --all-extras
```
