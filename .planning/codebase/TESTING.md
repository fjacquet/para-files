# Testing Patterns

**Analysis Date:** 2025-03-22

## Test Framework

**Runner:**

- **pytest** 8.3.0+
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`
- Python path: `src` (allows imports like `from para_files.config import ...`)

**Assertion Library:**

- Standard pytest assertions (no additional library needed)
- Example: `assert result is not None`, `assert classifier.name == "rules_engine"`

**Run Commands:**

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run single test file
uv run pytest tests/test_main.py

# Run tests matching pattern
uv run pytest -k "test_version"

# Run with coverage report
uv run pytest --cov

# Run with coverage and missing lines report
uv run pytest --cov --cov-report=term-missing
```

**Coverage:**

- Fail-under threshold: **79%** (enforced via `tool.coverage.report.fail_under = 79`)
- Branch coverage: **enabled** (`tool.coverage.run.branch = true`)
- Source: `src/para_files` only (tests excluded)

## Test File Organization

**Location:**

- Co-located: Test files in `tests/` directory parallel to `src/para_files/`
- Pattern: For source module `src/para_files/X/y.py`, test file is `tests/test_y.py`

**Naming:**

- `test_*.py` prefix for test modules
- Example files: `test_rules_engine.py`, `test_book_detector.py`, `test_filename_sanitizer.py`

**Structure:**

```
tests/
├── conftest.py              # Shared fixtures
├── fixtures/                # Test data files
│   └── test_reference_tree.yaml
├── test_*.py               # Test modules (one per source module)
└── __init__.py            # Empty marker
```

## Test Structure

**Suite Organization:**

```python
"""Tests for rules engine classifier."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from para_files.classifiers.rules_engine import RulesEngineClassifier
from para_files.types import ClassificationSource, FileMetadata, RoutingRule


def make_metadata(**kwargs: object) -> FileMetadata:
    """Helper to create FileMetadata with required defaults."""
    defaults: dict[str, object] = {
        "path": Path("/test/file.txt"),
        "filename": "file.txt",
        "extension": ".txt",
        "size_bytes": 1024,
    }
    defaults.update(kwargs)
    return FileMetadata(**defaults)


class TestRulesEngineClassifierInit:
    """Test RulesEngineClassifier initialization."""

    def test_init_with_empty_rules(self) -> None:
        """Test initialization with empty rules dict."""
        classifier = RulesEngineClassifier({})
        assert classifier._rules == {}

    def test_init_with_rules(self) -> None:
        """Test initialization with routing rules."""
        rules = {"photos": RoutingRule(...)}
        classifier = RulesEngineClassifier(rules)
        assert "photos" in classifier._rules
```

**Patterns:**

- One test class per concept/behavior (e.g., `TestRulesEngineClassifierInit`, `TestClassify`)
- Test method names start with `test_` and describe what is tested
- Docstrings required on all test classes and methods
- Type annotations required for test parameters
- Return type: `-> None` for all test functions

## Mocking

**Framework:**

- `unittest.mock` (standard library)
- Import: `from unittest.mock import MagicMock, patch`

**Patterns:**

```python
# Mock a class method
@patch("para_files.encoders.ollama_encoder.litellm")
def test_encode_calls_litellm(self, mock_litellm: MagicMock):
    """Test that encoding calls litellm.embedding()."""
    mock_response = MagicMock()
    mock_response.data = [{"embedding": [0.1] * 768}]
    mock_litellm.embedding.return_value = mock_response

    encoder = OllamaEncoder()
    result = encoder(["hello world"])

    mock_litellm.embedding.assert_called_once()
    assert len(result) == 1
```

**What to Mock:**

- External API calls (litellm, isbnlib, geopy)
- File I/O operations (when testing logic, not actual filesystem)
- Network calls
- Expensive operations (ISBN lookup, OCR, embedding generation)

**What NOT to Mock:**

- Core business logic (classifiers, routing, pattern matching)
- Data validation (use real Pydantic models)
- Local filesystem operations in integration tests
- Configuration loading (test with real config files)

**MagicMock Usage:**

- For complex return values: `mock.return_value = MagicMock(...)`
- For call assertions: `mock.assert_called_once()`, `mock.assert_called_with(...)`
- For side effects: `mock.side_effect = [value1, value2]` for sequential returns

## Fixtures and Factories

**Test Data:**

Helper functions (not pytest fixtures) for creating test objects:

```python
def make_metadata(**kwargs: object) -> FileMetadata:
    """Helper to create FileMetadata with required defaults."""
    defaults: dict[str, object] = {
        "path": Path("/test/file.txt"),
        "filename": "file.txt",
        "extension": ".txt",
        "size_bytes": 1024,
    }
    defaults.update(kwargs)
    return FileMetadata(**defaults)

# Usage in tests:
metadata = make_metadata(
    path=Path("/test/image.jpg"),
    filename="image.jpg",
    extension=".jpg",
)
```

**Pytest Fixtures:**

Shared fixtures in `tests/conftest.py`:

