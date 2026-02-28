# Coding Conventions

**Analysis Date:** 2026-02-28

## Naming Patterns

**Files:**

- Lowercase with underscores for modules: `pipeline.py`, `rules_engine.py`, `pdf_metadata.py`
- CamelCase for test files matching module name: `test_classifiers.py`, `test_book_detector.py`
- Classifiers are organized in `src/para_files/classifiers/` subdirectory
- Utilities in `src/para_files/utils/` subdirectory
- Commands in `src/para_files/cli/` subdirectory

**Functions:**

- snake_case for all functions: `classify()`, `extract_isbn()`, `read_content_preview()`, `files_are_identical()`
- Helper functions prefixed with underscore: `_compute_file_hash()`, `_ensure_initialized()`, `_load_yaml_config()`
- Constants in UPPER_SNAKE_CASE: `DEFAULT_REFERENCE_TREE`, `DEFAULT_MLX_MODEL`, `_MAX_RENAME_ATTEMPTS`, `_HASH_BUFFER_SIZE`

**Variables:**

- snake_case for all variables: `file_path`, `metadata`, `content_preview`, `routing_rules`
- Type hints always present (mypy strict mode enabled)
- Enum values in UPPER_SNAKE_CASE: `VALIDATED_DB`, `RULES_ENGINE`, `SKIP`, `OVERWRITE`, `RENAME`

**Types:**

- CamelCase for all classes: `ClassificationResult`, `ClassificationSource`, `BaseClassifier`, `FileMover`, `RulesEngineClassifier`
- Pydantic `BaseModel` subclasses for data structures: `FileMetadata`, `ClassificationResult`, `RoutingRule`, `Config`
- Enums inherit from `str, Enum` for serialization: `ClassificationSource(str, Enum)`, `ConflictStrategy(str, Enum)`
- Abstract base classes in `src/para_files/classifiers/base.py` using `ABC`

## Code Style

**Formatting:**

- Ruff (v0.8.0+) for linting and formatting
- Black-compatible formatter with double quotes: `format = "string"` not `format = 'string'`
- Line length: 100 characters
- Indent: 4 spaces

**Linting:**

- Ruff with strict configuration (38 rule categories enabled)
- Python 3.12+ syntax enforced
- Comprehensive rules: F, E, W, C90, I, N, UP, YTT, ANN, ASYNC, S, BLE, FBT, B, A, COM, C4, DTZ, T10, EM, EXE, FA, ISC, ICN, LOG, G, INP, PIE, T20, PYI, PT, Q, RSE, RET, SLF, SLOT, SIM, TID, TCH, INT, ARG, PTH, TD, FIX, ERA, PD, PGH, PL, TRY, FLY, PERF, FURB, RUF

**Per-file exceptions in pyproject.toml:**

- Tests allow: `S101` (assert), `ARG` (unused args), `FBT` (bool trap), `PLR2004` (magic values), `ANN` (type hints), `SLF001` (private access), `S108` (temp paths), `DTZ` (datetime), `RUF059`
- `src/para_files/classifiers/rules_engine.py` allows: `C901` (complexity), `PLR0912` (too many branches)
- `src/para_files/mover.py` allows: `PLR0911` (too many returns)
- `src/para_files/utils/ocr.py` allows: `ANN401` (Any type for PyObjC)
- `src/para_files/main.py` and CLI commands allow: `FBT002` (bool default), `PLR0913` (too many args)

## Import Organization

**Order:**

1. Future imports: `from __future__ import annotations` (in every module)
2. Standard library: `import sys`, `from pathlib import Path`, `from datetime import datetime`
3. Third-party: `from pydantic import BaseModel`, `from loguru import logger`, `import yaml`
4. First-party: `from para_files.config import Config`, `from para_files.types import ClassificationResult`
5. TYPE_CHECKING block for type-only imports: `if TYPE_CHECKING: from para_files.classifiers.base import BaseClassifier`

**Path aliases:**

- Configured in pyproject.toml: `known-first-party = ["para_files"]`
- All imports use absolute paths from package root: `from para_files.config import Config` not relative imports

**Lazy imports:**

- Used intentionally in some modules (e.g., in `pipeline.py` for OCR utilities): `from para_files.utils.file_utils import extract_file_metadata`
- Ruff exception: `PLC0415` (import should be at top-level) disabled for intentional lazy loading

**Blank lines after imports:**

- Two blank lines between imports and code (enforced by isort: `lines-after-imports = 2`)
- Single-line imports preferred over multi-line: `from para_files.types import ClassificationResult, ClassificationSource`

## Error Handling

**Patterns:**

- Use custom exception types where possible (Pydantic ValidationError for config validation)
- Try/except blocks for operations that may fail:
  - File I/O: `try: file_path.open() except OSError:`
  - Date parsing: `try: datetime.strptime() except ValueError:`
  - Geolocation: `try: geopy_call() except (GeocoderTimedOut, GeocoderUnavailable):`

**Example from mover.py:**

```python
try:
    shutil.move(source, destination)
except OSError as e:
    logger.error("Failed to move {}: {}", source, e)
    return MoveResult(source=source, destination=destination, success=False, action="error", message=str(e))
```

- Raise `RuntimeError` with descriptive messages for unrecoverable errors
- Never silently ignore errors - always log or re-raise
- Safety checks with early returns and guards (e.g., "SAFETY: Prevented deletion of source=destination")

**Validation:**

- Pydantic models validate on instantiation (in `config.py`, `types.py`)
- Path validation with `Path.exists()` before operations
- File content checks before classification (empty files vs. readable content)
- Filesystem safety checks (permissions, size limits)

## Logging

