# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Placeholder resolver utility** (`para_files/utils/placeholder_resolver.py`): New shared `clean_unreplaced_placeholders()` function replaces three divergent implementations across `rules_engine.py`, `semantic_classifier.py`, and `taxonomy_classifier.py` — eliminates 43 lines of duplicated regex logic and ensures consistent cleanup of `{year}`, `{issuer}`, `{location}`, and other template tokens
- **Pipeline exception isolation tests**: New `TestClassificationPipeline` methods prove that a classifier raising `RuntimeError` or `ValueError` is skipped and the next classifier runs, rather than crashing the entire pipeline
- **Concurrent bookstore conflict resolution tests**: `TestConcurrentIsbnDeduplication` and `TestFileMoverConcurrentConflicts` prove that 5 concurrent workers registering the same ISBN produce exactly 1 winner with no data loss, and that `ConflictStrategy.RENAME` produces unique filenames under concurrent writes
- **Rules engine edge case tests**: 14 new tests in `TestUnicodeAndSpecialCharFilenames` and `TestOverlappingPatterns` cover accented Latin filenames (Résumé, Décompte), CJK filenames, glob metacharacters in filenames (`[`, `]`, `*`), parentheses, ampersand, first-rule-wins ordering, and AND logic (extension + pattern must both match)
- **MLX encoder per-text progressive truncation** (`_encode_single`): Replaces the silent zero-vector batch fallback with a 4-level retry (700 / 400 / 200 / 100 chars) — technical specifications, source code, and symbol-dense documents now receive a real semantic embedding instead of a zero vector

### Fixed

- **File extension case sensitivity** (`file_utils.py`): `FileMetadata.extension` is now normalized to lowercase at construction time — files named `.PDF`, `.EPUB`, `.CHM` are now classified correctly instead of falling through extension checks
- **OCR rename confidence threshold** (`config.py`): Default `OCRRenameConfig.min_confidence` raised from `0.3` to `0.7` — bank statement headers and other low-signal text no longer trigger erroneous file renames
- **Silent ISBN enrichment failures** (`isbn_lookup.py`): Bare `pass` statements replaced with `logger.warning("ISBN description/cover URL enrichment failed for {isbn}: {ExcType} {msg}")` — enrichment failures are now visible in logs with the specific step (description vs. cover URL) that failed
- **Silent PDF page extraction failures** (`pdf_metadata.py`): Bare `except` in the page loop now calls `logger.debug("Failed to extract text from page {N} of {file}: {ExcType} {msg}")` — corrupted or encrypted pages are traceable without flooding logs
- **Missing file misreported as OCR failure** (`pipeline.py`, `file_utils.py`): `FileNotFoundError` in `_ocr_pdf_first_page` is now re-raised instead of swallowed, and `classify_file` checks file existence upfront — OneDrive TOCTOU failures now surface as `FileNotFoundError` rather than a misleading "OCR failed for PDF" log entry

### Added

- **Comprehensive subject mappings for book classification**: Expanded THEMA code mappings to cover all major subject areas
  - Added humanities (philosophy, ethics, religion, aesthetics, logic, metaphysics)
  - Added social sciences (sociology, anthropology, politics, education, psychology)
  - Added arts & literature (visual arts, music, cinema, theatre, poetry, fiction, creative writing)
  - Added history & geography (ancient, medieval, modern history, biographies)
  - 100+ new subject keywords with accurate THEMA classification codes
  - Enables proper classification of educational materials across all disciplines

### Fixed

- **Book detection threshold architecture**: THEMA subject detection now contributes to book scoring
  - THEMA detection moved BEFORE threshold check instead of after
  - Subject identification now adds +0.4 to detection score as a strong signal
  - Fixes issue where low-scoring educational PDFs were rejected before subject analysis
  - Great Courses PDFs now correctly classified by subject matter (Philosophy, Political Science, etc.)
- **Default book classification**: Changed fallback from Computing to Reference/Interdisciplinary
  - Previously all unmatched books defaulted to "U" (Informatique)
  - Now defaults to "G" (Reference/General) for better semantic accuracy
