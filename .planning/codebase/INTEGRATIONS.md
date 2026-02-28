# External Integrations

**Analysis Date:** 2026-02-28

## APIs & External Services

**ISBN Metadata Lookup:**

- Google Books API (via isbnlib)
  - SDK/Client: `isbnlib` 3.10.14+
  - Usage: `src/para_files/utils/isbn_lookup.py` - BookInfo lookup via lookup_isbn()
  - Fallback: Multiple sources (Google Books, Open Library, Wikipedia)
  - Credentials: None required (public API)

**Book Classification:**

- Thema (international book classification system)
  - Data source: `config/thema.json` - Pre-loaded 9,187 classification codes
  - Usage: `src/para_files/taxonomies/models.py` - ThemaTaxonomy model
  - Integration: `src/para_files/utils/thema_lookup.py` - Code lookup and path building
  - Credentials: None (offline data)

**Reverse Geocoding:**

- geopy (OSM Nominatim, fallback providers)
  - SDK/Client: `geopy` 2.4.1+
  - Usage: `src/para_files/utils/geolocation.py` - reverse_geocode() function
  - Purpose: Convert GPS coordinates to location names
  - Cache: Two-level (in-memory LRU + persistent SQLite at ~/.cache/para-files/geolocation.db)
  - Timeout: 5 seconds per request
  - Credentials: None (public API, though rate-limited)

## Data Storage

**Databases:**

- None (no persistent relational database)

**File Storage:**

- Local filesystem only
  - PARA folder structure: `$PARA_ROOT/0_Inbox, 1_Projects, 2_Areas, 3_Resources, 4_Archives`
  - Cache: `~/.cache/para-files/` - Geolocation SQLite DB, HuggingFace model cache
  - Logs: `$PARA_ROOT/logs/operations.log` (JSON format with rotation)

**Caching:**

- HuggingFace transformers cache: `~/.cache/huggingface/` (MLX models)
- In-memory: LRU caches for YAML parsing, geolocation lookups
- Persistent: SQLite geolocation cache at ~/.cache/para-files/geolocation.db

## Machine Learning Models

**Embedding Models:**

- MLX embedding models (mlx-community registry)
  - Default: `mlx-community/nomic-embed-text-v1.5` (768-dimensional)
  - Configurable via: PARA_FILES_MLX_MODEL_NAME environment variable
  - Download source: HuggingFace Hub (via mlx-embedding-models)
  - Cache location: ~/.cache/huggingface/
  - Size: ~100MB for nomic-embed-text-v1.5
  - Hardware: Apple Neural Engine (MLX optimized)
  - Integration: `src/para_files/encoders/mlx_encoder.py` - MLXEncoder class
  - Used by: `src/para_files/classifiers/semantic_classifier.py` - Signal 4 semantic routing

**Language Models (Optional LLM Fallback):**

- MLX-LM native models (recommended):
  - Default: `mlx-community/Qwen2.5-1.5B-Instruct-4bit` (1-2GB)
  - Alternatives: Phi-3.5-mini, Llama-3.2-3B (all 4-bit quantized)
  - Integration: `src/para_files/classifiers/mlx_llm_classifier.py` - Signal 6 LLM fallback
  - Control: PARA_FILES_LLM_ENABLED (false by default)

- Alternative: litellm for remote models
  - Supported: OpenAI (gpt-4o-mini), Anthropic (claude-3-haiku), Ollama local
  - Integration: Not directly in code, but supported via litellm configuration
  - Control: PARA_FILES_LLM_MODEL, PARA_FILES_LLM_API_BASE

## Authentication & Identity

**Auth Provider:**

- None (no authentication required)
- ISBN/book lookup: Public APIs (no credentials)
- Geocoding: Public APIs (no authentication, but rate-limited)
- HuggingFace model download: No authentication (public models)

## Monitoring & Observability

**Error Tracking:**

- None (no external service integration)

**Logs:**

- Local file-based: `$PARA_ROOT/logs/operations.log` (JSON format)
  - Framework: loguru
  - Rotation: Size-based (default: 10 MB)
  - Retention: Time-based (default: 30 days)
  - Compression: gzip (configurable)
  - Configuration: `src/para_files/logging.py` and config.LoggingConfig

## CI/CD & Deployment

