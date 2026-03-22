# Coding Conventions

**Analysis Date:** 2025-03-22

## Naming Patterns

**Files:**

- Module files: `snake_case` (e.g., `rules_engine.py`, `filename_sanitizer.py`)
- Test files: `test_` prefix followed by module name (e.g., `test_rules_engine.py`, `test_filename_sanitizer.py`)
- CLI command files: `{command}_cmd.py` suffix (e.g., `classify_cmd.py`, `move_cmd.py`)
- Config/taxonomy files: `lowercase_with_underscores.json` or `.yaml` (e.g., `personal_file_tree.yaml`, `documents.json`)

**Functions:**

- Function names: `snake_case` for all functions
- Private/internal functions: `_leading_underscore` prefix (e.g., `_ensure_initialized()`, `_matches_extension_and_pattern()`)
- Helper functions in tests: no prefix, use descriptive names (e.g., `make_metadata()`)
- Constants for internal implementation: `_UPPERCASE_WITH_UNDERSCORES` (e.g., `_MIN_CONTENT_FOR_RENAME = 50`, `_HASH_BUFFER_SIZE = 65536`)

**Variables:**

- Local variables: `snake_case`
- Class instance variables: `_leading_underscore` for private attributes (e.g., `self._classifiers`, `self._config`)
- Public attributes: direct names without underscore (e.g., `value`, `source` in Pydantic models)

**Types:**

- Class names: `PascalCase` (e.g., `ClassificationPipeline`, `RulesEngineClassifier`, `FileMetadata`)
- Enum names: `PascalCase` (e.g., `ClassificationSource`, `ConflictStrategy`)
- Type aliases: `PascalCase` when significant, `snake_case` when inline

## Code Style

**Formatting:**

- Tool: **Ruff** for both linting and formatting
- Line length: **100 characters** (enforced via `ruff.line-length`)
- Quote style: **Double quotes** (enforced via `ruff.format.quote-style = "double"`)
- Indentation: **4 spaces** (no tabs)
- Line endings: Auto (platform-dependent)

**Linting:**

- Tool: **Ruff** (comprehensive rule set)
- Selected rules include: Pyflakes (F), pycodestyle (E, W), isort (I), pep8-naming (N), flake8-annotations (ANN), flake8-bandit (S), flake8-comprehensions (C4), flake8-simplify (SIM), Pylint (PL), and many more
- Key ignored rules:
  - `COM812`: Trailing commas (conflicts with formatter)
  - `ISC001`: Implicit string concatenation (conflicts with formatter)
  - `TD002`, `TD003`: TODO author/issue requirements (optional)
  - `TC001-003`: Type-checking block imports (over-optimization)
  - `PLC0415`: Lazy imports allowed (intentional for circular dependency avoidance)
- Per-file exceptions for test files, classifiers, CLI commands (see `pyproject.toml` for specific allowances)

**Type Checking:**

- Tool: **MyPy** in strict mode
- Configuration:
  - `strict = true`
  - `disallow_untyped_defs = true`
  - `disallow_incomplete_defs = true`
  - `check_untyped_defs = true`
  - `disallow_untyped_decorators = true`
  - `no_implicit_optional = true`
- All functions must have complete type annotations (parameters and return types)
- Test modules allowed reduced strictness (`disallow_untyped_defs = false`)
- Third-party libraries with missing stubs: `ignore_missing_imports = true`

**Python Version:**

- Minimum: **Python 3.12**
- Future imports: `from __future__ import annotations` in all modules (enables PEP 563 postponed evaluation)

## Import Organization

**Order:**

1. Future imports: `from __future__ import annotations`
2. Standard library imports (e.g., `from pathlib import Path`, `from typing import TYPE_CHECKING`)
3. Third-party imports (e.g., `from pydantic import BaseModel`, `from loguru import logger`)
4. Local application imports (e.g., `from para_files.config import Config`)
5. Conditional TYPE_CHECKING block for type-only imports (prevents circular dependencies)

**Path Aliases:**

- First-party package: `para_files` (configured in `pyproject.toml` under `ruff.lint.isort.known-first-party`)
- Enforced via isort integration in Ruff

**Blank Lines:**

- 2 blank lines after imports (enforced via `ruff.lint.isort.lines-after-imports = 2`)
- 2 blank lines between top-level class/function definitions
- 1 blank line between method definitions

