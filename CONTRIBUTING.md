# Contributing to para-files

Thank you for your interest in contributing to para-files!

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Development Setup

```bash
# Clone the repository
git clone https://github.com/fjacquet/para-files.git
cd para-files

# Install dependencies (includes dev tools)
uv sync --all-extras

# Install pre-commit hooks
pre-commit install
```

## Code Quality

We use strict quality checks. Run all checks before submitting:

```bash
# Linting
uv run ruff check src/ tests/

# Formatting
uv run ruff format src/ tests/

# Type checking
uv run mypy src/

# Tests
uv run pytest -v

# All at once
uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/ && uv run pytest
```

## Code Style

- Python 3.12+ features welcomed
- Strict mypy type checking (`py.typed` package)
- Line length: 100 characters
- Use `from __future__ import annotations` in all modules
- Docstrings: Google style

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Ensure all checks pass
5. Commit with a descriptive message
6. Push to your fork
7. Open a Pull Request

## Commit Messages

Follow conventional commits:

```
feat: add new classification signal
fix: correct path resolution for archives
docs: update installation instructions
test: add tests for semantic router
refactor: simplify pipeline initialization
```

## Testing

- Write tests for new functionality
- Maintain or improve code coverage (target: 80%)
- Use pytest fixtures for common setup
- Mark slow tests with `@pytest.mark.slow`

## Documentation Maintenance

Keep documentation up-to-date with every change:

### CHANGELOG.md

Update `CHANGELOG.md` for every PR:

- **Added**: New features or commands
- **Changed**: Modifications to existing behavior
- **Fixed**: Bug fixes
- **Removed**: Removed features
- **Security**: Security-related changes

Add entries under `## [Unreleased]` section.

### README.md

Update when:

- Adding new CLI commands
- Changing configuration options
- Modifying installation steps

### docs/ (GitHub Pages)

Update `docs/architecture.md` when:

- Adding new classifiers or signals
- Changing the pipeline flow
- Modifying major components

### Code Documentation

- Add docstrings to all public functions/classes
- Use Google-style docstrings
- Include type hints in signatures

## Architecture Guidelines

When adding new classifiers:

1. Inherit from `BaseClassifier`
2. Implement `classify()` method
3. Define `source`, `name`, and `default_confidence` properties
4. Add to pipeline in `ClassificationPipeline.__init__`
5. Write comprehensive tests

## Questions?

Open an issue or discussion on GitHub.
