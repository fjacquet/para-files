# Testing Patterns

**Analysis Date:** 2026-02-28

## Test Framework

**Runner:**
- pytest 8.3.0+ (configured in pyproject.toml)
- Config: `[tool.pytest.ini_options]` in `pyproject.toml`

**Assertion Library:**
- pytest built-in assertions (no external library needed)

**Run Commands:**
```bash
uv run pytest                      # Run all tests
uv run pytest -v                   # Verbose output (show each test)
uv run pytest -k "test_version"    # Run tests matching pattern
uv run pytest --cov                # With coverage report
uv run pytest tests/test_main.py   # Single test file
```

**Test discovery:**
- `testpaths = ["tests"]` in pyproject.toml
- Python path: `pythonpath = ["src"]` for imports
- Pattern: files named `test_*.py` or `*_test.py`

## Test File Organization

**Location:**
- Mirror structure: `tests/` parallel to `src/para_files/`
- Test file naming: `test_{module_name}.py` matches module file
- Example: `src/para_files/types.py` → `tests/test_types.py`

**Naming:**
- Test classes: `Test{FunctionName}` or `Test{ModuleName}`
- Test methods: `test_{behavior}_{condition}` or `test_{method}_{scenario}`
- Example: `test_isbn13_valid()`, `test_classify_match()`, `test_match_by_extension()`

**Structure:**
```
tests/
├── conftest.py                 # Shared fixtures
├── fixtures/
│   └── test_reference_tree.yaml # Test data
├── test_book_detector.py
├── test_classifiers.py
├── test_config.py
├── test_encoders.py
├── test_learner.py
├── test_main.py
├── test_mover.py
├── test_pdf_metadata.py
├── test_pipeline.py
└── test_types.py
```

**Total test count:**
- 41 test files with ~590 total tests
- Coverage target: 80% (enforced by `fail_under = 80` in coverage config)

## Test Structure

**Conftest setup (conftest.py):**
```python
from __future__ import annotations
from pathlib import Path
import pytest

@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent

@pytest.fixture
def fixtures_dir() -> Path:
    """Return the test fixtures directory."""
    return Path(__file__).parent / "fixtures"
```

**Class-based test organization:**
- Tests grouped into classes by functionality: `TestBaseClassifier`, `TestRulesEngineClassifier`, `TestExtractIsbn`
- One test class per major function or feature
- Each test method is independent and can run in any order

**Example test class structure (test_classifiers.py):**
```python
class TestBaseClassifier:
    """Tests for abstract BaseClassifier."""

    def test_cannot_instantiate_abstract(self):
        """Test that BaseClassifier cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseClassifier()  # type: ignore[abstract]

    def test_concrete_implementation(self):
        """Test concrete classifier works."""
        classifier = ConcreteClassifier()
        assert classifier.name == "test_classifier"

class TestRulesEngineClassifier:
    """Tests for RulesEngineClassifier (Signal 1)."""

    @pytest.fixture
    def photo_rules(self) -> dict[str, RoutingRule]:
        """Create sample photo routing rules."""
        return {
            "photos": RoutingRule(
                extensions=[".jpg", ".jpeg", ".png"],
                destination="4_Archives/photos/{YYYY}/{MM}",
            )
        }

    def test_match_by_extension(self, photo_rules: dict[str, RoutingRule]):
        """Test matching by file extension."""
        classifier = RulesEngineClassifier(photo_rules)
        metadata = FileMetadata(
            path=Path("/tmp/photo.jpg"),
            filename="photo.jpg",
            extension=".jpg",
            size_bytes=1024,
        )
        result = classifier.classify("", metadata)
        assert result is not None
```

## Fixtures and Factories

**Test Data:**
- Simple fixtures using `@pytest.fixture` decorator
- Fixtures scoped to function level (default)
- Example from `test_classifiers.py`:
```python
@pytest.fixture
def photo_rules(self) -> dict[str, RoutingRule]:
    """Create sample photo routing rules."""
    return {
        "photos": RoutingRule(
            extensions=[".jpg", ".jpeg", ".png"],
            destination="4_Archives/photos/{YYYY}/{MM}",
        )
    }
```

**Fixture location:**
- In-test fixtures: defined in test class as `@pytest.fixture` method
- Shared fixtures: in `tests/conftest.py` (like `project_root`, `fixtures_dir`)

**Test data files:**
- YAML test data: `tests/fixtures/test_reference_tree.yaml`
- Minimal fixtures with only necessary fields
- Use factory-like fixtures that accept parameters via fixture functions

## Mocking

**Framework:** unittest.mock (from standard library)

**Patterns:**
```python
from unittest.mock import patch, MagicMock

# Patch external service calls
@patch("para_files.classifiers.book_detector.lookup_isbn")
def test_isbn_lookup(mock_lookup):
    """Test with mocked ISBN lookup."""
    mock_lookup.return_value = BookInfo(title="Python", author="Guido")
    result = classifier.classify(...)
    assert result is not None

# Mock exception handling
def test_lookup_timeout():
    """Test graceful handling of lookup timeout."""
    with patch("para_files.utils.isbn_lookup.lookup_isbn") as mock_lookup:
        mock_lookup.side_effect = TimeoutError("Connection timeout")
        result = isbn_lookup(...)
        assert result is None
```

**What to Mock:**
- External API calls (ISBN lookup, geolocation services)
- File system operations in some cases (when testing path resolution logic)
- Time-dependent operations (use `freezegun` if needed, though not currently used)