**Type Checking Blocks:**

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from para_files.types import ClassificationResult
```

Used to avoid circular imports while maintaining type hints.

## Error Handling

**Patterns:**

- No bare `except` clauses; always specify exception type(s)
- Avoid catching broad exceptions like `Exception`; catch specific types:

  ```python
  try:
      value = int(user_input)
  except ValueError as e:
      logger.error(f"Invalid input: {e}")
  ```

- Use `SystemExit` with code 1 for CLI validation errors (e.g., in `validate_file_exists()`)
- Custom exception types not used; rely on standard library exceptions

**Logging over printing:**

- Never use `print()` for normal output; linting rule `T20` enforces this
- Use `from loguru import logger` for all logging:

  ```python
  from loguru import logger
  logger.info(f"Processing {filename}")
  logger.warning(f"Fallback used for {path}")
  logger.error(f"Failed to classify {file}: {error}")
  ```

**Return None vs. raising:**

- Return `None` when operation is optional/non-matching (e.g., classifier doesn't match)
- Raise exceptions for unrecoverable errors (e.g., invalid config, file I/O failure)
- Pattern in classifiers:

  ```python
  def classify(self, content: str, metadata: FileMetadata | None = None) -> ClassificationResult | None:
      if not metadata:
          return None  # Can't classify without metadata
      # ... try to classify ...
      if not matches_rule:
          return None  # This classifier doesn't match; next one tries
  ```

## Logging

**Framework:** `loguru` (not standard library `logging`)

**Setup:**

- Configured in `src/para_files/logging.py` via `setup_logging()`
- Console output: Human-readable format with color support
- File output: JSON format for audit trail (when `log_to_file=True`)
- Rotation: Size-based or time-based (configurable via `config.rotation`)
- Retention: Automatic cleanup (configurable via `config.retention`)
- Thread-safe: Uses `enqueue=True` for async writes

**Patterns:**

- Import: `from loguru import logger` (not `import logging`)
- Log levels used: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- Messages should be descriptive:

  ```python
  logger.info(f"Classified {filename} as {category}")
  logger.warning(f"ISBN lookup failed for {isbn}, falling back to heuristics")
  logger.error(f"Failed to write to {path}: {error}")
  ```

- Avoid logging secrets or sensitive data (paths may contain user identifiers)

**Noisy library suppression:**

- Libraries that log expected failures (e.g., `isbnlib` logs 404s, `pypdf` logs malformed PDFs) are silenced in `setup_logging()` to prevent log spam

## Comments

**When to Comment:**

- Docstrings: Always present for all public classes, functions, and methods
- Inline comments: Only for non-obvious logic or temporary workarounds
- Avoid obvious comments: Bad: `# increment i`; Good: `# Double-checked locking to ensure thread safety`

**JSDoc/TSDoc Style:**
Use Google-style docstrings with type annotations. Examples:

```python
def sanitize_filename(
    name: str,
    replacement: str = "_",
    max_length: int | None = None,
    *,
    preserve_extension: bool = False,
) -> str:
    """Sanitize a string for safe use as a filename.

    Replaces invalid characters and whitespace with the replacement character.
    Optionally truncates to a maximum length.

    Args:
        name: Original string to sanitize.
        replacement: Character to replace invalid chars with (default: "_").
        max_length: Maximum length of result (None = unlimited).
        preserve_extension: If True and max_length set, preserve file extension.

    Returns:
        Sanitized filename-safe string.

    Examples:
        >>> sanitize_filename("Hello: World")
        'Hello_World'
        >>> sanitize_filename("File/Name#Test")
        'File_Name_Test'
    """
```

**Class docstrings:**

```python
class ClassificationPipeline:
    """Orchestrates 6-signal classification cascade (v2.2).

    Simplified pipeline using JSON taxonomies:
    1. Rules Engine (95%) - Extension/pattern based routing
    2. Book Detector (92%, 100% with ISBN) - ISBN + Thema classification
    3. Taxonomy Classifier (90%) - Issuers + keywords from documents.json
    4. Semantic Classifier (85%) - Ollama embedding similarity via litellm
    5. Extension Router (97%) - Deterministic routing by file extension
    6. LLM Fallback (60%) - Optional LLM via litellm/Ollama

    First match wins. If nothing matches, returns default 0_Inbox.
    """
```

## Function Design

**Size:**

- Target: Single responsibility principle; functions doing one thing well
- Max complexity (McCabe): 10 (enforced via `ruff.lint.mccabe.max-complexity = 10`)
- Max statements: 50 (enforced via `ruff.lint.pylint.max-statements = 50`)
- Large functions allowed with per-file exceptions (e.g., `rules_engine.py`, `mover.py`)

**Parameters:**

- Max parameters: 6 (enforced via `ruff.lint.pylint.max-args = 6`)
- CLI commands exempt (naturally have many parameters via Typer)
- Prefer named parameters over positional for readability:

  ```python
  FileMover(
      para_root=config.para_root,
      dry_run=True,
      copy_mode=False,
      conflict_strategy=ConflictStrategy.RENAME,
  )
  ```

**Return Values:**

- Max early returns: 6 (enforced via `ruff.lint.pylint.max-returns = 6`)
- Use explicit returns; avoid implicit `None` returns
- Single return point preferred when readable, early returns acceptable for error handling

**Optional/Union types:**

- Use `X | None` syntax (PEP 604) for optional types
- Avoid `Optional[X]` (now discouraged in favor of union syntax)

## Module Design

**Exports:**

- Use `__all__` in modules with public exports (e.g., `logging.py`)
- Example:

  ```python
  __all__ = ["logger", "setup_logging"]
  ```

**Barrel Files:**

- CLI modules use barrel imports in `__init__.py`:

  ```python
  # src/para_files/cli/__init__.py
  from para_files.cli import (
      bookstore_cmd,
      classify_cmd,
      # ... other commands
  )
  ```

- Commands register via `@app.command()` decorator when imported
- Main entry point imports all command modules to trigger registration

**Lazy Imports:**

- Allowed when necessary to avoid circular dependencies (exception: `PLC0415`)
- Example in `logging.py`:

  ```python
  def setup_logging(config: LoggingConfig | None = None) -> None:
      import logging  # Import here to avoid circular dependency
      from para_files.config import LoggingConfig
  ```

---

*Convention analysis: 2025-03-22*
