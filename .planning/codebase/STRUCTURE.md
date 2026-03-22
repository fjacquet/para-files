# Codebase Structure

**Analysis Date:** 2026-03-22

## Directory Layout

```
para-files/
├── .planning/codebase/        # Codebase analysis documents
├── config/                     # Configuration files (YAML, JSON)
│   ├── personal_file_tree.yaml # PARA structure + routing rules
│   ├── thema.json             # Thema v1.6 book classification codes
│   └── documents.json         # Document type taxonomy
├── docs/                       # User-facing documentation
│   ├── adr/                   # Architecture Decision Records
│   ├── architecture/          # Technical architecture guides
│   ├── cli/                   # Command reference
│   ├── configuration/         # Configuration guides
│   ├── getting-started/       # Installation & quick start
│   ├── tasks/                 # How-to guides
│   └── troubleshooting/       # Common issues
├── scripts/                    # Utility scripts (brew, CI/CD)
├── src/para_files/            # Main application code
│   ├── __init__.py
│   ├── main.py               # CLI entry point (re-exports)
│   ├── config.py             # Configuration loading & validation
│   ├── types.py              # Domain type definitions (Pydantic models)
│   ├── pipeline.py           # Classification pipeline orchestrator
│   ├── mover.py              # File movement with conflict resolution
│   ├── learner.py            # Feedback-based routing extensions
│   ├── reference_tree.py     # YAML reference tree parser
│   ├── logging.py            # Logging configuration
│   ├── cli/                  # CLI command implementations (Typer)
│   │   ├── __init__.py
│   │   ├── app.py            # Typer app instance
│   │   ├── shared.py         # Shared utilities for commands
│   │   ├── scan_cmd.py       # Scan directory & classify
│   │   ├── move_cmd.py       # Move single file
│   │   ├── classify_cmd.py   # Classify without moving
│   │   ├── learn_cmd.py      # Learn from corrections
│   │   ├── routes_cmd.py     # Show/manage routes
│   │   ├── bookstore_cmd.py  # Detect & classify books
│   │   ├── clean_cmd.py      # Cleanup operations
│   │   ├── dedupe_cmd.py     # Deduplication
│   │   ├── inbox_cmd.py      # Manage inbox
│   │   ├── init_cmd.py       # Initialize reference tree
│   │   ├── config_cmd.py     # Show configuration
│   │   ├── tree_cmd.py       # Show PARA tree
│   │   ├── migrate_cmd.py    # Migrate from old format
│   │   ├── rescan_cmd.py     # Rescan existing files
│   │   └── (other commands)
│   ├── classifiers/          # 6-signal classification cascade
│   │   ├── __init__.py
│   │   ├── base.py           # BaseClassifier abstract interface
│   │   ├── book_detector.py  # Signal 1: ISBN/Thema detection
│   │   ├── rules_engine.py   # Signal 2: Pattern matching
│   │   ├── taxonomy_classifier.py # Signal 3: Taxonomy lookup
│   │   ├── semantic_classifier.py # Signal 4: Embedding similarity
│   │   ├── extension_router.py   # Signal 5: Extension-based routing
│   │   └── llm_classifier.py     # Signal 6: LLM fallback
│   ├── encoders/             # Semantic embedding implementations
│   │   ├── __init__.py
│   │   ├── base.py           # BaseEncoder interface
│   │   └── ollama_encoder.py # Ollama embedding via litellm
│   ├── taxonomies/           # Document & book taxonomies
│   │   ├── __init__.py
│   │   ├── loader.py         # Singleton loader for taxonomies
│   │   └── models.py         # DocumentCategory, DocumentType, ThemaTaxonomy
│   ├── learning/             # Feedback-based pattern learning
│   │   ├── __init__.py
│   │   ├── feedback_tracker.py # Track classification mismatches
│   │   └── pattern_extractor.py # Extract patterns from content
│   └── utils/                # Utility functions & helpers
│       ├── __init__.py
│       ├── file_utils.py     # File I/O, metadata extraction
│       ├── ocr.py            # OCR processing (macOS only)
│       ├── ocr_metadata.py   # Extract metadata from OCR text
│       ├── pdf_metadata.py   # PDF metadata extraction
│       ├── isbn_lookup.py    # ISBN resolution
│       ├── thema_lookup.py   # Thema code lookup
│       ├── filename_sanitizer.py # Filesystem-safe names
│       ├── filename_detector.py  # Detect generic names
│       ├── smart_renamer.py  # Suggest renames
│       ├── placeholder_resolver.py # Template variable substitution
│       ├── validation.py     # Input validation helpers
│       ├── technology_extractor.py # Extract tech keywords
│       ├── geolocation.py    # Reverse geocoding (EXIF GPS)
│       ├── exiftool.py       # EXIF metadata via exiftool
│       ├── pandoc.py         # Document conversion
│       ├── epub_metadata.py  # EPUB metadata
│       ├── mobi_metadata.py  # MOBI metadata
│       ├── chm_metadata.py   # CHM metadata
│       ├── nfo_parser.py     # NFO file parsing
│       └── cleanup.py        # File cleanup operations
├── tests/                     # Test suite (pytest)
│   ├── conftest.py           # Pytest fixtures & configuration
│   ├── fixtures/             # Test data & mock files
│   ├── test_pipeline.py      # Pipeline tests
│   ├── test_classifiers.py   # Individual classifier tests
│   ├── test_config.py        # Configuration tests
│   ├── test_mover.py         # File movement tests
│   ├── test_learner.py       # Learning module tests
│   ├── test_*_cmd.py         # CLI command tests
│   └── (other test modules)
├── Formula/                   # Homebrew formula
├── pyproject.toml            # Project metadata & dependencies
├── uv.lock                   # UV lock file
├── Makefile                  # Development commands
├── CLAUDE.md                 # Project-specific instructions
├── CHANGELOG.md              # Release notes
└── README.md                 # Project overview
```

