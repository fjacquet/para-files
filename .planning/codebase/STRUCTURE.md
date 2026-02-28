# Codebase Structure

**Analysis Date:** 2026-02-28

## Directory Layout

```
/Users/fjacquet/Projects/para-files/
├── src/
│   └── para_files/              # Main package
│       ├── __init__.py          # Package exports (__version__, main entry points)
│       ├── main.py              # CLI entry point (delegates to cli.app)
│       ├── config.py            # Pydantic settings models
│       ├── types.py             # Type definitions (ClassificationResult, etc.)
│       ├── pipeline.py          # Classification pipeline orchestrator
│       ├── reference_tree.py    # YAML reference tree loader
│       ├── logging.py           # Loguru configuration
│       ├── mover.py             # FileMover for file operations
│       ├── learner.py           # Learning system for manual mappings
│       │
│       ├── cli/                 # CLI commands
│       │   ├── __init__.py      # Imports all command modules
│       │   ├── app.py           # Typer app instance
│       │   ├── shared.py        # Shared utilities (setup_logging, validation, output formatting)
│       │   ├── classify_cmd.py  # Classification command
│       │   ├── scan_cmd.py      # Preview classifications without moving
│       │   ├── move_cmd.py      # Move files to PARA destinations
│       │   ├── learn_cmd.py     # Learn from manual file placements
│       │   ├── bookstore_cmd.py # Intelligent book classification/organization
│       │   ├── tree_cmd.py      # Show PARA folder structure
│       │   ├── routes_cmd.py    # Show routing rules
│       │   ├── config_cmd.py    # Show configuration
│       │   ├── clean_cmd.py     # Clean up empty directories
│       │   ├── dedupe_cmd.py    # Find duplicate files
│       │   ├── init_cmd.py      # Initialize PARA structure
│       │   ├── migrate_cmd.py   # Migrate files from old structure
│       │   └── rescan_cmd.py    # Rescan files with updated rules
│       │
│       ├── classifiers/         # 5-signal classification pipeline
│       │   ├── base.py          # BaseClassifier abstract interface
│       │   ├── book_detector.py # Signal 1: ISBN/PDF book detection
│       │   ├── rules_engine.py  # Signal 2: Glob pattern matching
│       │   ├── taxonomy_classifier.py  # Signal 3: Domain knowledge (issuers, keywords)
│       │   ├── semantic_classifier.py  # Signal 4: MLX embeddings
│       │   ├── mlx_llm_classifier.py   # Signal 5: Optional MLX-LLM fallback
│       │   └── __init__.py      # Classifier module exports
│       │
│       ├── encoders/            # Embedding model handling
│       │   ├── base.py          # BaseEncoder abstract
│       │   ├── mlx_encoder.py   # MLX embedding implementation (lazy loading)
│       │   └── __init__.py
│       │
│       ├── taxonomies/          # Taxonomy data loaders
│       │   ├── loader.py        # TaxonomyLoader: loads documents.json + thema.json
│       │   ├── models.py        # Thema/document data models
│       │   └── __init__.py
│       │
│       ├── learning/            # Learning system
│       │   ├── pattern_extractor.py  # Extract patterns from filenames/content
│       │   ├── feedback_tracker.py   # Track user feedback
│       │   └── __init__.py
│       │
│       └── utils/               # Utility functions
│           ├── file_utils.py    # File metadata extraction + content reading
│           ├── validation.py    # Path validation
│           ├── filename_sanitizer.py  # Sanitize filenames for filesystem
│           ├── filename_detector.py   # Detect generic filenames (scan_001.pdf)
│           ├── smart_renamer.py       # Suggest renames based on OCR
│           ├── pdf_metadata.py        # Extract PDF metadata
│           ├── epub_metadata.py       # Extract EPUB metadata
│           ├── mobi_metadata.py       # Extract MOBI metadata
│           ├── chm_metadata.py        # Extract CHM metadata
│           ├── exiftool.py            # EXIF data extraction
│           ├── pandoc.py              # File conversion to text
│           ├── ocr.py                 # OCR using Vision Framework
│           ├── ocr_metadata.py        # Extract structured data from OCR results
│           ├── isbn_lookup.py         # ISBN → book metadata lookup
│           ├── thema_lookup.py        # Thema code information
│           ├── technology_extractor.py # Extract tech keywords from content
│           ├── geolocation.py         # GPS coordinates → location names
│           ├── nfo_parser.py          # Parse .nfo metadata files
│           ├── cleanup.py             # Empty directory cleanup
│           └── __init__.py
│
├── tests/                       # Test suite
│   ├── conftest.py              # Pytest fixtures and configuration
│   ├── fixtures/                # Test data (sample files, YAML, JSON)
│   ├── test_classifiers.py      # Classifier tests
│   ├── test_pipeline.py         # Pipeline orchestration tests
│   ├── test_main.py             # CLI command tests
│   ├── test_config.py           # Configuration loading tests
│   ├── test_types.py            # Type definitions tests
│   ├── test_reference_tree.py   # YAML parsing tests
│   ├── test_mover.py            # File movement tests
│   ├── test_learner.py          # Learning system tests
│   ├── test_encoders.py         # Embedding encoder tests
│   ├── test_file_utils.py       # File utility tests
│   ├── test_pdf_metadata.py     # PDF parsing tests
│   ├── test_epub_metadata.py    # EPUB parsing tests
│   ├── test_mobi_metadata.py    # MOBI parsing tests
│   ├── test_book_detector.py    # Book detection tests
│   ├── test_rules_engine.py     # Routing rules tests
│   ├── test_isbn_lookup.py      # ISBN lookup tests
│   ├── test_thema_taxonomy.py   # Thema classification tests
│   ├── test_*_cmd.py            # Individual command tests
│   └── ...
│
├── config/                      # Configuration files
│   ├── personal_file_tree.yaml  # PARA reference tree (example)
│   └── thema.json               # Thema v1.6 book classification (9,187 codes)
│
├── docs/                        # User documentation
│   ├── index.md                 # Overview
│   ├── getting-started/         # Installation + quick start
│   ├── cli/                     # Command reference
│   ├── configuration/           # Settings guide
│   ├── tasks/                   # How-to guides
│   ├── architecture/            # Technical deep dives
│   └── troubleshooting/         # Common issues
│
├── scripts/                     # Build and utility scripts
│
├── .planning/                   # GSD planning documents (generated)
│   └── codebase/                # Analysis documents
│
├── pyproject.toml               # Project metadata and dependencies
├── CLAUDE.md                    # Development guidelines (this project)
├── README.md                    # User-facing overview
├── CHANGELOG.md                 # Version history
└── .env.example                 # Example environment variables
```

