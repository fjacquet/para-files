# Architecture

**Analysis Date:** 2026-02-28

## Pattern Overview

**Overall:** 5-Signal Classification Pipeline with Cascade Matching

**Key Characteristics:**

- Deterministic multi-stage classifier pipeline: first match wins
- Content-agnostic classification: abstracts away file type complexities
- Configuration-driven routing rules: YAML-based PARA taxonomy definition
- Lazy initialization of ML models: embeddings and LLM load on first use
- Platform-specific macOS constraints: Apple Neural Engine for MLX, Vision Framework for OCR

## Layers

**CLI Layer:**

- Purpose: Command dispatcher and user interface
- Location: `src/para_files/cli/`
- Contains: Command modules (classify, scan, move, learn, etc.), shared utilities, app setup
- Depends on: Pipeline, Config, File operations
- Used by: End users via typer CLI

**Pipeline Layer:**

- Purpose: Orchestrates the 5-signal classification cascade
- Location: `src/para_files/pipeline.py`
- Contains: ClassificationPipeline coordinator, signal initialization, lazy loading
- Depends on: All classifiers, ReferenceTree, Config, taxonomy loaders
- Used by: All CLI commands for file classification

**Classification Signals (Strategy Pattern):**

- Purpose: Implement individual classification strategies
- Location: `src/para_files/classifiers/`
- Contains: BaseClassifier abstract interface + 5 concrete implementations
- Depends on: File metadata, taxonomy data, embedding models
- Used by: Pipeline in priority order

**Taxonomy Layer:**

- Purpose: Loads and manages classification taxonomies
- Location: `src/para_files/taxonomies/`
- Contains: Taxonomy loaders (documents.json, thema.json), model definitions
- Depends on: Pydantic for validation
- Used by: Classifiers for domain knowledge

**Configuration Layer:**

- Purpose: Manages application settings and secrets
- Location: `src/para_files/config.py`
- Contains: Pydantic settings models with env var override support
- Depends on: YAML reference tree, environment variables
- Used by: Pipeline, CLI, logging setup

**Utilities Layer:**

- Purpose: Cross-cutting concerns and file handling
- Location: `src/para_files/utils/`
- Contains: File operations, metadata extraction, validation, OCR, ISBN lookup, etc.
- Depends on: External tools (exiftool, pandoc), external APIs (ISBN lookup)
- Used by: Classifiers, pipeline, mover

**Reference Tree Layer:**

- Purpose: Loads PARA folder structure and routing rules
- Location: `src/para_files/reference_tree.py`
- Contains: YAML parsing, routing rule extraction, issuer database
- Depends on: YAML format, types
- Used by: Pipeline for rules engine initialization

## Data Flow

**Classification Request Flow:**

1. **CLI Command Entry** (`classify_cmd.py`, `scan_cmd.py`)
   - User provides file or directory path
   - Config loaded from YAML/env (`.env` or `config/personal_file_tree.yaml`)
   - Logging configured for console + optional file output

2. **File Discovery**
   - CLI expands paths to list of files (glob patterns or single files)
   - Filters by extension if specified
   - Validates file existence

3. **Pipeline Initialization** (`pipeline.py::_ensure_initialized()`)
   - Lazy initialization on first use (not at startup)
   - Loads ReferenceTree from YAML
   - Initializes all 5 classifiers in priority order:
     1. BookDetector (96-100% confidence)
     2. RulesEngineClassifier (95% confidence)
     3. TaxonomyClassifier (90% confidence)
     4. SemanticClassifier (85% confidence, MLX embeddings)
     5. MLXLLMClassifier (60% confidence, optional)

4. **Per-File Classification** (`pipeline.py::classify_file()`)
   - Extract file metadata: size, dates, EXIF, PDF metadata
   - Read content preview (configurable chars)
   - Optional OCR renaming for generic filenames
   - Call `classify(content, metadata)` through cascade

5. **Cascade Matching** (`pipeline.py::classify()`)
   - For each classifier in order:
     - Call `classifier.classify(content, metadata)`
     - If returns ClassificationResult (not None), return immediately
     - Otherwise continue to next classifier
   - Default to `0_Inbox` if no classifier matches

6. **Result Processing**
   - Extract target path from category
   - Format for JSON or human-readable output
   - Return to CLI

**File Movement Flow:**

1. **Move Command** (`move_cmd.py`)
   - Scan source directory for files
   - Classify each file using pipeline
   - Create FileMover with conflict strategy
   - Move files to target directories

2. **Conflict Resolution** (`mover.py::FileMover`)
   - SKIP: keep file in source if target exists
   - OVERWRITE: replace target file
   - RENAME: add numeric suffix (file_1.txt, file_2.txt)
   - RENAME_WITH_DATE: prepend date (2025-01-15_file.txt)

**Learning Flow** (`learn_cmd.py`, `learner.py`):

- User provides file and destination
- Stores mapping: issuer/domain → category
- Extracts patterns from filename/content
- Updates validated database for future matching

**State Management:**

- **Stateless Pipeline:** No state held between classifications
- **Configuration State:** Loaded once at CLI startup, passed to pipeline
- **ML Model State:** Models loaded on first use, cached in memory (or HuggingFace cache)
- **Reference Tree State:** Parsed once during pipeline initialization, held in memory

## Key Abstractions

**BaseClassifier Interface:**

- Purpose: Define contract for all classification signals
- Location: `src/para_files/classifiers/base.py`
- Pattern: Strategy pattern with uniform interface
- Properties: `name`, `source`, `default_confidence`
- Methods: `classify(content, metadata) → ClassificationResult | None`

