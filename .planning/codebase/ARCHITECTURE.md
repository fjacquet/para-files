# Architecture

**Analysis Date:** 2026-03-22

## Pattern Overview

**Overall:** Cascading classifier pipeline with deterministic fallback routing

**Key Characteristics:**
- **First-match-wins classification** - Pipeline stops after first successful classification
- **6-signal cascade** - Each signal has explicit confidence scores and sources
- **Lazy initialization** - Pipeline initialized on first classification (thread-safe)
- **Modular classifiers** - Each signal implements `BaseClassifier` interface
- **Configuration-driven** - Pydantic-based settings from env, YAML, and .env files
- **PARA method foundation** - File organization into 5 buckets (Inbox, Projects, Areas, Resources, Archives)

## Layers

**Configuration Layer:**
- Purpose: Load and validate all runtime settings
- Location: `src/para_files/config.py`
- Contains: `Config`, `MLXConfig`, `LLMConfig`, `LoggingConfig`, `ExtensionRoutingConfig`
- Depends on: Pydantic, YAML files, environment variables
- Used by: Pipeline, CLI commands

**Type Definitions Layer:**
- Purpose: Define domain models and enums
- Location: `src/para_files/types.py`
- Contains: `ClassificationResult`, `FileMetadata`, `SignalResult`, `RoutingRule`, `Route`, classification enums
- Depends on: Pydantic for validation
- Used by: Pipeline, classifiers, CLI commands

**Reference Tree Layer:**
- Purpose: Parse and expose PARA structure and routing configuration
- Location: `src/para_files/reference_tree.py`
- Contains: `ReferenceTree` loader for personal_file_tree.yaml
- Depends on: YAML files, types layer
- Used by: Pipeline, rules engine, learning module

**Classification Pipeline Layer:**
- Purpose: Orchestrate 6-signal cascade
- Location: `src/para_files/pipeline.py`
- Contains: `ClassificationPipeline` with lazy init, signal coordination, default 0_Inbox fallback
- Depends on: All classifier implementations, configuration, reference tree, encoders
- Used by: CLI commands (scan, classify, move)

**Classifier Implementations Layer:**
- Purpose: Implement each classification signal
- Location: `src/para_files/classifiers/`
- Contains: 6 classifiers - `BookDetector`, `RulesEngineClassifier`, `TaxonomyClassifier`, `SemanticClassifier`, `ExtensionRouterClassifier`, `LLMClassifier`
- Depends on: `BaseClassifier` interface, utilities, taxonomy loader, encoders
- Used by: Pipeline in priority order

**Encoding Layer:**
- Purpose: Compute semantic embeddings via Ollama/litellm
- Location: `src/para_files/encoders/ollama_encoder.py`
- Contains: `OllamaEncoder` using litellm API
- Depends on: litellm library, Ollama server
- Used by: `SemanticClassifier`

**Taxonomy Layer:**
- Purpose: Load and expose document/book classification taxonomies
- Location: `src/para_files/taxonomies/loader.py`, `src/para_files/taxonomies/models.py`
- Contains: `TaxonomyLoader`, `DocumentCategory`, `DocumentType`, `ThemaTaxonomy` (for Thema book codes)
- Depends on: JSON configuration files (thema.json, documents.json)
- Used by: `TaxonomyClassifier`, `BookDetector`, `SemanticClassifier`

**File Movement Layer:**
- Purpose: Move/copy classified files with conflict resolution
- Location: `src/para_files/mover.py`
- Contains: `ConflictStrategy` enum, file hashing, deduplication logic
- Depends on: Pathlib, file I/O
- Used by: `move_cmd`, `scan_cmd`

**Learning Layer:**
- Purpose: Extend routing rules based on user feedback
- Location: `src/para_files/learner.py`, `src/para_files/learning/`
- Contains: `RoutingLearner` for YAML modifications, feedback tracking, pattern extraction
- Depends on: Reference tree, YAML serialization
- Used by: `learn_cmd`

**Utilities Layer:**
- Purpose: Extract metadata, perform transformations, validate inputs
- Location: `src/para_files/utils/`
- Contains: File utilities, OCR, PDF/book metadata extraction, filename sanitization, EXIF parsing, geolocation
- Depends on: Various external libraries (PyMuPDF, pypdf, exiftool, Ollama)
- Used by: Pipeline, classifiers, CLI commands

**CLI Layer:**
- Purpose: Expose classification and file management as commands
- Location: `src/para_files/cli/`
- Contains: Typer commands (scan, move, classify, learn, routes, bookstore, etc.) and shared utilities
- Depends on: Pipeline, mover, configuration, logging
- Used by: Entry point `main.py`

## Data Flow

**Classification Flow (classify_file):**

1. **Input** - File path from CLI or file system
2. **Metadata Extraction** (`extract_file_metadata`) - Size, timestamps, EXIF, PDF properties
3. **Pre-classification Rename** (optional) - OCR rename if filename is generic and content-based metadata available
4. **Content Preview** (`read_content_preview`) - Extract first N characters for semantic matching
5. **Pipeline Execution** - Run 6-signal cascade:
   - Signal 1: `BookDetector` - ISBN/Thema detection (returns if matched)
   - Signal 2: `RulesEngineClassifier` - Glob patterns + issuer matching (returns if matched)
   - Signal 3: `TaxonomyClassifier` - Issuer + keyword lookup (returns if matched)
   - Signal 4: `SemanticClassifier` - Embedding similarity (returns if matched)
   - Signal 5: `ExtensionRouterClassifier` - File extension routing (returns if matched)
   - Signal 6: `LLMClassifier` - LLM fallback if configured (returns if matched)
   - **Fallback** - Default to `0_Inbox` if no signal matches
