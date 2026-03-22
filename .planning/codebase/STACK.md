# Technology Stack

**Analysis Date:** 2026-03-22

## Languages

**Primary:**
- Python 3.12+ - Core application language, strictly typed
- Python 3.13 - Supported via future annotations
- YAML - Configuration and taxonomy definitions

**Secondary:**
- JSON - Taxonomies and reference data (Thema, documents.json)
- Shell (bash/zsh) - Build and deployment automation via Makefile

## Runtime

**Environment:**
- Python 3.12 (defined in `.python-version`)
- macOS (primary platform due to Vision Framework for OCR)
- Cross-platform capable (excluding OCR features)

**Package Manager:**
- uv (Rust-based, 10-100x faster than pip)
- Lockfile: `uv.lock` (mandatory, ensures reproducible builds)

## Frameworks

**Core:**
- Typer 0.21.0+ - Type-hint-driven CLI framework (built on Click)
- Pydantic 2.12.0+ - Data validation and configuration management
- Pydantic-Settings 2.6.0+ - Environment-based configuration

**LLM & Embeddings:**
- litellm 1.50.0+ - Unified LLM/embedding API (calls Ollama, OpenAI, Anthropic)
- semantic-router 0.1.0+ - Intent routing with embedding similarity

**File Processing:**
- PyMuPDF (fitz) 1.26.7+ - PDF metadata extraction and fallback OCR
- pypdf 4.0.0+ - PDF processing (optional, `pdf` extra)
- isbnlib 3.10.14+ - ISBN validation and book metadata lookup
- openpyxl 3.1.5+ - Excel file handling
- odfpy 1.4.1+ - ODF (OpenDocument) file handling
- xlrd 2.0.2+ - Legacy Excel support
- py7zr 0.22.0+ - 7-zip archive extraction (optional, `archives` extra)

**macOS-Specific (OCR & Vision):**
- pyobjc-framework-vision 12.1+ - Apple Vision Framework
- pyobjc-framework-quartz 12.1+ - Quartz graphics framework
- pyobjc-framework-cocoa 12.1+ - Cocoa/macOS API bindings

**Utilities:**
- loguru 0.7.3+ - Structured logging with rotation and retention
- pyyaml 6.0+ - YAML parsing and dumping
- httpx 0.28.1+ - Async HTTP client for API calls
- geopy 2.4.1+ - Geolocation and reverse geocoding
- einops 0.8.1+ - Tensor operations for embedding comparisons
- cryptography 46.0.3+ - Encryption utilities for sensitive data
- faker 39.0.0+ - Test data generation
- bandit 1.9.2+ - Security vulnerability scanning

## Testing Framework

**Test Runner:**
- pytest 8.3.0+ - Test discovery and execution
- pytest-cov 6.0.0+ - Coverage reporting

**Type Checking:**
- mypy 1.15.0+ - Strict static type checker
- types-PyYAML 6.0.0+ - Type stubs for PyYAML

**Code Quality:**
- Ruff 0.8.0+ - Fast linting and formatting (combines isort, black, flake8, etc.)
  - Target: Python 3.12
  - Line length: 100 characters
  - Import grouping: first-party (para_files), third-party, stdlib
  - Formatting: double quotes, 2-space indentation

**Pre-commit:**
- pre-commit 4.0.0+ - Git hooks automation (defined in `.pre-commit-config.yaml`)

## Key Dependencies

**Critical - Core Pipeline:**
- litellm (1.50.0+) - Unified interface to Ollama embeddings and LLM fallback
- semantic-router (0.1.0+) - Intent classification with cosine similarity
- pydantic (2.12.0+) - Type-safe configuration and data models
- typer (0.21.0+) - CLI command building and argument parsing
- loguru (0.7.3+) - Structured, rotating JSON logs with audit trail

