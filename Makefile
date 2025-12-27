# Makefile for para-files
# Automates build, test, and quality checks

.PHONY: all check-deps setup lint format typecheck test clean help

# Default target
all: check-deps setup lint format typecheck test

# Check required dependencies
check-deps:
	@echo "Checking dependencies..."
	@command -v uv >/dev/null 2>&1 || { echo "Error: uv is not installed. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	@echo "All dependencies found."

# Setup environment and install packages
setup: check-deps
	@echo "Setting up environment..."
	uv sync --all-extras
	@echo "Environment ready."

# Run linter
lint:
	@echo "Running linter..."
	uv run ruff check src/ tests/

# Run formatter
format:
	@echo "Running formatter..."
	uv run ruff format src/ tests/

# Run type checker
typecheck:
	@echo "Running type checker..."
	uv run mypy src/

# Run tests
test:
	@echo "Running tests..."
	uv run pytest

# Run tests with coverage
test-cov:
	@echo "Running tests with coverage..."
	uv run pytest --cov=src/para_files --cov-report=term-missing

# Run all quality checks (no tests)
quality: lint typecheck

# Fix linting issues automatically
fix:
	@echo "Fixing linting issues..."
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf __pycache__
	rm -rf src/**/__pycache__
	rm -rf tests/__pycache__
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf dist
	rm -rf *.egg-info
	@echo "Clean complete."

# Install pre-commit hooks
hooks:
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "Hooks installed."

# Run pre-commit on all files
pre-commit:
	@echo "Running pre-commit checks..."
	pre-commit run --all-files

# Build distribution
build: quality test
	@echo "Building distribution..."
	uv build

# Show help
help:
	@echo "para-files Makefile"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  all        Run full pipeline: deps, setup, lint, format, typecheck, test"
	@echo "  check-deps Check that uv is installed"
	@echo "  setup      Install dependencies with uv sync"
	@echo "  lint       Run ruff linter"
	@echo "  format     Run ruff formatter"
	@echo "  typecheck  Run mypy type checker"
	@echo "  test       Run pytest"
	@echo "  test-cov   Run pytest with coverage report"
	@echo "  quality    Run lint and typecheck (no tests)"
	@echo "  fix        Auto-fix linting issues and format code"
	@echo "  clean      Remove build artifacts and caches"
	@echo "  hooks      Install pre-commit hooks"
	@echo "  pre-commit Run pre-commit on all files"
	@echo "  build      Build distribution package"
	@echo "  help       Show this help message"
