# Suggested Commands for para-files Development

## Package Management (uv)

```bash
# Install all dependencies including dev tools
uv sync --all-extras

# Add a new dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>
```

## Running the Application

```bash
# Run CLI
uv run para-files

# CLI Commands
uv run para-files classify <files...>           # Classify files
uv run para-files move <files...>               # Move files to PARA destinations
uv run para-files scan <dir>                    # Preview classifications
uv run para-files tree                          # Display reference tree
uv run para-files routes                        # List available routes
uv run para-files issuers                       # List known issuers
uv run para-files config                        # Show configuration
```

## Quality Checks

```bash
# Lint (check for issues)
uv run ruff check src/ tests/

# Lint and auto-fix
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/

# Type checking
uv run mypy src/

# Run ALL quality checks
uv run ruff check src/ tests/ && uv run ruff format src/ tests/ && uv run mypy src/
```

## Testing

```bash
# Run all tests
uv run pytest

# Verbose output
uv run pytest -v

# Single test file
uv run pytest tests/test_main.py

# Run tests matching pattern
uv run pytest -k "test_version"

# With coverage report
uv run pytest --cov

# Skip slow tests
uv run pytest -m "not slow"
```

## Pre-commit Hooks

```bash
# Install hooks (first time setup)
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

## Git Commands

```bash
# Standard git commands work as expected on Darwin/macOS
git status
git diff
git add .
git commit -m "message"
git push
git pull
git log --oneline -10
```

## System Utilities (Darwin/macOS)

```bash
# List files
ls -la

# Find files
find . -name "*.py"

# Search in files
grep -r "pattern" src/

# Current directory
pwd

# Change directory
cd path/to/dir
```

## Environment Configuration

```bash
# Copy example env
cp .env.example .env

# Edit environment
# Key variables:
# PARA_FILES_PARA_ROOT - Root directory for PARA structure
# PARA_FILES_MLX__MODEL_NAME - MLX model name
# PARA_FILES_LLM__ENABLED - Enable LLM fallback
```