**ClassificationResult Type:**

- Purpose: Encapsulates classification output
- Location: `src/para_files/types.py`
- Fields: category, confidence (value + source), route_name, extracted_params, raw_score
- Used everywhere: returned by classifiers, processed by CLI commands

**FileMetadata Type:**

- Purpose: Standardized metadata extraction across file types
- Location: `src/para_files/types.py`
- Fields: path, filename, extension, size, dates (created/modified/EXIF), EXIF GPS/camera, PDF metadata
- Pattern: Data class for passing between components

**Config Models (Pydantic):**

- Purpose: Configuration with type validation and env var override
- Location: `src/para_files/config.py`
- Classes: Config (root), MLXConfig, LLMConfig, LoggingConfig, OCRRenameConfig
- Pattern: Nested settings with priority: overrides > env vars > .env > YAML > defaults

**RoutingRule Type:**

- Purpose: Special routing for photos, videos, courses with date extraction
- Location: `src/para_files/types.py`
- Fields: extensions, patterns, destination, date_source, issuers, platforms
- Pattern: Declarative rule matching with placeholder expansion

## Entry Points

**`main()` / `cli()`:**

- Location: `src/para_files/main.py`
- Triggers: Package entry point (via pyproject.toml)
- Responsibilities: Imports all commands, calls `app()` (Typer)

**CLI Commands (Typer app):**

- Location: `src/para_files/cli/`
- Triggers: User invokes `para-files <command>`
- Modules: app.py (Typer instance), individual command modules
- Commands: classify, scan, move, learn, bookstore, tree, routes, config, dedupe, clean, init, migrate, rescan

**`ClassificationPipeline.classify_file()`:**

- Location: `src/para_files/pipeline.py`
- Triggers: Called by CLI commands (classify, scan, move, bookstore)
- Responsibilities: Extract metadata, read content, orchestrate cascade

**Test Entry Points:**

- Location: `tests/` (conftest.py for fixtures, individual test_*.py modules)
- Fixtures: project_root, fixtures_dir, mocked components
- Pattern: pytest with standard discovery (test_*.py files)

## Error Handling

**Strategy:** Graceful degradation with explicit error paths

**Patterns:**

1. **Configuration Errors** (`load_config_or_exit()` in `cli/shared.py`)
   - ValidationError caught and logged
   - Exit code 1 immediately
   - Console error message shown to user

2. **File Validation** (`utils/validation.py`)
   - `validate_file_exists()`, `validate_directory_exists()`
   - Return boolean, let caller decide action
   - CLI uses for filtering/skipping invalid paths

3. **Classifier Failures** (`pipeline.py::classify()`)
   - Try/except around each classifier
   - Log exception, continue to next classifier
   - Never crash the pipeline

4. **Content Extraction Errors** (`utils/file_utils.py`)
   - Graceful fallback: if OCR fails, use text extraction
   - If content extraction fails, return empty string
   - Classification continues with empty content (may trigger defaults)

5. **External Tool Failures** (`utils/exiftool.py`, `utils/pandoc.py`, `utils/ocr.py`)
   - Command execution wrapped in try/except
   - Return empty result on failure
   - Logged as warnings (not errors)

## Cross-Cutting Concerns

**Logging:**

- Framework: `loguru` (from `para_files/logging.py`)
- Pattern: Import `logger` from loguru, not standard logging
- Output: Console (colored, human-readable) + File (JSON format with rotation)
- Configuration: Via `LoggingConfig` in settings

**Validation:**

- Framework: `pydantic` for data models, custom functions for paths
- Pattern: Type-annotated models with Field() constraints
- Location: `src/para_files/utils/validation.py` for file/directory checks

**Authentication:**

- Strategy: External APIs (ISBN lookup, geocoding) use direct HTTP calls
- Secrets: Stored in `.env` file (not in YAML)
- Pattern: Config loads from env vars with `PARA_FILES_*` prefix

## Classifier Signal Details

**Signal 1: BookDetector** (`src/para_files/classifiers/book_detector.py`)

- Confidence: 96% (100% if ISBN found)
- Detection: PDF file with book metadata or MOBI/EPUB format
- Classification: Thema codes (international book classification)
- Lookup: ISBN lookup to get Thema classification

**Signal 2: RulesEngineClassifier** (`src/para_files/classifiers/rules_engine.py`)

- Confidence: 95%
- Matching: Glob patterns on filename, extension, directory
- Routing: Special rules for photos (EXIF date), videos, courses, screenshots
- Placeholder Resolution: {year}, {month}, {day} from EXIF/content/filename

**Signal 3: TaxonomyClassifier** (`src/para_files/classifiers/taxonomy_classifier.py`)

- Confidence: 90%
- Data Source: documents.json (administrative docs) + learned patterns
- Matching: Issuer patterns + keywords from domain knowledge

**Signal 4: SemanticClassifier** (`src/para_files/classifiers/semantic_classifier.py`)

- Confidence: 85%
- Engine: MLX embedding similarity (nomic-text-v1.5 by default)
- Input: Content preview (2000 chars by default)
- Matching: Cosine similarity against category descriptions

**Signal 5: MLXLLMClassifier** (`src/para_files/classifiers/mlx_llm_classifier.py`)

- Confidence: 60% (configurable)
- Model: Qwen2.5-1.5B (or configurable)
- Engine: Native MLX-LM (macOS Apple Neural Engine)
- Optional: Disabled by default, enable via config

---

*Architecture analysis: 2026-02-28*