```python
@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent

@pytest.fixture
def fixtures_dir() -> Path:
    """Return the test fixtures directory."""
    return Path(__file__).parent / "fixtures"
```

**Location:**

- Shared fixtures: `tests/conftest.py`
- Test data files: `tests/fixtures/` directory
- Example: `tests/fixtures/test_reference_tree.yaml`

**Naming:**

- Fixture names: lowercase with underscores (e.g., `project_root`, `fixtures_dir`)
- Fixture functions: use `@pytest.fixture` decorator
- Helper factory functions: descriptive names without decorator (e.g., `make_metadata()`)

## Coverage

**Requirements:**

- Target: **79% branch coverage** (fail-under threshold)
- Enforcement: CI/pre-commit hooks (if configured)

**View Coverage:**

```bash
# Generate and display coverage report
uv run pytest --cov --cov-report=term-missing

# Generate HTML report
uv run pytest --cov --cov-report=html
# Open htmlcov/index.html in browser
```

**Coverage Configuration:**

- Source: `src/para_files` (tests excluded)
- Branch coverage: enabled (tracks both true/false paths)
- Parallel: enabled (safe for running tests in parallel)
- Exclude from coverage:
  - `def __repr__` (debug output)
  - `raise AssertionError` (should never happen in production)
  - `raise NotImplementedError` (abstract methods)
  - `if __name__ == .__main__.:` (script entry points)
  - `if TYPE_CHECKING:` (type-only blocks)
  - `@abstractmethod` (abstract methods)

## Test Types

**Unit Tests:**

- Scope: Single function or method in isolation
- Mocking: Mock external dependencies (APIs, file I/O, expensive operations)
- Examples: `test_sanitize_filename()`, `test_rules_engine_classifier_init()`, `test_book_structure_score()`
- Location: Same file as functional tests (not separated)

**Integration Tests:**

- Scope: Multiple components working together
- Mocking: Minimal; test real behavior
- Marked with: `@pytest.mark.integration` (defined in `pyproject.toml`)
- Examples: Classification pipeline with multiple classifiers, file moving with conflict resolution
- Run: `pytest -m integration` to run only integration tests
- Run: `pytest -m "not integration"` to skip integration tests

**E2E Tests:**

- Status: **Not used** in this codebase
- Alternative: Integration tests cover end-to-end classification workflows

## Markers

**Available Markers:**

- `slow`: Marks tests as slow (long-running or expensive operations)
  - Usage: `@pytest.mark.slow`
  - Run: `pytest -m "not slow"` to skip slow tests
- `integration`: Marks tests as integration tests (cross-component)
  - Usage: `@pytest.mark.integration`
  - Run: `pytest -m integration` to run only integration tests

**Configuration:**

- Defined in `pyproject.toml` under `[tool.pytest.ini_options].markers`
- Enforced: `--strict-markers` prevents typos

## Common Patterns

**Async Testing:**

- Framework: Standard pytest (no special async support needed)
- Library: `loguru` logger calls are not async
- Pattern: No async/await in tests currently

**Error Testing:**

```python
def test_nonexistent_file_with_exit_on_error_raises(self, tmp_path: Path) -> None:
    """Test that exit_on_error=True raises SystemExit for nonexistent file."""
    test_file = tmp_path / "nonexistent.txt"
    with pytest.raises(SystemExit) as exc_info:
        validate_file_exists(test_file, exit_on_error=True)
    assert exc_info.value.code == 1
```

**Parameterized Testing:**

- Not extensively used in codebase
- Could use `@pytest.mark.parametrize` for repetitive test cases
- Example (hypothetical):

  ```python
  @pytest.mark.parametrize("input,expected", [
      ("hello:world", "hello_world"),
      ("path/file", "path_file"),
  ])
  def test_sanitize(input: str, expected: str) -> None:
      assert sanitize_filename(input) == expected
  ```

**Temporary Filesystem:**

- Fixture: pytest's built-in `tmp_path` fixture
- Type: `Path` object pointing to temporary directory
- Cleanup: Automatic after test
- Example:

  ```python
  def test_existing_file_returns_true(self, tmp_path: Path) -> None:
      """Test that an existing file returns True."""
      test_file = tmp_path / "test.txt"
      test_file.write_text("content")
      assert validate_file_exists(test_file) is True
  ```

## Test Execution Configuration

**Pytest Options:**

- `-ra`: Show all summary info
- `-q`: Quiet mode
- `--strict-markers`: Fail on unknown markers
- `--strict-config`: Fail on configuration errors

**Filter Warnings:**

- Default: `error` (treat warnings as errors)
- Allowed (ignored):
  - `DeprecationWarning` (expected from old dependencies)

**Test Discovery:**

- Path: `tests/` directory
- Pattern: `test_*.py` files
- Python path: `src` (allows direct imports)

## Pre-commit Integration

**Testing in pre-commit:**

- Hook: Not auto-installed; must run manually or in CI
- Command: `uv run pytest`
- Coverage enforcement: Part of CI pipeline, not pre-commit hooks

---

*Testing analysis: 2025-03-22*
