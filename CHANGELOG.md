# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Fuzzy matching for issuers**: TaxonomyClassifier now uses difflib.SequenceMatcher for typo tolerance
  - Threshold: 85% similarity required for fuzzy matches
  - Confidence penalty: 95% of base confidence for fuzzy matches
  - Handles OCR errors and misspellings (e.g., "Swicom" → "Swisscom")
  - Fuzzy matches tracked in extracted_params: `fuzzy_match`, `fuzzy_similarity`
- **PDF metadata for classification**: TaxonomyClassifier now uses PDF author/title/subject for better matching
  - PDF author is checked first for issuer matching (most reliable source)
  - PDF title/subject are prepended to content for keyword matching
  - New fields in FileMetadata: `pdf_title`, `pdf_author`, `pdf_subject`
  - extract_file_metadata() now extracts PDF metadata automatically
- **Retention-based folder suffixes**: TaxonomyClassifier now adds retention policy suffixes to folder names
  - `_perm` for permanent (stays in 3_Resources)
  - `_10y` for 10_years retention
  - `_5y` for 5_years retention
  - `_ctr` for contract_duration
  - `_2y` for warranty_2_years
  - `_ret` for retirement
  - Example: `4_Archives/fiscalite/{year}` → `4_Archives/fiscalite_10y/{year}`
  - Retention info now included in `extracted_params` of ClassificationResult
- **Updated documents.json with retention suffixes**: All 48 document types now have `para_pattern` with retention suffix
  - Automated update script at `scripts/update_documents_json.py`
  - Enables visual identification of retention requirements in folder structure
- **New `migrate` command**: Reorganizes existing files to retention-aware folder structure
  - Preview mode by default (`--dry-run`)
  - Filter by category (`--category fiscalite`)
  - JSON output for scripting (`--json`)
  - Automatic cleanup of empty directories (`--cleanup`)
  - Example: `uv run para-files migrate /path/to/PARA --no-dry-run`
- **THEMA book classification**: Book detector now uses official THEMA v1.6 international book classification
  - Replaces custom technology categories with standardized THEMA codes
  - PARA paths now use hybrid naming: `{CodeValue}_{ShortName}` (e.g., `3_Resources/livres/U_Informatique/UB_Programmation`)
  - Max 2 hierarchy levels for cleaner paths
  - Accents removed for filesystem compatibility (é→e, ç→c)
- **Centralized filename sanitization**: New `filename_sanitizer.py` utility for all filename/path operations
  - Handles all invalid characters: `, # " * : < > ? / \ |`
  - Used by book detector, geolocation, and Thema path building
  - New `thema_lookup.py` service for subject-to-THEMA code mapping
  - Supports computing, business, and science subject mappings
  - Result includes `thema_code` in extracted_params for traceability
- **New routing categories**:
  - `billets_avion` - Flight tickets with airline issuers (Swiss, Lufthansa, etc.)
  - `documents_voyage` - Travel documents (ESTA, Visa applications)
  - `conferences` - Professional conference registrations
  - `voyages` (hotels) - Hotel invoices with issuers (Radisson, Hilton, Marriott, Accor, etc.)
- **Filename date extraction**: New `date_source: "filename"` option extracts year from filenames
  - Supports patterns: `YYYY-MM-DD`, `YYYYMMDD`, and standalone `YYYY`
  - Used for conferences to avoid incorrect file modification dates
- **Content date extraction**: New `date_source: "content"` option extracts year from PDF content
  - Prioritizes fiscal year patterns (`Année fiscale`, `Exercice`, `Fiscal Year`)
  - Falls back to filename patterns, then removes `{YYYY}` from path if not found
  - Used for certificates where year is in document content
- **SONiC networking documentation routing**: Dell SONiC documents now route to Dell-EMC docs
  - Added `*[Ss]onic*` and `*SONiC*` patterns to dell_emc_documentation rule
  - Added `SONiC` and `Networking` to known_technologies
