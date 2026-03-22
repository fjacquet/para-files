# External Integrations

**Analysis Date:** 2026-03-22

## APIs & External Services

**Ollama (Primary):**
- Service: Local LLM and embedding server
- What it's used for: Text embeddings (semantic classification) and LLM fallback classification
- SDK/Client: litellm 1.50.0+
- Auth: None (local service)
- Endpoint: `http://localhost:11434` (configurable via `PARA_FILES_LLM_API_BASE`)
- Models used:
  - Embeddings: `nomic-embed-text` (768 dimensions, configured in `PARA_FILES_MLX_MODEL_NAME`)
  - LLM: `ministral-3:8b` (default, configurable via `PARA_FILES_LLM_MODEL`)

**Book Metadata (via isbnlib):**
- Service: Multiple fallback providers (Open Library, Wikipedia, Google Books)
- What it's used for: ISBN validation and book metadata enrichment for classification
- SDK/Client: isbnlib 3.10.14+
- Auth: None (public APIs with rate limiting)
- Files: `src/para_files/utils/isbn_lookup.py` (lines 34-80), `src/para_files/classifiers/book_detector.py`
- Lookup order: Open Library → Wikipedia → Google Books
- Behavior: Graceful fallback if all providers fail

**Geolocation (via geopy):**
- Service: OpenStreetMap (Nominatim) reverse geocoding
- What it's used for: Converting GPS coordinates to location names for file classification
- SDK/Client: geopy 2.4.1+
- Auth: None (public API with rate limits)
- Files: `src/para_files/utils/geolocation.py`
- Timeout: 5 seconds per request
- Cache: Two-level (in-memory LRU + persistent SQLite at `~/.cache/para-files/geolocation.db`)

**LiteLLM (Universal LLM Router):**
- Service: Unified API for Ollama, OpenAI, Anthropic, and other LLM providers
- What it's used for: Abstracts embedding and LLM calls to support multiple backends
- SDK/Client: litellm 1.50.0+
- Auth: API keys required only for non-local providers (OpenAI, Anthropic, Azure)
- Files: `src/para_files/encoders/ollama_encoder.py`, `src/para_files/classifiers/llm_classifier.py`
- Supported models format: `provider/model` (e.g., `ollama/nomic-embed-text`, `openai/gpt-4o-mini`)

## Data Storage

**Databases:**
- Type: Local SQLite (embedded, no server required)
- Purpose: Geolocation cache for reverse geocoding results
- Location: `~/.cache/para-files/geolocation.db`
- Client: sqlite3 (Python stdlib)
- Schema: Single table `geolocation_cache` with lat/lon/address_json

**File Storage:**
- Type: Local filesystem only (no cloud storage)
- Structure: PARA method (0_Inbox, 1_Projects, 2_Areas, 3_Resources, 4_Archives)
- Configuration: `PARA_FILES_PARA_ROOT` environment variable
- Reference tree: `config/personal_file_tree.yaml` (YAML, user-editable)
- Validated mappings: Optional JSON file at `PARA_FILES_VALIDATED_DB_PATH` for manual sender→category mappings

**Taxonomies (Read-Only):**
- Thema v1.6 (9,187 book classification codes): `config/thema.json` (3.6 MB)
- Document types (issuers, keywords, categories): `config/documents.json` (69.8 KB)
- Both loaded once at startup via `TaxonomyLoader` (thread-safe singleton)

**Logs:**
- Type: JSON-formatted rotating files
- Location: `{PARA_ROOT}/logs/operations.log`
- Rotation: Size-based (default 10 MB) or time-based
- Retention: Default 30 days
- Format: JSON serialization with async writes (thread-safe via loguru)
- Compression: gzip, bz2, xz, or zip

**Caching:**
- In-memory: LRU caches via `functools.lru_cache` for:
  - Thema taxonomy lookups
  - Document type classifications
  - ISBN metadata results
  - Geolocation results (up to 128 entries in memory, overflow to SQLite)
- Persistent: SQLite cache for geolocation at `~/.cache/para-files/geolocation.db`
- Pipeline state: Thread-safe singleton with lazy initialization (ADR-010)

## Authentication & Identity

**Auth Provider:**
- Type: None (no user authentication)
- System runs as filesystem automation with no user identity
- File access: Direct filesystem access (permissions inherited from OS)
- No API tokens required for local/open services

## Monitoring & Observability

**Error Tracking:**
- Type: None (no centralized error tracking)
- Approach: Structured JSON logs with full context

**Logs:**
- Framework: loguru 0.7.3+
- Format:
  - Console: Human-readable with colors (DEBUG level if verbose, INFO otherwise)
  - File: JSON format with structured fields for parsing
