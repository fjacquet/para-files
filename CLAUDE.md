# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**para-files** is a macOS-only (Apple Silicon) intelligent file classification system using MLX-powered semantic routing. It implements the PARA method (Projects, Areas, Resources, Archives) with a deterministic embedding-based classification pipeline.

## Build & Development Commands

```bash
# Install dependencies (includes dev tools)
uv sync --all-extras

# Run the application
uv run para-files

# Run all quality checks
uv run ruff check src/ tests/      # Lint
uv run ruff format src/ tests/     # Format
uv run mypy src/                   # Type check

# Testing
uv run pytest                      # Run all tests
uv run pytest -v                   # Verbose output
uv run pytest tests/test_main.py   # Single test file
uv run pytest -k "test_version"    # Run tests matching pattern
uv run pytest --cov                # With coverage report

# Pre-commit hooks (after install)
pre-commit install                 # Install hooks
pre-commit run --all-files         # Run manually
```

## Architecture

### 5-Signal Classification Pipeline

The system classifies files using signals in priority order:

1. **Validated DB** (100% confidence) - Manual sender/issuer → category mappings
2. **Rules Engine** (95%) - Glob patterns on filename/path/sender domain
3. **Domain/Issuer KB** (90%) - Known domain/issuer to category mappings
4. **Semantic Router MLX** (85%) - Embedding similarity to reference categories (deterministic)
5. **LLM Fallback** (configurable) - Optional AI for ambiguous cases

### Two Separate Reference Trees

The project maintains distinct taxonomies that should never be mixed:
- **Dell Mail Tree** - Professional email classification (from `outlook-mail-structure.md`)
- **Personal File Tree** - Personal files using PARA structure (`personal_file_tree.yaml`)

### MLX Stack

- **Embeddings**: `nomic-embed-text-v1.5` via `mlx-community` (~100MB, 10-15ms latency)
- **Semantic Router**: Custom implementation with cosine similarity
- **SLM Fallback**: Optional Qwen 2.5-1.5B-Instruct via litellm/Ollama
- **OCR**: Vision Framework (Apple Neural Engine)

### Model Loading

The MLX embedding model uses **lazy loading** - it downloads automatically from Hugging Face on first use:

```python
from para_files.encoders import MLXEncoder

# Model not loaded yet (fast instantiation)
encoder = MLXEncoder(model_name="mlx-community/nomic-embed-text-v1.5")

# Model loads on first call (~100MB download, cached in ~/.cache/huggingface)
embeddings = encoder(["text to embed"])
```

The `ClassificationPipeline` handles this automatically - no manual model management needed.

## Configuration

Configuration uses pydantic-settings with environment variables (prefix: `PARA_FILES_`) or `.env` file:

```bash
# Required
PARA_FILES_PARA_ROOT=/path/to/para/folder

# MLX settings
PARA_FILES_MLX_MODEL_NAME=mlx-community/nomic-embed-text-v1.5
PARA_FILES_MLX_SCORE_THRESHOLD=0.75

# Optional LLM fallback
PARA_FILES_LLM_ENABLED=false
PARA_FILES_LLM_MODEL=ollama/qwen2.5:1.5b
```

See `.env.example` for all options.

## Key Files

| File                                     | Purpose                                                            |
|------------------------------------------|--------------------------------------------------------------------|
| `personal_file_tree.yaml`                | PARA folder structure, semantic utterances, routing rules, issuers |
| `.env.example`                           | Configuration template with all available options                  |
| `src/para_files/config.py`               | Configuration management with pydantic-settings                    |
| `src/para_files/pipeline.py`             | 5-signal classification orchestrator                               |
| `src/para_files/encoders/mlx_encoder.py` | MLX embedding encoder with lazy loading                            |
| `src/para_files/reference_tree.py`       | YAML reference tree loader                                         |
| `src/para_files/classifiers/`            | Classification signal implementations                              |

## Code Style

- Python 3.12+, strict mypy, comprehensive ruff ruleset
- Line length: 100 characters
- Use `from __future__ import annotations` in all modules
- Package is typed (`py.typed` marker present)

## Platform Constraint

This project is **macOS only** (Apple Silicon required) because it uses:
- MLX for optimized embeddings on Apple Neural Engine
- Vision Framework for OCR