- **Issuer-based routing for IFU documents**: Bank documents now route by bank name
  - New `{issuer}` placeholder in routing rules for dynamic issuer extraction
  - Added `RuleIssuer` model in types.py for pattern-based issuer matching
  - Word boundary matching for accurate issuer detection (avoids "UBS" in "CLUBS")
  - IFU documents route to `4_Archives/banques/{issuer}/{YYYY}` (e.g., `Credit_Agricole/2023`)
  - Supported banks: Credit Agricole, BNP Paribas, Société Générale, LCL, Boursorama, Fortuneo
- **CAMT.053 bank statement routing**: ISO 20022 XML bank statements now route by bank
  - New `camt_statements` rule for CAMT.053 files
  - BIC code detection (BCVLCH2L, POFICHBE, UBSWCHZH, etc.)
  - Routes to `4_Archives/banques/{issuer}/{YYYY}` (e.g., `BCV/2025`)
- **Red Hat documentation routing**: Red Hat technical documents now route with technology subfolder
  - Patterns: `*[Rr]ed*[Hh]at*`, `*RH-*`, `*RHEL*`, `*[Oo]pen[Ss]hift*`, `*[Aa]nsible*`, `*AAP*`, etc.
  - Routes to `3_Resources/docs/Red_Hat/{technology}`
  - Known technologies: RHEL, OpenShift, Ansible, AAP, Satellite, JBoss, Ceph, Quay, ACM

### Fixed

- **Bug: `required_context` not loaded**: TaxonomyLoader was not loading `required_context` from documents.json
  - This caused false positives like hotel invoices matching "spectacles" due to "ticket" keyword
- **False positive "Zurich"**: Insurance issuer patterns now require "Zurich Versicherung/Insurance/Assurance"
  - Previously matched airport/city name in flight documents
- **False positive "Visa"**: Credit card keyword changed from "Visa" to "Carte Visa"
  - Added `required_context` for banking terms to prevent ESTA matches
- **False positive "certificat"**: Certificate patterns refined to exclude 3e pilier attestations
  - Removed generic `*[Cc]ertificat*` pattern
  - Added vendor-specific patterns: `EMC *[Cc]ertif*`, `VMware *[Cc]ertif*`, etc.
- **False positive "chat"**: Animaux category now requires animal-related context
  - Previously matched networking documents (SONiC) containing "chat" word
  - Added `required_context` with animal-specific terms (animal, vétérinaire, vaccination, etc.)
- **Year extraction 1976**: Previously extracted birth year from 3e pilier documents
  - TaxonomyClassifier now prioritizes fiscal year patterns in content
- **Year extraction with parentheses**: Filenames like `E-IFU - 2023(...)` now extract year correctly
  - Extended regex separators to include `(` and `)` characters
  - Previously failed for files like `E-IFU - 2023(31_12_2023).pdf`
- **European date formats in filenames**: Added support for DD_MM_YYYY, DD-MM-YYYY, DD.MM.YYYY
  - Previously only supported YYYY-MM-DD and YYYYMMDD formats
- **Enhanced fiscal year extraction from content**: Added many French fiscal patterns
  - Now matches: "réalisées en 2023", "perçus en 2023", "versés en 2023", "payés en 2023"
  - Also: "année 2023", "période 2023", "déclaration 2023", "IFU 2023"
  - Changed `ifu_documents` rule (formerly `banques_france`) to use `date_source: "content"` for accurate fiscal year
- **Bug: issuers not loaded from YAML**: `ReferenceTree._parse_routing_rules()` wasn't loading `issuers` field
  - Added parsing of `issuers` and `known_technologies` fields from routing rules
  - BIC codes like `BCVLCH2LXXX` now match patterns like `BCVLCH2L` (prefix matching)
- **False positive "Don"**: English "don't" was matching French "Don" keyword for donations
  - Changed keywords from generic "Don" to specific phrases: "Reçu de don", "Confirmation de don", etc.
  - Added `required_context` with French donation terms (reçu, attestation, déductible, merci, etc.)
- **CRITICAL: Prevented file deletion when source=destination**: Files already in correct location were being deleted as "duplicates"
  - Added safety check in `FileMover.move()` to skip when source.resolve() == destination.resolve()
  - Added defense-in-depth check in `_handle_duplicate()` with warning log
  - Files now return "skipped" with message "File already in correct location"
- **False positive "Orange"**: Color "orange" in product descriptions was matching Orange telecom
  - Changed pattern from generic `"Orange"` to specific: `"Orange France"`, `"Orange SA"`, `"orange.fr"`, etc.

