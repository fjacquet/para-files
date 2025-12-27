# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
- New utilities in `para_files.utils`:
  - `cleanup.py`: Junk file detection and deletion
  - `nfo_parser.py`: NFO file parsing with encoding fallback
  - `cleanup_log.py`: Audit logging for cleanup operations
- **Geolocation for photos and videos**: Photos and videos with GPS EXIF data now include location in the destination path (e.g., `4_Archives/photos/2024/Geneva/06/15/IMG_1234.jpg`)
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