- **Electronics & engineering keywords**: Corrected THEMA codes for electronics subjects
  - Changed from TH (Energy Engineering) to TJ/TJF (Electronic Engineering)
  - Added specific terms: microprocessor, microcontroller, digital logic, circuits, embedded systems
  - Prevents electronics books from misclassifying as philosophy/logic

### Added

- **Smart renaming for CHM and MOBI files**: Files are now renamed using their document title during classification
  - BookDetector now processes `.pdf`, `.chm`, and `.mobi` files
  - **CHM files**: Extracts title from HTML content using 7z extraction
  - **MOBI files**: Extracts title from metadata using PyMuPDF
  - ISBN lookup works for CHM and MOBI files just like PDFs
  - CHM files get base confidence of 0.8 as documentation/help files
  - MOBI files get base confidence of 0.8 as ebook files
  - Extracted titles are sanitized and used as `suggested_name` for file renaming
- **Parallel processing in bookstore command**: 8x faster processing with `--workers` option
  - Default: 8 parallel workers for ISBN extraction and API lookups
  - Thread-safe ISBN deduplication with proper locking
  - Use `-w 1` for sequential processing (old behavior)
- **CHM and EPUB support in bookstore command**: Extended book detection beyond PDFs
  - New `chm_metadata.py`: Extracts ISBNs from Microsoft Compiled HTML Help files using 7z
  - New `epub_metadata.py`: Extracts ISBNs from EPUB files via OPF metadata
  - Bookstore now scans `.pdf`, `.chm`, and `.epub` files automatically
  - Renamed files preserve original extension (e.g., `Author - Title (Year).epub`)
- **Auto-correct date in filenames**: New `auto_correct_date` option for routing rules
  - Detects when filename date (e.g., `201304-Expense.pdf`) differs from content date
  - Automatically suggests corrected filename in ISO format (e.g., `2014-04-Expense.pdf`)
  - Preserves month from filename when content only has year
  - Works with `date_source: "content"` rules
- **YYYYMM filename pattern support**: Added support for 6-digit date format in filenames
  - Patterns like `201304-` now correctly extract as April 2013
  - Previously only YYYYMMDD (8-digit) was supported

### Fixed

- **ISBN lookup now prefers Open Library**: Changed service order from `goob→openl→wiki` to `openl→wiki→goob`
  - Google Books API often returns wrong metadata for valid ISBNs
  - Open Library has more reliable book data
  - Significantly improves coherence matching accuracy
- **Space-separated ISBNs now detected**: Fixed ISBN extraction to catch formats like `ISBN 0 7506 67362`
  - Now uses regex patterns FIRST to find candidates, then validates with isbnlib
  - Previously `isbnlib.get_isbnlike()` missed space-separated formats
  - Significantly improves book detection rate for older publications
- **Rename conflict handling in bookstore**: Files are now renamed with counter suffix when target exists
  - Previously silent skip when `Author - Title (Year).pdf` already existed
  - Now uses `Author - Title (Year)_1.pdf`, `_2.pdf`, etc.
- **Rejection stats in bookstore summary**: Shows breakdown of why books were not detected
  - `No ISBN in file`: File had no ISBN in first 20 pages
  - `API lookup failed`: Google Books API returned no results
  - `Title mismatch`: ISBN lookup title didn't match filename
- **Duplicate books in bookstore command**: Added ISBN-based and content-based deduplication
  - Tracks processed ISBNs to skip duplicate books
  - Uses `FileMover` for content-based duplicate detection
  - Shows summary of skipped duplicates
- **ISBN false positives in bookstore command**: Consolidated ISBN validation logic (DRY)
  - Created shared `find_matching_book_info()` function in `isbn_lookup.py`
  - Both `BookDetector` and `bookstore` command now use the same ISBN coherence validation
  - Prevents false positives from promotional ISBNs embedded in PDFs (e.g., all books getting ISBN 9789786468600)
  - Iterates through all ISBNs found to match filename with lookup title
