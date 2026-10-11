# para-files

[![CI](https://github.com/fjacquet/para-files/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/fjacquet/para-files/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)

para-files files documents into a [PARA](https://fortelabs.com/blog/para/) tree (Projects, Areas, Resources, Archives):

- **Pinned rules and books with a verified ISBN** file themselves: the green files move on `sort --apply`. Books go to the library, placed by ISBN and its Thema subject.
- **Everything else** is read by the model (when an OpenRouter key is set), which suggests a folder. Yellow files wait for your confirmation, red files stay where they are. Unpinned rules and issuer matches are only hints to the model.

Nothing moves until you ask. Every run is journaled, and `undo` reverses it step by step.

## Quick Start

```bash
# 1. Install
git clone https://github.com/fjacquet/para-files.git
cd para-files
uv sync --all-extras

# 2. Point it at your PARA root (the folder that holds 0_Inbox)
mkdir -p ~/.config/para-files
echo 'PARA_FILES_PARA_ROOT=~/PARA' > ~/.config/para-files/.env

# 3. Describe your folders in ~/.config/para-files/tree.yaml (plus rules.yaml and issuers.yaml), then check them
uv run para-files tree --validate

# 4. Create the missing folders, preview, then move
uv run para-files init --apply
uv run para-files sort
uv run para-files sort --apply
```

**→ [Getting started](docs/getting-started.md)** walks through a minimal configuration.

## System Requirements

- **Python 3.12+** and the **[uv](https://docs.astral.sh/uv/)** package manager
- **macOS (Apple Silicon)** only for the OCR features; everything else is cross-platform
- **No local model server.** The cloud model is optional: set `OPENROUTER_API_KEY` to allow it. Requests ask OpenRouter for zero data retention, and secret-looking files are never sent

## Essential Commands

```bash
uv run para-files sort                      # Preview where the inbox files would go
uv run para-files sort --apply              # Move the green ones
uv run para-files sort --apply --review     # And confirm or correct the yellow ones
uv run para-files explain file.pdf          # Why a file goes where it goes
uv run para-files undo                      # Reverse the last run
```

**→ [Full CLI Reference](docs/cli/overview.md)**

## Documentation

- **[Getting started](docs/getting-started.md)**: install, configure, sort, undo
- **[Configuration](docs/configuration.md)**: settings, `tree.yaml`, `rules.yaml`, `issuers.yaml`, validation
- **[Architecture](docs/architecture.md)**: the cascade, bands, secrets guard, journal, cache
- **[Troubleshooting](docs/troubleshooting.md)**: red files, nothing green, undo, the model, secrets
- **[Documentation index](docs/index.md)**: every page

## All CLI Commands

| Command | Description |
|---------|-------------|
| `sort` | Classify files (default: the inbox), preview, move with `--apply` |
| `explain` | Why one file goes where it goes, and what to edit |
| `undo` | Reverse a run from its journal |
| `clean` | Junk files, empty folders, duplicates to `.trash` |
| `tree` | Leaves, settings, calibration progress, config warnings |
| `init` | Create the inbox and the leaf folders |

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