### Changed

- **Pipeline v2.0**: Simplified from 6 signals to 4 signals for classification
  - Removed: ValidatedDB, DomainKB, SemanticRouter, LLMFallback (Ollama)
  - Added: TaxonomyClassifier, MLXLLMClassifier (native MLX-LM)
  - New signal order: RulesEngine (95%) → BookDetector (92%) → TaxonomyClassifier (90%) → MLX-LLM (60%)
- **Taxonomy-based classification**: Unified issuer + keyword matching via `documents.json`
  - Replaced separate DomainKB and SemanticRouter classifiers
  - All issuers migrated from YAML to JSON taxonomy
  - Word boundary matching for accurate issuer detection
- **MLX-LM native inference**: Replaced Ollama server with in-process MLX-LM
  - No external server required
  - Lazy model loading for fast startup
  - Supports mlx-community models (Qwen, Phi, Llama)
- **CLI refactoring**: Split `main.py` (1818 lines) into modular `cli/` package
  - One file per command (~400 lines max each)
  - Shared utilities in `cli/shared.py`
  - Backward compatibility maintained via re-exports
  - All 656 tests pass without modification
- **Move command**: `--cleanup-empty` now enabled by default (use `--no-cleanup-empty` to disable)

### Added

- **New routing rule**: `immobilier_france` for French real estate documents (SAFER, notaire, cadastre)
- **70+ new known issuers** from pre-classified invoice folders:
  - Banques: American Express, SwissQuote, Neon, TradeDirect, Credit Agricole...
  - Téléphonie: UPC, Orange, SFR, Bouygues Telecom, Cegetel...
  - Energie: EDF, ERDF, GDF, Engie
  - Matériels: digitec, Brack, Conrad, Hornbach, Apple, Nespresso...
  - Santé: M-Thérapies, Silhouette, Ostheopathe
  - Transport: AirFrance, Hertz, europcar, ByJuno...
  - Licences: Abbyy, Commvault, Crashplan, PearsonVue...
  - Dons: Unicef, Amnesty, Wikimedia, Croix Rouge, Rega...
- **Health reimbursement routing**: Extended patterns for `*Remboursement*invoice*`, `*M-Thérapies*`
- **Technology extraction for documents**: MLX-based semantic matching for technology categorization
  - New `TechnologyExtractor` utility class with dual-strategy detection
  - Filename pattern matching for fast detection (95% confidence)
  - Content-based MLX semantic similarity for accurate detection
  - Supports 25+ technologies: MariaDB, PostgreSQL, Kubernetes, VMware, Docker, etc.
  - Used for `{technology}` placeholder in routing destinations
  - BookDetector refactored to use TechnologyExtractor (removes code duplication)
- **Dell-EMC documentation routing**: Automatic classification with technology subfolders
  - Patterns for PowerFlex, PowerStore, VxRail, Unity, Isilon docs
  - Dell document prefix `H[0-9]*_*` detection
  - Technology extraction routes to `3_Resources/docs/Dell-EMC/{technology}`

### Fixed

- **MLX encoder token limit handling**: Improved error recovery for texts exceeding model's token limit
  - Default `max_chars` increased to 1000 (from 700) for better content coverage
  - Added `fallback_chars` (700) for automatic retry on IndexError
  - Uses `logging.exception` for better error diagnostics

### Added

- **Parallel file processing**: Configurable multi-threaded classification for faster processing
  - New `max_workers` configuration option (default: 1, max: 16)
  - Set via `PARA_FILES_MAX_WORKERS` environment variable or in config
  - `classify` and `scan` commands support parallel processing
  - `move` command remains sequential for file operation safety
  - Thread-safe lazy loading of MLX encoder with double-check locking
  - Thread-safe SQLite geolocation cache with RLock synchronization
- **Intelligent Inbox Cleanup** (`clean` command): Automated cleanup of temporary and junk files
  - Removes Apple temp files: `.DS_Store`, `._*` (AppleDouble), `.Spotlight-V100`, `.Trashes`
  - Removes Windows temp files: `Thumbs.db`, `desktop.ini`
  - Removes editor backup files: `*~`, `.swp`, `.swo`
  - Optional `.nfo` file cleanup with `--nfo` flag
  - Empty directory removal with bottom-up traversal
  - Audit logging to JSON (`--log` option)
  - Full dry-run support with `--dry-run`
