# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
- Comprehensive test suite (235+ tests)