6. **Result** - `ClassificationResult` with category, confidence, signals, extracted params
7. **Path Computation** - `get_target_path()` joins PARA root + category
8. **File Movement** - Move/copy to destination with conflict handling

**Learning Flow (learn_cmd):**

1. **User provides** - File path and correct category
2. **Feedback tracking** - Log classification result vs. user correction
3. **Pattern extraction** - Analyze why classification was wrong
4. **Route extension** - Add issuer/utterance to routing_rules in reference tree YAML
5. **Validation** - Reload pipeline to test extended rules

**Configuration Flow (load_config):**

1. **Priority cascade** - Env vars > .env file > YAML config section > defaults
2. **Nested configs** - MLXConfig, LLMConfig, LoggingConfig, ExtensionRoutingConfig
3. **Path expansion** - Tilde (~) expanded for home directories
4. **Validation** - Pydantic validates all fields
5. **Lazy initialization** - Pipeline classifiers init on first classify() call

**State Management:**
- **No global state** - Configuration passed to components
- **Thread-safe pipeline init** - Double-checked locking in `_ensure_initialized()`
- **Immutable results** - Classification results frozen after creation
- **Side-effect isolation** - File moves logged but rollback not supported (by design)

## Key Abstractions

**BaseClassifier Interface:**
- Purpose: Unified signature for all 6 signals
- Location: `src/para_files/classifiers/base.py`
- Pattern: Abstract methods for `name`, `source`, `default_confidence`, `classify()`
- Examples: All 6 classifiers in `src/para_files/classifiers/`

**ClassificationResult:**
- Purpose: Immutable classification outcome with metadata
- Location: `src/para_files/types.py`
- Pattern: Pydantic model with category, confidence, signals, extracted params
- Used by: All layers above pipeline

**RoutingRule:**
- Purpose: Pattern-based routing configuration
- Location: `src/para_files/types.py`
- Pattern: Contains extensions, glob patterns, destination template, date source options
- Examples: Loaded from reference_tree YAML by `ReferenceTree.load()`

**TaxonomyLoader:**
- Purpose: Lazy-load and cache taxonomies
- Location: `src/para_files/taxonomies/loader.py`
- Pattern: Singleton pattern via `get_taxonomy_loader()`
- Used by: Pipeline, `SemanticClassifier`, `TaxonomyClassifier`, `BookDetector`

**FileMetadata:**
- Purpose: Extracted file attributes for classification
- Location: `src/para_files/types.py`
- Pattern: Pydantic model with paths, timestamps, EXIF, PDF metadata
- Sources: `extract_file_metadata()` in file_utils.py

## Entry Points

**CLI Entry Point:**
- Location: `src/para_files/main.py` / `src/para_files/cli/app.py`
- Triggers: `para-files [command]` from command line
- Responsibilities: Parse command-line args, route to Typer command, setup logging
- Structure: Typer app with 10+ commands (scan, move, classify, learn, routes, etc.)

**Scan Command:**
- Location: `src/para_files/cli/scan_cmd.py`
- Triggers: `para-files scan [directory]`
- Responsibilities: Recursively classify files, optionally move to PARA destinations
- Flow: Walk directory → classify each file → optionally move with conflict strategy

**Move Command:**
- Location: `src/para_files/cli/move_cmd.py`
- Triggers: `para-files move [file] [category]`
- Responsibilities: Move single file to PARA category with conflict handling
- Flow: Validate category → compute path → move/copy file

**Classify Command:**
- Location: `src/para_files/cli/classify_cmd.py`
- Triggers: `para-files classify [file|directory]`
- Responsibilities: Classify files and show signals/confidence (no move)
- Flow: Read file → extract metadata → run pipeline → display results

**Learn Command:**
- Location: `src/para_files/cli/learn_cmd.py`
- Triggers: `para-files learn [file] [category]`
- Responsibilities: Add user correction to routing rules
- Flow: Analyze misclassification → extract patterns → update YAML

**Bookstore Command:**
- Location: `src/para_files/cli/bookstore_cmd.py`
- Triggers: `para-files bookstore [directory]`
- Responsibilities: Scan for PDFs, detect/classify books by ISBN/Thema
- Flow: Find PDFs → extract metadata → classify to book hierarchy

## Error Handling

**Strategy:** Log and continue (non-fatal errors), raise on configuration/validation failures

**Patterns:**
- **Classifier exceptions** - Caught in pipeline, logged, signal marked as failed
- **File I/O errors** - Logged with context (file path, operation)
- **Content extraction failures** - Fall back to empty string (treated as unmatched)
- **Configuration errors** - Pydantic raises `ValidationError` (fatal)
- **API failures** (Ollama, ISBN lookup) - Logged, classifier returns None (try next signal)

## Cross-Cutting Concerns

**Logging:**
- Framework: loguru
- Pattern: Import `from loguru import logger` in each module
- Levels: DEBUG (fine-grained flow), INFO (decisions), WARNING (recoverable issues), ERROR (failures)
- Configuration: `LoggingConfig` with rotation/retention

**Validation:**
- Pydantic models validate all domain types
- Custom validators in `utils/validation.py` for paths, directories
- CLI options validated before pipeline execution

**Authentication:**
- ISBN lookup: Uses external API (optional, graceful fallback if unavailable)
- Ollama embedding server: Requires running service (configured via `LLMConfig.api_base`)
- No user authentication (file system permission checks only)

**Threading:**
- Pipeline initialization: Double-checked locking for thread safety
- File scanning: Optional parallel processing via `max_workers` config
- No shared mutable state across threads