- **Expense reports routing to wrong year**: Changed `notes_frais` rule from `date_source: "file_modified"` to `date_source: "content"`
  - Files now route based on document content date, not filesystem date
  - Prevents old documents from routing to current year when copied/touched
- **Silenced noisy library logs**: Reduced log spam from third-party libraries
  - **isbnlib**: ISBN lookup 404s no longer spam CRITICAL/WARNING (expected fallback behavior)
  - **pypdf**: "Ignoring wrong pointing object" warnings silenced (common in scanned PDFs)

### Changed

- **ISBN lookup logic refactored (DRY)**: Single source of truth for ISBN validation
  - Moved `is_title_coherent_with_filename()` to `isbn_lookup.py`
  - New `find_matching_book_info()` encapsulates iteration and validation
  - Removed duplicate logic from `book_detector.py` and `bookstore_cmd.py`
- **Pipeline reorder: book_detector before rules_engine**: Books with ISBN now get proper Thema classification
  - Book Detector runs FIRST (96-100% confidence) before Rules Engine (95%)
  - Fixes misclassification of books like "Microsoft Press Exam Ref..." being routed to exam materials
  - Books are now classified via ISBN/metadata/Thema before pattern-based rules can capture them

### Added

- **Technical publisher books rule**: Routes known publishers to books before `*Exam*` pattern
  - Microsoft Press, O'Reilly, Apress, Packt, Manning, Pragmatic, No Starch, Wiley, Pearson, etc.
  - Routes to `3_Resources/livres/informatique` as fallback for books without ISBN
- **Citrix/NetScaler documentation rule**: Prevents NetScaler docs from Microsoft certification routing
  - Patterns: NetScaler, Citrix, XenServer, XenApp, XenDesktop, ADC
  - Routes to `3_Resources/docs/Citrix/{YYYY}`
- **Veeam documentation rule**: Prevents Veeam docs from being classified as insurance/pension
  - Patterns: Veeam, "V 12...", Log Analyzer, Backup Replication, VBR Guide
  - Routes to `3_Resources/docs/Veeam/{YYYY}`
- **Case studies rule**: Marketing/technical case studies no longer route to invoices
  - Patterns: CaseStudy, CustomerStory, SuccessStory
  - Routes to `3_Resources/docs/case-studies`
- **Fujitsu Storage documentation rule**: Prevents Fujitsu storage docs from AVS/pension routing
  - Patterns: Fujitsu Storage, Eternus, Virtual Appliance, Primergy
  - Routes to `3_Resources/IT/Storage/{YYYY}`

### Fixed

- **HP-Technical pattern capturing donation files**: Fixed overly broad regex `[0-9A-Z]{4}-*` that matched year-prefixed files
  - Changed pattern from `[0-9A-Z][0-9A-Z][0-9A-Z][0-9]-*` to `[A-Z][0-9A-Z][0-9A-Z][0-9A-Z]-*`
  - Now requires first character to be a letter (HP product codes start with letters, not years)
  - Prevents `2016-amnesty.pdf`, `2017-unicef.pdf` etc. from routing to `3_Resources/docs/HP-Technical/`
  - Donation files now correctly route to `4_Archives/10y_dons/{issuer}/{year}` via domain KB
- **MLX token limit crash in TechnologyExtractor**: Reduced content limit from 2000 to 400 characters
  - Prevents `IndexError: list index out of range` when text tokenizes to >512 tokens
  - Some texts tokenize poorly (e.g., 700 chars → 800+ tokens), causing model failure
  - 400 chars safely stays under the MLX model's 512 token limit
- **Remaining `%s` logging in pipeline.py**: Converted 2 remaining printf-style log calls to loguru `{}` format
- **EMC document misclassification**: Added comprehensive Dell EMC product portfolio to TechnologyExtractor
  - ~45 Dell EMC products in TECHNOLOGY_DESCRIPTIONS with semantic descriptions
  - ~80 keyword mappings for filename-based detection
  - Categories: Storage (PowerMax, PowerStore, PowerScale), Data Protection (PowerProtect, DataDomain), Legacy (VMAX, VNX, Isilon), HCI (VxRail, VxRack), Networking (Connectrix, SONiC)
  - Added OpenStack as distinct from OpenShift (previously conflated)
  - Prevents XtremIO→Oracle, OpenStack→OpenShift, EMC World→MariaDB misroutes