- Configuration:
  - Level: `PARA_FILES_LOG_LEVEL` (DEBUG, INFO, WARNING, ERROR)
  - Rotation: `PARA_FILES_LOG_ROTATION` (size-based, e.g., "10 MB")
  - Retention: `PARA_FILES_LOG_RETENTION` (e.g., "30 days")
  - Compression: `PARA_FILES_LOG_COMPRESSION` (gz, bz2, xz, zip)
- File: `src/para_files/logging.py` - setup_logging() configures both console and file output
- Silenced loggers: isbnlib (expected 404s), pypdf (malformed PDFs) to reduce noise

**Metrics:**
- Type: None (no metrics collection or telemetry)

## CI/CD & Deployment

**Hosting:**
- Type: Local/Desktop application (not server-based)
- Platform: macOS primary, cross-platform capable
- Distribution: PyPI (planned), wheel packages

**CI Pipeline:**
- Type: None yet (GitHub Actions workflows planned)
- Local: Makefile with full quality pipeline

**Build Process:**
- Builder: hatchling (from pyproject.toml)
- Output: Wheel distribution in `dist/`
- Entry point: `para-files` console script

## Environment Configuration

**Required Environment Variables:**
- `PARA_FILES_PARA_ROOT` - Root directory for PARA folders (required, defaults to ~/Documents/PARA)
- `PARA_FILES_REFERENCE_TREE_PATH` - Path to personal_file_tree.yaml (default: config/personal_file_tree.yaml)

**Optional Environment Variables - Embeddings:**
- `PARA_FILES_MLX_MODEL_NAME` - Embedding model (default: nomic-text-v1.5)
- `PARA_FILES_MLX_SCORE_THRESHOLD` - Min similarity score 0-1 (default: 0.75)
- `PARA_FILES_MLX_SEMANTIC_ENABLED` - Enable semantic classifier (default: true)
- `PARA_FILES_MLX_SEMANTIC_THRESHOLD` - Min similarity for semantic match (default: 0.65)

**Optional Environment Variables - LLM Fallback:**
- `PARA_FILES_LLM_ENABLED` - Enable LLM fallback (default: true)
- `PARA_FILES_LLM_MODEL` - Model identifier (default: ollama/ministral-3:8b)
- `PARA_FILES_LLM_API_BASE` - Ollama/provider endpoint (default: http://localhost:11434)
- `PARA_FILES_LLM_CONFIDENCE_THRESHOLD` - Min confidence 0-1 (default: 0.6)
- `PARA_FILES_LLM_TIMEOUT` - Request timeout in seconds (default: 15.0)

**Optional Environment Variables - Logging:**
- `PARA_FILES_LOG_LEVEL` - Log level (default: INFO)
- `PARA_FILES_LOG_ROTATION` - Rotation policy (default: 10 MB)
- `PARA_FILES_LOG_RETENTION` - Retention duration (default: 30 days)
- `PARA_FILES_LOG_COMPRESSION` - Compression format (default: gz)

**Optional Environment Variables - Processing:**
- `PARA_FILES_CONTENT_PREVIEW_CHARS` - Characters extracted for matching (default: 2000, min: 100, max: 10000)
- `PARA_FILES_MAX_WORKERS` - Parallel workers (default: 4, range: 1-16)

**Secrets Location:**
- Type: Environment variables or `.env` file
- Priority: Env vars > `.env` > `config:` section in YAML > defaults
- `.env` is git-ignored (never committed)

**Configuration Files:**
- Primary: `config/personal_file_tree.yaml` (user-maintained YAML with routing rules)
- Secondary: `.env` or `.env.local` for environment overrides
- Taxonomies: `config/documents.json`, `config/thema.json` (bundled, read-only)

## Webhooks & Callbacks

**Incoming:**
- Type: None (no webhook server)
- Approach: CLI-driven, no external callbacks

**Outgoing:**
- Type: None (no external webhooks)

## API Rate Limiting

**Ollama:**
- Type: None (local service)

**isbnlib (Book Metadata):**
- Open Library: Recommended ≤1 req/sec
- Google Books: Rate limited by Google (typically 100-1000 req/day per IP)
- Wikipedia: Rate limited (typically high for Nominatim-like usage)
- Fallback graceful: If all fail, book classification continues with other signals

**geopy (Geolocation):**
- Nominatim (OpenStreetMap): 1 req/sec recommended, cached to minimize calls
- Response caching: In-memory LRU + SQLite persistent cache
- Timeout: 5 seconds per request

## External Validation

**Validation Services:**
- ISBN validation: Built-in via isbnlib (no external call for validation, only metadata)
- File content: Local parsing via PyMuPDF, pypdf, openpyxl, etc.
- No external validation APIs used

---

*Integration audit: 2026-03-22*