- **NFO file parser**: Extracts classification hints from `.nfo` files
  - Parses title, category, year, author, publisher, language, tags
  - Multi-encoding support (UTF-8, CP437, Latin-1, Windows-1252)
  - Automatic association with media files
- **Move command enhancements**:
  - `--skip-unclassifiable`: Skip files that cannot be classified instead of warning
  - `--cleanup-empty`: Remove empty directories after moving files
- **Automatic duplicate detection**: Smart deduplication when moving files
  - Compares files with same name by SHA256 hash before moving
  - Deletes source file if identical to destination (avoids creating `file_1.txt`, `file_2.txt`)
  - Quick size check before expensive hash computation
  - Enabled by default, can be disabled with `deduplicate=False`
  - Full dry-run support showing "would delete duplicate"
- **Dedupe command** (`dedupe`): Cleanup suffixed duplicate files
  - Scans for files with `_N` suffix (e.g., `file_1.pdf`, `document_2.txt`)
  - Compares with original file by SHA256 hash
  - Deletes suffixed duplicates if content is identical
  - Keeps files with different content (reports them in verbose mode)
  - Supports `--dry-run`, `--recursive`, `--json`, `--verbose` options
- New utilities in `para_files.utils`:
  - `cleanup.py`: Junk file detection and deletion
  - `nfo_parser.py`: NFO file parsing with encoding fallback
  - `cleanup_log.py`: Audit logging for cleanup operations
- **Geolocation for photos and videos**: Photos and videos with GPS EXIF data now include location in the destination path (e.g., `4_Archives/photos/2024/Switzerland/Geneva/06/IMG_1234.jpg`)
  - Separate `{country}` and `{location}` placeholders for flexible path configuration
  - Uses reverse geocoding via Nominatim/OpenStreetMap
  - LRU-cached lookups for efficiency
  - Graceful fallback when no GPS data or lookup fails
- **Makefile**: Standardized build automation
  - `make all`: Full pipeline (deps, setup, lint, format, typecheck, test)
  - `make quality`: Quick lint + typecheck
  - `make fix`: Auto-fix linting issues
  - `make test-cov`: Run tests with coverage
  - `make clean`: Remove build artifacts
- **Book detector classifier** (Signal 2.5, 92% confidence): Intelligent detection of technical books in PDF format
  - Multi-signal analysis: ISBN extraction, PDF metadata, content structure, file size
  - ISBN lookup via Google Books/Open Library for book enrichment
  - Automatic technology categorization (Python, JavaScript, Kubernetes, etc.)
  - Routes books to `3_Resources/livres/{technology}`
- New `BOOK_DETECTOR` classification source for book detection results
- `geopy` dependency for GPS reverse geocoding
- Comprehensive test suite for book detection (83 new tests, 621 total)
- New routing rules based on inbox analysis:
  - `.dng` (Adobe DNG raw) extension added to photos
  - VMware documentation routing (`*VMware*`, `*vSphere*`, `*vSAN*`, etc.)
  - Training certificates routing (`*Certificate*`, `*Completion*`, `*Badge*`)
  - Software licenses routing (`.lic`, `.license`, `.key` extensions)
  - Financial transactions CSV routing
  - French tax documents route (`impots-france`)
  - TV redevance route with Serafe/Billag issuers
- New known issuers:
  - Transport: Mobility, mobility-genossenschaft (car sharing)
  - Redevances: Serafe, Billag (TV/radio tax)
- **documentation-master** Claude Code skill for documentation guardianship and onboarding:
  - Developer onboarding guide with environment setup and codebase orientation
  - User onboarding guide with quick start and common workflows
  - Documentation templates for README, CHANGELOG, docstrings, and PRs
  - Audit checklists for quick, weekly, monthly, and pre-release reviews
- GitHub Actions CI workflow with macOS-14 runner (Apple Silicon)
- New 2_Areas routes for personal collections:
  - `perso-photos`: Collection photos personnelles
  - `perso-notebooks`: Notes personnelles (OneNote, carnets)
  - `perso-mindmaps`: Cartes mentales (xmind)
  - `perso-wallpapers`: Fonds d'écran
