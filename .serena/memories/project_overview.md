# para-files Project Overview

## Purpose

**para-files** is a macOS-only (Apple Silicon) intelligent file classification system using MLX-powered semantic routing. It implements the PARA method (Projects, Areas, Resources, Archives) with a deterministic embedding-based classification pipeline.

## Tech Stack

- **Python**: 3.12+ (strictly typed with mypy)
- **Build System**: Hatch with uv for package management
- **ML Stack**: MLX for Apple Silicon optimized embeddings
  - Embeddings: `nomic-embed-text-v1.5` via `mlx-community` (~100MB, 10-15ms latency)
  - SLM Fallback: Optional Qwen 2.5-1.5B-Instruct via litellm/Ollama
- **OCR**: Vision Framework (Apple Neural Engine via PyObjC)
- **CLI**: Typer
- **Config**: pydantic-settings with YAML support
- **Testing**: pytest with coverage
- **Quality**: ruff (linting + formatting), mypy (type checking), pre-commit hooks

## Platform Constraint

**macOS only** (Apple Silicon required) because it uses:

- MLX for optimized embeddings on Apple Neural Engine
- Vision Framework for OCR

## 5-Signal Classification Pipeline

The system classifies files using signals in priority order:

1. **Validated DB** (100% confidence) - Manual sender/issuer → category mappings
2. **Rules Engine** (95%) - Glob patterns on filename/path/sender domain
3. **Domain/Issuer KB** (90%) - Known domain/issuer to category mappings
4. **Semantic Router MLX** (85%) - Embedding similarity to reference categories
5. **LLM Fallback** (configurable) - Optional AI for ambiguous cases

## Codebase Structure

```
src/para_files/
├── __init__.py           # Package exports
├── main.py               # CLI entry point (Typer)
├── config.py             # Configuration with pydantic-settings
├── pipeline.py           # 5-signal classification orchestrator
├── reference_tree.py     # YAML reference tree loader
├── mover.py              # File moving logic
├── learner.py            # Interactive learning
├── types.py              # Shared type definitions
├── encoders/
│   ├── base.py           # Encoder base class
│   └── mlx_encoder.py    # MLX embedding encoder (lazy loading)
├── classifiers/
│   ├── base.py           # Classifier base class
│   ├── validated_db.py   # Signal 1: Manual mappings
│   ├── rules_engine.py   # Signal 2: Glob patterns
│   ├── domain_kb.py      # Signal 3: Domain/issuer KB
│   ├── semantic_router.py # Signal 4: MLX embeddings
│   ├── llm_fallback.py   # Signal 5: LLM fallback
│   └── book_detector.py  # Book/ISBN detection
└── utils/
    ├── ocr.py            # Vision Framework OCR
    ├── exiftool.py       # EXIF metadata extraction
    ├── pdf_metadata.py   # PDF metadata extraction
    ├── isbn_lookup.py    # ISBN lookup utilities
    ├── geolocation.py    # Geolocation utilities
    ├── pandoc.py         # Document conversion
    └── file_utils.py     # File utilities
```

## Key Configuration Files

- `config/personal_file_tree.yaml` - PARA structure, routes, issuers, AND app config
- `.env` / `.env.example` - Environment variable configuration
- `pyproject.toml` - Project configuration, dependencies, tool settings

## Two Separate Reference Trees

The project maintains distinct taxonomies that should never be mixed:

- **Dell Mail Tree** - Professional email classification
- **Personal File Tree** - Personal files using PARA structure
