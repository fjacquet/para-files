# Technology Stack

**Analysis Date:** 2026-02-28

## Languages

**Primary:**

- Python 3.12+ - Core application language with strict type checking (mypy)
- YAML - Configuration files (reference tree, project config)
- JSON - Data serialization (taxonomy data, ISBN metadata, user feedback)

## Runtime

**Environment:**

- Python 3.12 (minimum requirement, tested with 3.13)
- macOS with Apple Silicon (M1/M2/M3/M4) - required for MLX framework

**Package Manager:**

- uv (astral-sh) - Fast Python package manager and resolver
- Lockfile: Not used (uv uses deterministic dependency resolution)

## Frameworks

**Core Application:**

- Typer 0.21.0 - CLI framework (Click-based, better for complex CLIs)
- Pydantic 2.12.0+ - Data validation and configuration management
- Pydantic-settings 2.6.0+ - Environment-based configuration

**Machine Learning / Embeddings:**

- MLX 0.30.1+ - Inference framework optimized for Apple Neural Engine
- mlx-lm 0.20.0+ - Language models for MLX runtime
- mlx-embedding-models 0.0.11+ - Pre-trained embedding models for semantic routing
- semantic-router 0.1.0+ - Semantic route matching library (integrates with MLX encoder)

**Testing:**

- pytest 8.3.0+ - Test runner
- pytest-cov 6.0.0+ - Coverage reporting

**Build/Dev:**

- Ruff 0.8.0+ - Fast Python linter and formatter
- mypy 1.15.0+ - Static type checker (strict mode enabled)
- pre-commit 4.0.0+ - Git hook framework
- types-PyYAML 6.0+ - Type stubs for YAML

**Quality & Security:**

- bandit 1.9.2+ - Security linting
- gitleaks 8.21.2+ - Secret detection (pre-commit hook)
- commitizen 4.1.0+ - Commit message validation

## Key Dependencies

**Critical:**

- PyYAML 6.0+ - YAML parsing for reference tree configuration
- loguru 0.7.3+ - Structured logging with rotation/retention
- isbnlib 3.10.14+ - ISBN lookup and validation from Google Books/Open Library
- pymupdf (fitz) 1.26.7+ - PDF text extraction and metadata analysis
- pypdf 4.0.0+ (optional) - Additional PDF manipulation capabilities

**Content Processing:**

- cryptography 46.0.3+ - Encryption utilities
- einops 0.8.1+ - Tensor operations for embedding processing
- httpx 0.28.1+ - Async HTTP client for ISBN lookups

**Platform Integration:**

- pyobjc-framework-vision 12.1+ - macOS Vision Framework for OCR (Apple Silicon)
- pyobjc-framework-cocoa 12.1+ - macOS Cocoa Framework bindings
- pyobjc-framework-quartz 12.1+ - macOS Quartz/CoreGraphics bindings

**Geocoding & Reference:**

- geopy 2.4.1+ - Reverse geocoding for GPS coordinate lookup
- faker 39.0.0+ - Synthetic data generation for testing

**LLM Fallback (Optional):**

- litellm 1.50.0+ - Unified LLM API (supports OpenAI, Anthropic, Ollama, local providers)

## Configuration

**Environment Variables:**

- PARA_FILES_PARA_ROOT - Root directory for PARA folders (default: ~/Documents/PARA)
- PARA_FILES_REFERENCE_TREE_PATH - Path to YAML configuration (default: config/personal_file_tree.yaml)
- PARA_FILES_VALIDATED_DB_PATH - Optional JSON file with sender→category mappings
- PARA_FILES_MLX_MODEL_NAME - MLX embedding model (default: mlx-community/nomic-embed-text-v1.5)
- PARA_FILES_MLX_SCORE_THRESHOLD - Similarity threshold (0.0-1.0, default: 0.75)
- PARA_FILES_LLM_ENABLED - Enable optional LLM fallback (default: false)
- PARA_FILES_LLM_MODEL - LLM model identifier for litellm (default: ollama/qwen2.5:1.5b)
- PARA_FILES_LLM_CONFIDENCE_THRESHOLD - Minimum LLM confidence (0.0-1.0, default: 0.6)
- PARA_FILES_LLM_API_BASE - API base URL for local LLM providers (e.g., <http://localhost:11434> for Ollama)
- PARA_FILES_CONTENT_PREVIEW_CHARS - Content preview length for semantic matching (default: 2000)
- PARA_FILES_LOG_LEVEL - Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
- PARA_FILES_LOG_ROTATION - Log rotation size (default: 10 MB)
- PARA_FILES_LOG_RETENTION - Log retention period (default: 30 days)

**Configuration Files:**

- `pyproject.toml` - Project metadata, dependencies, tool configurations (Ruff, mypy, pytest)
- `.env` / `.env.example` - Local environment variable overrides
- `config/personal_file_tree.yaml` - User's PARA reference tree, semantic routes, known issuers
- `config/documents.json` - Swiss administrative document taxonomy (69KB)
- `config/thema.json` - International book classification (Thema v1.6, 9,187 codes, 3.6MB)
- `.pre-commit-config.yaml` - Git hook configurations (Ruff, mypy, gitleaks, commitizen)
- `.python-version` - Python version specification (3.12)

## Build System

**Build Backend:**

- hatchling - Standard Python build backend
- Wheel packaging: `src/para_files/` structure

**Entry Points:**

- para-files = "para_files.main:cli" - CLI executable

## Platform Requirements

**Development:**

- macOS (Apple Silicon M1+)
- Python 3.12+
- uv package manager
- ~500MB disk for MLX models (cached in ~/.cache/huggingface)

**Production:**

- Same as development (macOS/Apple Silicon only)
- No external server dependencies (all ML inference local)
- Requires ~500MB for MLX embedding model cache

**Optional External Services:**

- Ollama (if using LLM fallback with local inference)
- GitHub Actions - CI/CD (defined in `.github/workflows/`)

---

*Stack analysis: 2026-02-28*