**Critical - File Classification:**
- PyMuPDF (1.26.7+) - PDF parsing, text extraction, metadata fallback
- isbnlib (3.10.14+) - Book ISBN validation and metadata lookup
- openpyxl, xlrd, odfpy - Office document content extraction

**Infrastructure:**
- pyyaml (6.0+) - Reference tree and configuration parsing
- pydantic-settings (2.6.0+) - Environment variable configuration overlay
- httpx (0.28.1+) - HTTP requests for Ollama/litellm communication
- geopy (2.4.1+) - Reverse geocoding with local SQLite cache

**Development:**
- mypy (1.15.0+) - Strict type checking enforced in CI
- ruff (0.8.0+) - Single tool for lint, format, import sorting
- pytest (8.3.0+) - Test framework with markers for slow/integration tests

## Configuration

**Environment:**
- Env prefix: `PARA_FILES_*` (pydantic-settings auto-maps)
- Config file: `.env` or `.env.local` (auto-loaded by pydantic-settings)
- YAML config: `config/personal_file_tree.yaml` (reference tree with optional config section)

**Key Environment Variables:**
```
# PARA filesystem
PARA_FILES_PARA_ROOT = /path/to/PARA      # Root for 0_Inbox, 1_Projects, etc.

# Embeddings (Ollama via litellm)
PARA_FILES_MLX_MODEL_NAME = nomic-text-v1.5
PARA_FILES_MLX_SCORE_THRESHOLD = 0.75
PARA_FILES_MLX_SEMANTIC_ENABLED = true

# LLM Fallback (Ollama via litellm)
PARA_FILES_LLM_ENABLED = true
PARA_FILES_LLM_MODEL = ollama/ministral-3:8b
PARA_FILES_LLM_API_BASE = http://localhost:11434
PARA_FILES_LLM_CONFIDENCE_THRESHOLD = 0.6

# Logging
PARA_FILES_LOG_LEVEL = INFO
PARA_FILES_LOG_ROTATION = 10 MB
PARA_FILES_LOG_RETENTION = 30 days

# Reference & taxonomies
PARA_FILES_REFERENCE_TREE_PATH = config/personal_file_tree.yaml
```

**Build Configuration:**
- `pyproject.toml` - Project metadata, dependencies, build backend (hatchling)
- `Makefile` - Convenience targets for lint, format, typecheck, test, build
- `.pre-commit-config.yaml` - Git hooks (ruff, mypy, bandit)
- `pyproject.toml` [tool.pytest] - Markers for slow/integration tests, 79% coverage minimum

**Type Checking:**
- `pyproject.toml` [tool.mypy] - Strict mode enabled
- `src/para_files/py.typed` - PEP 561 marker for type distribution

## Platform Requirements

**Development:**
- Python 3.12+ with pip/uv
- uv package manager (required by Makefile)
- macOS 12+ with Apple Silicon (for OCR features only)
- Running Ollama server (http://localhost:11434) for embeddings and LLM

**Production:**
- Python 3.12+ runtime
- Ollama server (local or remote, configurable via PARA_FILES_LLM_API_BASE)
- Filesystem access to PARA root directory
- Optional: macOS for OCR; other platforms work without OCR

**Optional External Services:**
- Open Library / Google Books / Wikipedia (via isbnlib) - for book metadata fallback
- geopy geocoding providers (OpenStreetMap/Nominatim) - for GPS reverse geocoding

## Build & Distribution

**Package Format:**
- Wheel distribution via hatchling
- Packages built into `dist/`
- Entry point: `para-files` console script (calls `para_files.main:cli`)

**Build Process:**
```bash
make build              # Runs: quality + test + uv build
```

**Quality Pipeline:**
```bash
make all               # Full: setup → lint → format → typecheck → test
make quality          # Lint + typecheck (no tests)
make lint            # Ruff check
make format          # Ruff format
make typecheck       # Mypy strict checking
make test            # Pytest with markers
make test-cov        # Pytest with coverage (min 79%)
```

---

*Stack analysis: 2026-03-22*