## Directory Purposes

**`src/para_files/`:**

- Purpose: Main application package
- Contains: All Python source code
- Key files: `main.py` (entry), `pipeline.py` (core), `config.py` (settings)

**`src/para_files/cli/`:**

- Purpose: Command-line interface commands
- Contains: Individual command modules, shared utilities
- Key files: `app.py` (Typer instance), `shared.py` (utilities), `classify_cmd.py` (main command)

**`src/para_files/classifiers/`:**

- Purpose: Implement 5-signal classification strategy
- Contains: BaseClassifier interface + 5 concrete implementations
- Key files: `base.py` (interface), `book_detector.py`, `rules_engine.py`, `semantic_classifier.py`

**`src/para_files/utils/`:**

- Purpose: Cross-cutting utilities and external integrations
- Contains: File handling, metadata extraction, external API calls
- Key files: `file_utils.py` (metadata), `exiftool.py` (EXIF), `pdf_metadata.py`, `isbn_lookup.py`

**`tests/`:**

- Purpose: Automated test suite
- Contains: Unit tests, integration tests, test fixtures
- Pattern: One test file per source module (test_classifiers.py for classifiers/)

**`config/`:**

- Purpose: Configuration and data files
- Contains: Example reference tree, Thema classification codes
- Files: `personal_file_tree.yaml` (PARA structure), `thema.json` (book classification)

**`docs/`:**

- Purpose: User-facing documentation
- Contains: How-to guides, API reference, architecture documentation
- Pattern: Organized by audience/task (getting-started, configuration, troubleshooting)

## Key File Locations

**Entry Points:**