**Hosting:**

- None (local macOS application only)

**CI Pipeline:**

- GitHub Actions (defined in .github/workflows/)
- Triggered on: Pull requests, pushes to maincd
- Jobs: Lint (Ruff), Type check (mypy), Test (pytest)

**Code Quality Gates:**

- Linting: Ruff (pre-commit hook + CI)
- Type checking: mypy strict mode (pre-commit hook + CI)
- Security: bandit + gitleaks (pre-commit hooks)
- Commit messages: commitizen validation (pre-commit hook)
- Test coverage: 80% minimum (pytest-cov)

## Webhooks & Callbacks

**Incoming:**

- None

**Outgoing:**

- None

## Validated Database

**Manual Mappings:**

- Path: PARA_FILES_VALIDATED_DB_PATH (optional JSON file)
- Format: `{"sender@domain.com": "2_Areas/Category/Path"}`
- Purpose: Manual overrides for known senders (highest priority in classification pipeline)
- Integration: `src/para_files/classifiers/validated_db.py` - Signal 1 (if implemented)
- Usage: Stores user feedback from interactive learning (`learn` command)

## Reference Tree (YAML Configuration)

**File:** `config/personal_file_tree.yaml`

**Sections:**

1. `config:` - Settings overrides (PARA root, MLX model, LLM settings, etc.)
2. `routes:` - Semantic routes (category descriptions for embedding similarity)
3. `rules:` - Glob pattern matching rules (filename/path patterns → categories)
4. `issuers:` - Known sender → category mappings (email, domain patterns)
5. `retention:` - Document retention rules by category
6. `categories:` - PARA folder descriptions and metadata

**Integration Points:**

- Loaded by: `src/para_files/reference_tree.py` - ReferenceTree class
- Configuration layer: `src/para_files/config.py` - load_config() uses YAML config section
- Used by: All classifiers (RulesEngineClassifier, SemanticClassifier, DomainClassifier)

## External Files & Taxonomies

**Document Taxonomy:**

- File: `config/documents.json` (69.6KB)
- Source: Swiss administrative document taxonomy
- Format: JSON
- Purpose: Maps document issuers to canonical paths
- Integration: `src/para_files/taxonomies/loader.py` - TaxonomyLoader.load_documents()

**Book Taxonomy:**

- File: `config/thema.json` (3.6MB)
- Source: Thema Classification Editorial Board (v1.6, 9,187 codes)
- Format: JSON with nested hierarchies
- Purpose: Book classification (Signal 2 - BookDetector)
- Integration: `src/para_files/taxonomies/models.py` - ThemaTaxonomy model
- Usage: `src/para_files/utils/thema_lookup.py` - get_thema_lookup()

## Platform-Specific Integrations

**macOS Vision Framework:**

- Framework: Vision (PyObjC binding)
- Package: `pyobjc-framework-vision` 12.1+
- Usage: OCR text extraction from images/PDFs
- Location: `src/para_files/utils/ocr.py` - extract_text_vision()
- Availability: macOS only (fallback when unavailable)
- Features: Language detection, confidence scoring

**macOS Cocoa Framework:**

- Framework: Cocoa
- Package: `pyobjc-framework-cocoa` 12.1+
- Usage: macOS-specific file system operations
- Platform constraint: macOS only

**macOS Quartz Framework:**

- Framework: Quartz/CoreGraphics
- Package: `pyobjc-framework-quartz` 12.1+
- Usage: Low-level graphics/PDF rendering operations
- Platform constraint: macOS only

## Async HTTP Client

**Library:** httpx 0.28.1+

- Purpose: Async HTTP requests for ISBN/metadata lookups
- Integration: Used by isbnlib indirectly for API calls
- Credentials: None (public APIs)
- Timeout: Varies by integration (5 seconds for geopy)

## No External Integrations For

- **Email:** Not integrated
- **Cloud storage:** Not integrated (local filesystem only)
- **Version control:** Git-aware (respects .gitignore) but no direct Git API integration
- **Web APIs:** No webhook servers or REST API (CLI-only)
- **Databases:** No SQL/NoSQL dependencies
- **Message queues:** No async task queues
- **Service discovery:** Not applicable (standalone app)

---

*Integration audit: 2026-02-28*