### Changed

- **Unified logging with loguru**: Replaced standard Python logging with loguru across all 32 source files
  - Console output: Colored, human-readable format
  - File output: JSON Lines to `{PARA_ROOT}/logs/operations.log`
  - Automatic rotation, retention, and compression
  - Thread-safe async writes with `enqueue=True`
- **Removed CleanupLogger**: Custom audit logger replaced by loguru's built-in file logging
- **OCR logs moved to DEBUG level**: Reduced console noise by changing verbose OCR messages to DEBUG
  - "PDF appears scanned, trying OCR" now only shows with `--verbose`
  - "OCR extracted N chars from PDF" now only shows with `--verbose`
- **Streaming rescan command**: `rescan` now processes files as discovered instead of loading all into memory
  - Generator-based file discovery for lower memory usage
  - Reuses single TaxonomyClassifier instance (faster classification)
  - Shows progress every 100 files with live move count
  - Better for large archives (10k+ files)
- **Enhanced rescan logging**: Much more informative output showing exactly what's happening
  - Each moved file shows source filename and full destination path
  - Summary includes category breakdown (moves per category)
  - Errors section shows first 5 failures with filenames
  - Dry-run mode clearly indicates simulated moves

### Added

- **Intelligent PDF OCR triggering**: OCR now evaluates text quality, not just length
  - New `_calculate_text_quality()` function scores extracted text (0.0 - 1.0)
  - Evaluates: alphabetic ratio, word quality, spacing, word length, PDF metadata patterns
  - OCR triggered if quality < 0.3 (garbage/metadata) or length < 50 chars
  - Compares pypdf vs OCR quality and uses the better result
  - Fixes scanned PDFs that pypdf extracts as metadata garbage (e.g., sword.pdf payslip → photos)
- **OCR-based pre-classification file renaming**: Automatically rename generic PDFs before classification
  - Detects generic filenames: `scan_001.pdf`, `IMG_1234.pdf`, `document.pdf`, timestamps, UUIDs, etc.
  - Extracts metadata from OCR text: date (ISO, European, French/English text formats), issuer, document type
  - Renames to descriptive format: `{YYYY-MM-DD}_{issuer}_{type}.pdf`
  - Helps rules engine match on descriptive names instead of generic scanner output
  - New modules: `filename_detector.py`, `ocr_metadata.py`, `smart_renamer.py`
  - Configuration: `ocr_rename.enabled`, `ocr_rename.min_confidence`, `ocr_rename.dry_run`
  - Default: enabled with 30% minimum confidence threshold
- **Configurable logging settings**: New `LoggingConfig` in config.py with customizable options
  - `level`: Log level for file output (DEBUG, INFO, WARNING, ERROR)
  - `rotation`: Size-based rotation (e.g., "10 MB", "100 MB")
  - `retention`: How long to keep logs (e.g., "30 days", "1 year")
  - `compression`: Format for rotated logs (gz, bz2, xz, zip)
  - Configure via YAML (`logging:` section) or env vars (`PARA_FILES_LOG_*`)
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
- **Retention-based folder prefixes**: TaxonomyClassifier now adds retention policy prefixes to folder names
  - `10y_` for 10_years retention
  - `5y_` for 5_years retention
  - `ctr_` for contract_duration
  - `2y_` for warranty_2_years
  - `ret_` for retirement
  - Permanent folders have no prefix (go to 3_Resources)
  - Example: `4_Archives/fiscalite/{year}` → `4_Archives/10y_fiscalite/{year}`
  - Retention info now included in `extracted_params` of ClassificationResult
- **Updated documents.json with retention prefixes**: All 48 document types now have `para_pattern` with retention prefix
  - Automated update script at `scripts/update_documents_json.py`
  - Enables visual identification of retention requirements in folder structure
