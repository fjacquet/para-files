# para-files

[![CI](https://github.com/fjacquet/para-files/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/fjacquet/para-files/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![Platform: macOS](https://img.shields.io/badge/platform-macOS%20(Apple%20Silicon)-lightgrey.svg)](https://www.apple.com/macos/)

**macOS-only (Apple Silicon)** intelligent file classification system using MLX-powered semantic routing.

Implements the **PARA method** (Projects, Areas, Resources, Archives) with a deterministic **6-signal classification pipeline**.

## Quick Start

```bash
# 1. Install
git clone https://github.com/fjacquet/para-files.git
cd para-files
uv sync --all-extras

# 2. Configure
export PARA_FILES_PARA_ROOT=~/Documents/PARA

# 3. Classify files
uv run para-files classify document.pdf
uv run para-files move *.pdf --dry-run
```

**→ [Complete Getting Started Guide](docs/getting-started/installation.md)**

## System Requirements

- **macOS** with Apple Silicon (M1/M2/M3/M4)
- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** package manager

## Key Features

- **6-Signal Pipeline** - Cascading classification for high accuracy
- **MLX Embeddings** - Fast semantic matching on Apple Neural Engine
- **PARA Method** - Organize into Projects, Areas, Resources, Archives
- **No Setup** - Works out of the box with reasonable defaults
- **Extensible** - Add custom routes, issuers, and utterances via YAML
- **Interactive Learning** - Improve accuracy by correcting classifications

## Essential Commands

```bash
uv run para-files classify file.pdf         # Determine category
uv run para-files move *.pdf --dry-run      # Preview move
uv run para-files move *.pdf                # Move files
uv run para-files learn wrong_file.pdf      # Learn from mistakes
uv run para-files add-issuer "Bank" -c cat  # Register company
uv run para-files add-utterance route "kw"  # Add keywords
```

**→ [Full CLI Reference](docs/cli/overview.md)**

## Documentation

Quick links to common tasks:

- **Getting Started** - [Installation](docs/getting-started/installation.md) • [Quick Setup](docs/getting-started/quick-setup.md) • [First File](docs/getting-started/first-file.md)
- **How-To Guides** - [Set Up PARA](docs/tasks/set-up-para-folder.md) • [Classify](docs/tasks/classify-single-file.md) • [Move](docs/tasks/move-files.md) • [Issuers](docs/tasks/manage-issuers.md) • [Learn](docs/tasks/learn-from-files.md)
- **Configuration** - [Overview](docs/configuration/overview.md) • [Env Variables](docs/configuration/env-file.md) • [YAML Config](docs/configuration/yaml-config.md)
- **Understanding** - [Architecture](docs/architecture/overview.md) • [Signals](docs/architecture/overview.md) • [Semantic Matching](docs/architecture/signal-4-semantic.md)
- **Troubleshooting** - [Inbox Issues](docs/troubleshooting/files-going-to-inbox.md) • [Low Confidence](docs/troubleshooting/confidence-too-low.md) • [Slow Model](docs/troubleshooting/model-download-slow.md)

**→ [Complete Documentation Index](docs/index.md)**

## All CLI Commands

| Command | Description |
|---------|-------------|
| `classify` | Determine file category |
| `move` | Move files to PARA folders |
| `scan` | Preview classifications for directory |
| `learn` | Interactive improvement |
| `add-issuer` | Register company/bank |
| `add-utterance` | Add matching keywords |
| `tree`, `routes`, `issuers` | View configuration |
| `config` | Show settings |
| `init` | Create folder structure |
| `clean` | Remove junk files |

**→ [CLI Reference](docs/cli/overview.md)**

## Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Run quality checks
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run mypy src/
uv run pytest
```

See [CLAUDE.md](CLAUDE.md) for development guidance and [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

MIT