- New 3_Resources routes with organized structure:
  - `livres/{technology}`: Livres techniques par technologie (Ansible, Python, Go, etc.)
  - `cours/{topic}`: Formations et cours par sujet (AI, Cloud, Security, etc.)
- Known technologies for livres: 19 categories (Ansible, C++, Cloud, Containers, etc.)
- Known topics for cours: 19 categories (AI, Automation, Cloud, Containers, etc.)
- GitHub Pages documentation site with Jekyll
- Dependabot for automated dependency updates
- MIT LICENSE file
- CONTRIBUTING.md with development guidelines
- Architecture documentation with Mermaid diagrams
- New routes in reference tree (from all-files.txt analysis):
  - `factures-materiels`: Shopping/retail invoices (fnac, Migros, Manor, digitec, etc.)
  - `factures-prevoyance`: Pension documents (2e/3e pilier, LPP, libre passage)
  - `factures-enfant`: Children expenses (crèche, garderie, activités)
  - `factures-voyages`: Travel documents and invoices
  - `salaires`: Salary archives by employer/year
- New known issuers:
  - Assurances: Generali, SwissCaution, Swiss Life, Maif, Allianz, ECA
  - Cloud: SwitchPlus, Azure, Infomaniak, AWS, OVH, Hetzner
  - Santé: CHUV, HUG, Pharmacie
  - Materiels: fnac, Migros, Manor, coop@home, digitec, Galaxus, Nespresso
  - Prévoyance: Generali, Vaudoise, Swiss Life, Retraites Populaires, PUBLICA
  - Enfant: Commune de Montreux, Leukerbad Skischule
  - Voyages: ebookers, Interhome, Ulys, Kontiki, airlines

### Documentation

- Fixed Jekyll just-the-docs navigation structure:
  - Created missing parent pages: `cli.md`, `tasks.md`, `configuration.md`, `troubleshooting.md`, `advanced.md`
  - Added `has_children: true` to parent pages enabling proper sidebar navigation
  - Fixed broken links in `index.md` (mlx-embeddings, custom-classifier)
  - Standardized `nav_order` across all parent pages for logical menu ordering

### Changed

- Moved `personal_file_tree.yaml` to `config/` folder
- Centralized configuration defaults in `config.py`
- LLM fallback now uses configurable content preview chars
- Enhanced `factures-cloud` route with AWS, Azure, Infomaniak utterances
- **Breaking**: Changed all factures patterns from `{year}/Category/{issuer}` to `Category/{issuer}/{year}` for better folder organization
- **Breaking**: Restructured archives for proper PARA semantics:
  - `banques` → `4_Archives/banques/{issuer}/{year}` (bank statements, not invoices)
  - `impots` → `4_Archives/impots/{year}` (tax declarations)
  - `prevoyance` → `4_Archives/prevoyance/{issuer}/{year}` (pension attestations)
  - `voyages` → `4_Archives/voyages/{destination}/{year}` (travel documents)
  - `dons` → `4_Archives/dons/{organization}/{year}` (donation receipts)
  - Only actual invoices remain under `factures/`

### Fixed

- Hardcoded content preview limit in LLM fallback classifier

## [0.1.0] - 2025-12-26

### Added

- Initial release with 5-signal classification pipeline
- MLX semantic routing using `nomic-embed-text-v1.5` embeddings
- PARA folder structure support (Projects, Areas, Resources, Archives)
- CLI commands: `classify`, `move`, `scan`, `init`, `tree`, `routes`, `issuers`
- Learning commands: `learn`, `add-issuer`, `add-utterance`, `test-route`
- Configuration management with YAML reference tree
- Multi-file support for classify and move commands
- Dry-run mode for safe previewing
- JSON output format for scripting
- Conflict resolution strategies (skip, overwrite, rename, rename_with_date)
- Date prefix option for organized file naming

### Technical

- macOS-only (Apple Silicon required for MLX)
- Python 3.12+ with strict type checking
- Pydantic for configuration validation
- Comprehensive test suite (318+ tests)