## Directory Purposes

**config/**
- Purpose: Static configuration and reference data
- Contains: YAML reference tree, JSON taxonomies
- Key files: `personal_file_tree.yaml` (PARA structure), `thema.json` (9,187 book codes), `documents.json` (doc types)

**docs/**
- Purpose: User-facing documentation
- Contains: Guides, API references, troubleshooting, ADRs
- Key files: `docs/architecture/` (technical reference), `docs/cli/` (command docs), `docs/getting-started/` (onboarding)

**src/para_files/cli/**
- Purpose: Command-line interface layer
- Contains: Typer commands, shared utilities, logging setup
- Key files: `app.py` (Typer instance), `shared.py` (utilities)
- Pattern: Each command in `{name}_cmd.py`, imports `app` from `app.py`, registers via `@app.command()`

**src/para_files/classifiers/**
- Purpose: Implement 6-signal classification cascade
- Contains: BaseClassifier interface + 6 implementations
- Pattern: Each classifier returns `ClassificationResult | None`
- Execution order: BookDetector → RulesEngine → Taxonomy → Semantic → Extension → LLM

**src/para_files/utils/**
- Purpose: Reusable utility functions across the system
- Contains: File I/O, metadata extraction, validation, transformation
- Pattern: One module per concern (file_utils, ocr, pdf_metadata, etc.)

**tests/**
- Purpose: Test suite with pytest
- Contains: Unit tests, integration tests, fixtures
- Pattern: Test files mirror source structure, fixtures in `conftest.py`

## Key File Locations

**Entry Points:**
- `src/para_files/main.py` - Reexports `app` from `cli/app.py`, defines `main()` and `cli()` functions
- `src/para_files/cli/app.py` - Typer application instance

**Configuration:**
- `src/para_files/config.py` - Load & validate config from env/YAML/.env
- `config/personal_file_tree.yaml` - PARA structure + routing rules (user-provided)
- `config/thema.json` - Thema book taxonomy (bundled)
- `config/documents.json` - Document type taxonomy (bundled)

**Core Logic:**
- `src/para_files/pipeline.py` - 6-signal classification cascade
- `src/para_files/mover.py` - File movement with conflict handling
- `src/para_files/reference_tree.py` - YAML parsing for routing rules
- `src/para_files/learner.py` - Feedback tracking & rule extension

**Type Definitions:**
- `src/para_files/types.py` - All Pydantic models (ClassificationResult, FileMetadata, etc.)

**Testing:**
- `tests/conftest.py` - Pytest fixtures and configuration
- `tests/test_pipeline.py` - Pipeline tests
- `tests/test_*.py` - Command and component tests

## Naming Conventions

**Files:**
- Command files: `{command_name}_cmd.py` (e.g., `scan_cmd.py`, `move_cmd.py`)
- Classifier files: `{signal_name}_classifier.py` or `{detector_name}.py` (e.g., `semantic_classifier.py`, `book_detector.py`)
- Utility modules: `{concern_name}.py` (e.g., `file_utils.py`, `pdf_metadata.py`)
- Test files: `test_{module_name}.py` (e.g., `test_pipeline.py`, `test_classify_cmd.py`)

**Directories:**
- Command modules: `cli/` - All commands in this directory
- Classifier modules: `classifiers/` - All classifiers here
- Utility functions: `utils/` - Generic helpers
- Domain-specific: `learning/`, `taxonomies/`, `encoders/` - Organized by feature

**Functions:**
- Private functions: `_function_name()` (underscore prefix)
- Public functions: `function_name()`
- Abstract methods: `@abstractmethod` with no body

**Classes:**
- Classifiers: `{Name}Classifier` or `{Name}Detector` (e.g., `SemanticClassifier`, `BookDetector`)
- Configuration: `{Name}Config` (e.g., `MLXConfig`, `LLMConfig`)
- Domain models: Singular nouns (e.g., `ClassificationResult`, `FileMetadata`, `Route`)

**Variables:**
- Constants: `UPPERCASE_WITH_UNDERSCORES` (e.g., `_MAX_RENAME_ATTEMPTS`, `TEXT_EXTENSIONS`)
- Module-level private: `_variable_name` (e.g., `_reference_tree`)
- Instance variables: `self._private` (single underscore)
- Public: `self.public` (no underscore)

## Where to Add New Code

**New Feature (e.g., new classification signal):**
- Implementation: `src/para_files/classifiers/{signal_name}.py` - Extend `BaseClassifier`
- Registration: Add to pipeline init in `src/para_files/pipeline.py` line ~95 (priority order)
- Tests: `tests/test_{signal_name}.py`
- Types: Add enum to `ClassificationSource` if needed in `src/para_files/types.py`

**New CLI Command (e.g., new subcommand):**
- Implementation: `src/para_files/cli/{command_name}_cmd.py`
- Registration: Import in `src/para_files/main.py` line ~13-26
- Decorator: Use `@app.command()` (imported from `app.py`)
- Shared utilities: Extract to `src/para_files/cli/shared.py`
- Tests: `tests/test_{command_name}_cmd.py`

**New Utility Function:**
- Implementation: `src/para_files/utils/{concern_name}.py` - Create if doesn't exist
- Export: Add to `__all__` in module
- Tests: `tests/test_{concern_name}.py` or add to existing test file
- Docstrings: Include type hints and examples

**New Metadata Extractor (e.g., file format):**
- Implementation: `src/para_files/utils/{format}_metadata.py`
- Integration: Import in `src/para_files/utils/file_utils.py` → `extract_file_metadata()`
- Tests: `tests/test_{format}_metadata.py`

**Configuration Change:**
- Settings class: Add field to appropriate config class in `src/para_files/config.py`
- Environment variable: Follow prefix pattern (e.g., `PARA_FILES_MLX_`, `PARA_FILES_LLM_`)
- YAML section: Document in config section of `personal_file_tree.yaml`
- Defaults: Define at top of `config.py` (e.g., `DEFAULT_LLM_MODEL`)

## Special Directories

**config/** (checked in, user-editable)
- Purpose: Application configuration files
- Generated: No (user provides `personal_file_tree.yaml`)
- Committed: Yes - thema.json and documents.json are bundled
- Mutable: `personal_file_tree.yaml` modified by learn_cmd, migrate_cmd

**.planning/codebase/** (generated, read-only)
- Purpose: GSD codebase analysis documents
- Generated: Yes (via `/gsd:map-codebase` command)
- Committed: Yes
- Mutable: No - regenerated on each mapping

**tests/fixtures/** (checked in)
- Purpose: Test data and mock files
- Generated: No (manually created test data)
- Committed: Yes - essential for reproducible tests
- Contents: Sample PDFs, YAML files, JSON fixtures

**.mypy_cache/, .pytest_cache/, dist/** (generated, ignored)
- Purpose: Build/test artifacts
- Generated: Yes (by type checker, test runner, build tools)
- Committed: No (.gitignore)
- Cleaned: `make clean` removes these

**.venv/** (optional, ignored)
- Purpose: Virtual environment
- Generated: Yes (via `uv sync`)
- Committed: No (.gitignore)
- Use: `source .venv/bin/activate` or `uv run` prefix

## Code Organization Patterns

**Pipeline Initialization:**
```python
# Pipeline is lazy-initialized on first classification
# Thread-safe via double-checked locking
if self._initialized:
    return
with self._init_lock:
    if self._initialized:
        return
    self._do_initialize()
```

**Classifier Template:**
```python
class MyClassifier(BaseClassifier):
    @property
    def name(self) -> str:
        return "my_classifier"

    @property
    def source(self) -> ClassificationSource:
        return ClassificationSource.MY_SOURCE

    def classify(
        self,
        content: str,
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        # Return None if no match (next classifier tries)
        # Return ClassificationResult if match found (stop pipeline)
        pass
```

**Configuration Loading:**
```python
from para_files.config import load_config

config = load_config()  # Merges env vars > .env > YAML > defaults
pipeline = ClassificationPipeline(config)
```

**File Movement:**
```python
from para_files.mover import ConflictStrategy

result = mover.move_file(
    source=file_path,
    destination=target_path,
    strategy=ConflictStrategy.RENAME,
)
```

**Logging Pattern:**
```python
from loguru import logger

logger.debug("Classifying {}", file_path)
logger.info("Classified as {} ({}%)", category, confidence * 100)
logger.exception("Classifier {} failed", classifier.name)
```

**Type-Safe Results:**
```python
# Always check for None from classifiers
result = classifier.classify(content, metadata)
if result is not None:
    # Classifier matched
    category = result.category
    confidence = result.confidence.value
```
