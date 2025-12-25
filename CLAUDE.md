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
- **Semantic Router**: `aurelio-labs/semantic-router` with custom MLX encoder
- **SLM Fallback**: Optional Qwen 2.5-1.5B-Instruct (MLX 4-bit, ~1GB)
- **OCR**: Vision Framework (Apple Neural Engine)

## Key Files

| File | Purpose |
|------|---------|
| `personal_file_tree.yaml` | PARA folder structure, semantic utterances, routing rules, known issuers |
| `src/para_files/` | Main package (src-layout) |

## Code Style

- Python 3.12+, strict mypy, comprehensive ruff ruleset
- Line length: 100 characters
- Use `from __future__ import annotations` in all modules
- Package is typed (`py.typed` marker present)

## Platform Constraint

This project is **macOS only** (Apple Silicon required) because it uses:
- MLX for optimized embeddings on Apple Neural Engine
- Vision Framework for OCR
