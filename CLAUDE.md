# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**para-files** is a Mac-only intelligent classification system for personal files and work emails using MLX-powered semantic routing. It implements the PARA method (Projects, Areas, Resources, Archives) with a deterministic embedding-based classification pipeline.

## Build & Development Commands

```bash
# Install dependencies
uv sync

# Run the application
uv run python main.py

# Type checking
uv run mypy .

# Linting
uv run ruff check .

# Format code
uv run ruff format .
```

## Architecture

### Core Design

The system uses a 5-signal classification pipeline (in priority order):
1. **Validated DB** (100% confidence) - Manual sender/issuer → category mappings
2. **Rules Engine** (95%) - Glob patterns on filename/path/sender domain
3. **Domain/Issuer KB** (90%) - Known domain/issuer to category mappings
4. **Semantic Router MLX** (85%) - Embedding similarity to reference categories (deterministic)
5. **LLM Fallback** (configurable) - Optional AI for ambiguous cases

### Key Concept: Two Separate Reference Trees

The project maintains separate taxonomies:
- **Dell Mail Tree** - Professional email classification (from `outlook-mail-structure.md`)
- **Personal File Tree** - Personal files using PARA structure (`personal_file_tree.yaml`)

### MLX Stack (Mac Only)

- **Embeddings**: `nomic-embed-text-v1.5` (~100MB, 10-15ms latency)
- **Semantic Router**: `aurelio-labs/semantic-router` with custom MLX encoder
- **SLM Fallback**: Optional Qwen 2.5-1.5B-Instruct (MLX 4-bit)

## Key Configuration File

`personal_file_tree.yaml` defines:
- PARA folder structure with path patterns
- Semantic routing utterances per category
- Special routing rules (photos by EXIF date, courses by platform)
- Known issuers for automated matching

## Platform Constraint

This project is **macOS only** (Apple Silicon) because it uses:
- MLX for optimized embeddings
- Vision Framework for OCR (Apple Neural Engine)