**What NOT to Mock:**
- Pydantic models (use real instances)
- Pure functions (test the actual implementation)
- Classification pipeline classifiers (integration test the chain)
- Core business logic (test real behavior)

**Example from test_pdf_metadata.py:**
```python
from unittest.mock import patch

def test_isbn_extraction_from_pdf_content():
    """Test extracting ISBN from actual PDF text."""
    # Uses real extract_isbn(), not mocked
    text = "ISBN: 978-0-596-51774-8"
    result = extract_isbn(text)
    assert result is not None
```

## Coverage

**Requirements:** 80% code coverage enforced (minimum)

**Configuration (pyproject.toml):**
```toml
[tool.coverage.run]
source = ["src/para_files"]
branch = true
parallel = true
omit = ["*/tests/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
fail_under = 80
show_missing = true
```

**View Coverage:**
```bash
uv run pytest --cov                    # Run tests with coverage
uv run pytest --cov --cov-report=html # Generate HTML report
```

**Coverage exclusions:**
- Abstract method stubs (marked `@abstractmethod`)
- TYPE_CHECKING blocks (type-only imports)
- `if __name__ == "__main__":` blocks
- `__repr__` methods (not critical)

## Test Types

**Unit Tests:**
- Scope: Individual functions and methods
- Approach: Fast, isolated from external dependencies
- Example: `test_classify_match()` tests single classifier behavior
- Location: `tests/test_*.py` files co-located with each module

**Integration Tests:**
- Scope: Multiple components working together (classifiers in pipeline, config loading)
- Approach: Full object instantiation, some external dependencies (file I/O, but not network)
- Example: `test_pipeline.py` tests the full classification cascade
- Marked with `@pytest.mark.integration` if needed

**E2E Tests:**
- Framework: Uses `typer.testing.CliRunner` for CLI testing
- Not full end-to-end (don't test actual file moving), but tests CLI integration
- Example from `test_main.py`:
```python
def test_main_help():
    """Verify main function shows help."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "para-files" in result.output.lower()
```

**Test markers:**
```toml
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
]
```

**Run without slow tests:**
```bash
uv run pytest -m "not slow"
```

## Common Patterns

**Async Testing:**
- Not used (project doesn't use async code)
- All operations are synchronous

**Error Testing:**
```python
def test_no_match_without_metadata(self, photo_rules: dict[str, RoutingRule]):
    """Test that classifier returns None without metadata."""
    classifier = RulesEngineClassifier(photo_rules)
    result = classifier.classify("some content")
    assert result is None

def test_isbn13_valid(self):
    """Test extracting valid ISBN-13."""
    text = "This book has ISBN: 9780596517748"
    result = extract_isbn(text)
    assert result is not None
    assert len(result) == 13
```

**Expected failures:**
- Use `pytest.raises()` for expected exceptions:
```python
def test_cannot_instantiate_abstract(self):
    """Test that BaseClassifier cannot be instantiated."""
    with pytest.raises(TypeError):
        BaseClassifier()  # type: ignore[abstract]
```

**Type-ignore in tests:**
- Use `# type: ignore[abstract]` for intentional typing bypasses in tests

## Configuration Options

**Strict mode enabled:**
```toml
addopts = [
    "-ra",              # Show all summary info
    "-q",               # Quiet (only show dots)
    "--strict-markers", # Fail on unknown markers
    "--strict-config",  # Fail on invalid config
]
```

**Warning handling:**
```toml
filterwarnings = [
    "error",                          # Treat warnings as errors
    "ignore::DeprecationWarning",    # Except deprecation warnings
]
```

## Test Execution Examples

**Run specific test:**
```bash
uv run pytest tests/test_classifiers.py::TestBaseClassifier::test_cannot_instantiate_abstract
```

**Run with verbose output:**
```bash
uv run pytest -vv tests/test_types.py
```

**Run with detailed error info:**
```bash
uv run pytest --tb=long tests/test_pdf_metadata.py
```

**Run only integration tests:**
```bash
uv run pytest -m integration
```

**Run with coverage per file:**
```bash
uv run pytest --cov=src/para_files --cov-report=term-missing
```

## Special Test Files

**test_main.py - CLI Integration:**
- Uses `CliRunner` from typer.testing
- Tests command invocation, exit codes, output messages
- Verifies help, version, and error handling

**test_book_detector.py - Complex classification:**
- Tests book structure scoring
- Tests ISBN extraction from various formats
- Tests Thema classification integration
- Uses factory methods for test data

**test_rules_engine.py - Pattern matching:**
- 41 separate test cases for routing rules
- Tests extension matching, glob patterns, date extraction
- Tests placeholder resolution ({year}, {month}, {issuer})

**test_pipeline.py - Full cascade:**
- Tests prioritization (first match wins)
- Tests all 5 classifiers in order
- Tests lazy initialization

## Pre-commit Checks

**Ruff in tests:**
```toml
"tests/**/*.py" = [
    "S101",     # Allow assert in tests
    "ARG",      # Allow unused fixture arguments
    "FBT",      # Allow boolean trap
    "PLR2004",  # Allow magic values
    "ANN",      # Allow missing type hints
    "SLF001",   # Allow private member access
    "S108",     # Allow temp file paths
    "DTZ",      # Allow naive datetimes
    "RUF059",   # Allow unused unpacked variables
]
```

**Mypy in tests:**
- Relaxed: `disallow_untyped_defs = false`
- Allows omitting type hints in tests for brevity

---

*Testing analysis: 2026-02-28*