**Framework:** loguru (not standard logging)

**Import:** `from loguru import logger` (imported module-wide, not per-function)

**Patterns:**

- **Debug level:** Development details

  ```python
  logger.debug("Technology from filename: {}", tech)
  logger.debug("Fiscal year from content: {}", year)
  ```

- **Info level:** User-facing operations

  ```python
  logger.info("Issuer '{}' already exists in category '{}'", issuer, category)
  logger.info("Added issuer '{}' to category '{}'", issuer, category)
  ```

- **Warning level:** Degraded operation or unexpected conditions

  ```python
  logger.warning("Route '{}' not found", route_name)
  logger.warning("SAFETY: Prevented deletion of source=destination: {}", source)
  ```

- **Error level:** Operation failures

  ```python
  logger.error("Failed to move {}: {}", source, e)
  ```

**Logging configuration:**

- Centralized in `src/para_files/logging.py`
- Console output: human-readable format
- File output: JSON format with rotation/retention
- Default level: INFO (DEBUG when `--verbose` flag used)
- Noisy loggers silenced: `isbnlib`, `pypdf` (expected warnings suppressed)

**Message format:**

- Use format strings with `{}` placeholders, not f-strings: `logger.info("Added file {}", path)`
- Never log raw exceptions inline (they'll show stack traces twice)

## Comments

**When to Comment:**

- Complex algorithms requiring explanation (e.g., rules engine placeholder resolution)
- Non-obvious design decisions
- Edge cases and safety considerations
- TODO/FIXME comments rare (ruff configured with `TD002`, `TD003`, `FIX002` disabled to avoid mandatory author/issue)

**Module docstrings:**

```python
"""Classification pipeline orchestrating 5-signal cascade.

Pipeline v2.0 - Simplified with taxonomy-based classification:
1. RulesEngine (95%) - Extension/pattern based routing
2. BookDetector (92%) - ISBN detection + Thema classification
...
"""
```

**Function/Class docstrings:**

- Google-style docstrings with Args, Returns, Raises

```python
def classify(self, content: str, metadata: FileMetadata | None = None) -> ClassificationResult | None:
    """Attempt to classify content.

    Args:
        content: Text content to classify (may be filename, file content, etc.).
        metadata: Optional file metadata for additional context.

    Returns:
        ClassificationResult if classification is possible, None otherwise.
    """
```

**JSDoc/TSDoc:**

- Not applicable (Python project)
- Property docstrings use single-line format:

```python
@property
def best_date(self) -> datetime | None:
    """Return the best available date for path resolution.

    Priority: EXIF date > file modified > file created.
    """
```

## Function Design

**Size:**

- Prefer functions under 50 lines
- Complex classifiers allowed up to ~100 lines for single logical operation
- Break up long functions into private helpers prefixed with underscore: `_extract_year_from_content()`

**Parameters:**

- Max 6 positional parameters (enforced by pylint: `max-args = 6`)
- Use Pydantic models for multiple related parameters instead of many scalars
- Type hints required for all parameters (mypy strict mode)
- Default values for optional parameters

**Return Values:**

- Use union types for optional returns: `ClassificationResult | None`
- Tuple returns for multiple values are OK, but Pydantic models preferred for clarity
- Return early to reduce nesting depth

**Example from base classifier:**

```python
@abstractmethod
def classify(
    self,
    content: str,
    metadata: FileMetadata | None = None,
) -> ClassificationResult | None:
    """Classify content, returning None if unable."""
```

## Module Design

**Exports:**

- Use `__all__` list in modules to define public interface
- Example from `logging.py`:

```python
__all__ = ["logger", "setup_logging"]
```

**Barrel Files:**

- Used sparingly for re-exporting from subpackages
- Example: `src/para_files/cli/__init__.py` imports all command modules to register them
- Not overused - most imports go directly to source files

**Module organization:**

- One primary class per module: `FileMover` in `mover.py`, `ClassificationPipeline` in `pipeline.py`
- Helper functions and enums in same module if closely related
- Utilities in `utils/` subpackage organized by concern: `pdf_metadata.py`, `filename_sanitizer.py`, `file_utils.py`

## Type Annotations

**Style:**

- Comprehensive type hints required (mypy strict mode enabled)
- Use `| None` union syntax (Python 3.10+), not `Optional[X]`
- Generics fully qualified: `list[str]`, `dict[str, Any]`
- Avoid `Any` except where unavoidable (PyObjC types)

**Configuration:**

- `disallow_untyped_defs = true` enforces all function signatures
- `disallow_incomplete_defs = true` rejects missing return types
- Test files have relaxed rules: `disallow_untyped_defs = false`

**Example:**

```python
def classify(
    self,
    content: str,
    metadata: FileMetadata | None = None,
) -> ClassificationResult | None:
    """Classification method with full type hints."""
```

## Special Patterns

**Lazy initialization:**

- ClassificationPipeline uses `_ensure_initialized()` lazy loading pattern to defer expensive operations
- Called before each classification attempt

**Pydantic validation:**

- Config objects validate on instantiation via pydantic-settings
- Path expansion in config: `Path(yaml_config["para_root"]).expanduser()`
- Arbitrary types allowed: `model_config = {"arbitrary_types_allowed": True}` in `FileMetadata`

**Abstract base classes:**

- `BaseClassifier` defines interface for all classifiers in pipeline
- Properties for `name`, `source`, `default_confidence`
- Abstract method `classify()` with standard signature

**Enums for safety:**

- Used extensively for classification sources: `ClassificationSource`, `ConflictStrategy`
- String enums inherit from `str, Enum` for serialization

---

*Convention analysis: 2026-02-28*