- `src/para_files/main.py`: Main function (called by pyproject.toml entry point)
- `src/para_files/cli/app.py`: Typer application instance (all commands register here)

**Configuration:**

- `src/para_files/config.py`: Config models, load_config() function
- `config/personal_file_tree.yaml`: PARA reference tree (example)

**Core Logic:**

- `src/para_files/pipeline.py`: ClassificationPipeline orchestrator
- `src/para_files/classifiers/`: 5-signal classification implementations
- `src/para_files/reference_tree.py`: YAML tree parsing

**File Operations:**

- `src/para_files/mover.py`: FileMover for file movement
- `src/para_files/utils/file_utils.py`: Metadata extraction + content reading

**Learning System:**

- `src/para_files/learner.py`: Learner for manual mappings
- `src/para_files/learning/pattern_extractor.py`: Pattern extraction

**Testing:**

- `tests/conftest.py`: Pytest fixtures
- `tests/test_pipeline.py`: Pipeline tests
- `tests/test_classifiers.py`: Classifier tests
- `tests/test_main.py`: CLI command tests

## Naming Conventions

**Files:**

- `*_cmd.py`: CLI command modules (classify_cmd.py, scan_cmd.py)
- `test_*.py`: Test files (test_classifiers.py, test_pipeline.py)
- `*.yaml`: Configuration files
- `*.json`: Data files (thema.json)

**Directories:**

- Plural nouns for module collections: `classifiers/`, `utils/`, `taxonomies/`
- Lowercase with underscores: `para_files/`, `cli/`, `learning/`

**Functions:**

- `camelCase` for private/internal: `_ensure_initialized()`, `_classify_single_file()`
- `snake_case` for public: `classify()`, `classify_file()`, `load_config()`

**Classes:**

- `PascalCase` for all classes: `ClassificationPipeline`, `BaseClassifier`, `FileMetadata`
- Abstract base classes prefixed: `BaseClassifier`, `BaseEncoder`

**Constants:**

- `UPPER_CASE` with underscores: `_MIN_CONTENT_FOR_RENAME`, `MAX_PATTERNS_SHOWN`
- Prefixed with underscore if module-private: `_MAX_RENAME_ATTEMPTS`

## Where to Add New Code

**New CLI Command:**

- Create: `src/para_files/cli/new_cmd.py`
- Implement: Function decorated with `@app.command()`
- Register: Import in `src/para_files/cli/__init__.py`
- Tests: `tests/test_new_cmd.py`

**New Classification Signal:**

- Create: `src/para_files/classifiers/new_classifier.py`
- Implement: Class inheriting from `BaseClassifier`
- Register: Add to pipeline in `src/para_files/pipeline.py::_ensure_initialized()`
- Tests: `tests/test_classifiers.py` (add test case)

**New Utility Function:**

- Create: In appropriate `src/para_files/utils/*.py` file
- Pattern: Pure function, no side effects, comprehensive type hints
- Tests: Corresponding `tests/test_*.py` file

**New Data Type:**

- Add: `src/para_files/types.py` (Pydantic model)
- Pattern: Use Field() with description, constraints, defaults
- Import: From `para_files.types` in consumers

## Special Directories

**`.planning/codebase/`:**

- Purpose: Generated analysis documents for GSD orchestrator
- Contents: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md, STACK.md, INTEGRATIONS.md
- Generated: By `/gsd:map-codebase` command
- Committed: Yes (tracked in git)

**`.venv/`:**

- Purpose: Python virtual environment
- Generated: Yes (created by `uv sync`)
- Committed: No (.gitignore)

**`.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`:**

- Purpose: Tool caches
- Generated: Yes
- Committed: No (.gitignore)

**`docs/`:**

- Purpose: User documentation
- Committed: Yes (tracked in git)
- Pattern: Markdown files, cross-linked

**`config/`:**

- Purpose: Example/bundled configuration files
- `thema.json`: Bundled (all 9,187 Thema codes)
- `personal_file_tree.yaml`: Example (not personalized data)
- Committed: Yes

**`.serena/`, `.vscode/`:**

- Purpose: Editor configuration
- Generated: Partially (VS Code creates)
- Committed: Yes (track project settings, not personal config)

---

*Structure analysis: 2026-02-28*