- **Retention rules for additional folders**: Added retention configuration for:
  - `agriculture` (contract duration)
  - `assurances` (contract duration)
  - `comptabilite` (10 years)
  - `correspondance` (permanent → 3_Resources)
- **Rewritten `migrate` command**: FAST folder-based migration with PARA relocation
  - Renames folders to add retention prefixes (e.g., `fiscalite` → `10y_fiscalite`)
  - Moves permanent folders to `3_Resources/` (no prefix needed)
  - Moves time-limited folders to `4_Archives/` with retention prefix
  - O(folders) instead of O(files) - completes in seconds, not hours
  - **Executes by default** - use `--dry-run` for preview mode
  - Filter by category (`--category fiscalite`)
  - JSON output for scripting (`--json`)
  - **New: `--merge` flag** for merging folders when destination already exists
    - Moves unique files to destination
    - Removes duplicate files (identical content)
    - Renames conflicting files with `_from_archives` suffix
  - Example: `uv run para-files migrate /path/to/PARA`
- **New `rescan` command**: Re-classify files already in PARA archives (SLOW)
  - Per-file classification for fixing misclassified documents
  - Use when taxonomy changed or files need reclassification
  - **Executes by default** - use `--dry-run` for preview mode
  - Same options: `--category`, `--json`, `--cleanup`
  - Example: `uv run para-files rescan /path/to/PARA`

### Fixed

- **HEIC photo misrouting during rescan (Part 2)**: Photos were still misrouting to certifications folder
  - Root cause: `source: "0_Inbox"` constraint on photos/videos/screenshots rules blocked matching during rescan
  - Fix 1: Removed `source:` constraint from `photos`, `videos`, `screenshots` rules (extension-based rules don't need source restriction)
  - Fix 2: Added `MEDIA_ONLY_EXTENSIONS` in file_utils.py to skip OCR for pure media files (defense-in-depth)
  - OCR on photos could extract misleading text (e.g., photo of certificate → "certification" keyword → misroute)
- **Comprehensive routing rules validation**: Reviewed all 216 routing rules for consistency
  - Removed duplicate `amiante_docs` rule (consolidated into `amiante_documents`)
  - Removed `*VTSP*` pattern from `vmware_docs` (VTSP is a certification, not documentation)
  - Removed overlapping patterns: `*[Bb]ateau*` from `loisirs_voile`, `*[Cc]over*[Ll]etter*` from `lettres_accompagnement`
  - Fixed `amiante_documents` destination to include `{YYYY}` for date-based organization
  - Added clarifying comments throughout YAML for maintainability
- **Photo/image routing during rescan**: Photos and images were being misrouted to fiscal folders
  - Root cause 1: `rescan` command bypassed RulesEngineClassifier by using TaxonomyClassifier directly
  - Root cause 2: `source:` constraint in routing rules was never enforced
  - Fix 1: `rescan` now uses full ClassificationPipeline with all classifiers in priority order
  - Fix 2: RulesEngineClassifier now validates `source:` constraint (e.g., files must be in `0_Inbox`)
  - Added `CAT_10_MEDIA` category in documents.json for photos, videos, and screenshots
  - Removed duplicate routing rules in personal_file_tree.yaml (vmware_documentation, credit_agricole, etc.)
- **CI/CD ruff compliance**: Added `# noqa: BLE001` comments to intentional broad exception catches
  - Defensive error handling for external tools (OCR, pandoc, exiftool, MLX)
  - Prevents pipeline crashes from unexpected external tool failures

### Changed

- **CLI commands execute by default**: All file-operation commands now execute immediately
  - Use `--dry-run` flag to preview changes without executing
  - Affected commands: `migrate`, `rescan`, `clean`, `dedupe`, `move`, `init`
  - More intuitive UX: commands do what they say by default
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

### Changed

- **documents.json patterns simplified**: Removed `_perm` suffix from `3_Resources` patterns
  - Resources folder = permanent by definition, no suffix needed
  - Example: `3_Resources/administratif_perm/identite` → `3_Resources/administratif/identite`
  - Archives still use retention suffixes: `_10y`, `_5y`, `_ret`, `_ctr`

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
