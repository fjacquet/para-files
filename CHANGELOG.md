# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- GitHub Actions CI workflow with macOS-14 runner (Apple Silicon)
- GitHub Pages documentation site with Jekyll
- Dependabot for automated dependency updates
- MIT LICENSE file
- CONTRIBUTING.md with development guidelines
- Architecture documentation with Mermaid diagrams

### Changed

- Moved `personal_file_tree.yaml` to `config/` folder
- Centralized configuration defaults in `config.py`
- LLM fallback now uses configurable content preview chars

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
