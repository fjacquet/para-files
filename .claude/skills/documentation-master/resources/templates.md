# Documentation Templates

Ready-to-use templates for consistent documentation.

## README Section Templates

### New CLI Command

```markdown
### command-name

Brief description of what the command does.

\`\`\`bash
# Basic usage
uv run para-files command-name <required-arg>

# With options
uv run para-files command-name <arg> --option value

# Common patterns
uv run para-files command-name *.pdf --json
uv run para-files command-name <arg> -v
\`\`\`

**Options:**

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--option` | `-o` | What this option does | `default` |
| `--dry-run` | `-n` | Preview without executing | `false` |
| `--json` | | Output as JSON | `false` |
| `--verbose` | `-v` | Enable verbose output | `false` |
```

### New Configuration Option

```markdown
### Configuration Section Name

| Variable | Default | Description |
|----------|---------|-------------|
| `PARA_FILES_NEW_OPTION` | `default_value` | Brief explanation of what this controls |

**Example:**

\`\`\`bash
# Via environment variable
export PARA_FILES_NEW_OPTION="custom_value"

# Via .env file
PARA_FILES_NEW_OPTION=custom_value
\`\`\`
```

## CHANGELOG Templates

### New Version Release

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- Feature description with context (#PR)

### Changed
- Behavior change explanation (#PR)

### Fixed
- Bug fix with reproduction context (#PR)

### Deprecated
- Feature being phased out with timeline (#PR)

### Removed
- Removed feature with migration path (#PR)

### Security
- Security fix details (#PR)
```

### Single Entry Templates

```markdown
### Added
- **command-name**: New command for doing X (#123)
- Support for Y format in classify command (#124)

### Changed
- `classify` now returns additional metadata field Z (#125)
- Default threshold increased from 0.7 to 0.75 (#126)

### Fixed
- Fix crash when processing empty PDF files (#127)
- Correct confidence calculation for edge cases (#128)

### Removed
- Remove deprecated `--old-flag` option (#129)
  - **Migration**: Use `--new-flag` instead
```

## CLAUDE.md Templates

### New CLI Command Section

```markdown
| `command-name <args>` | Brief description (`--option1`, `--option2`) |
```

### Architecture Change

```markdown
### Component Name

Description of component purpose and responsibilities.

\`\`\`mermaid
flowchart TB
    subgraph component["Component Name"]
        a["Part A"]
        b["Part B"]
    end
    component --> output["Output"]
\`\`\`
```

## Docstring Templates

### Module Docstring

```python
"""Module purpose in one line.

Extended description if needed. Explain what this module provides
and when it should be used.

Example:
    >>> from para_files.module import function
    >>> result = function("input")
"""
```

### Function Docstring

```python
def function_name(param1: str, param2: int = 10) -> Result:
    """Brief description of what the function does.

    Extended description with more context about behavior,
    edge cases, or important notes.

    Args:
        param1: Description of first parameter.
        param2: Description with default. Defaults to 10.

    Returns:
        Description of return value with type context.

    Raises:
        ValueError: When param1 is empty.
        FileNotFoundError: When referenced file doesn't exist.

    Example:
        >>> result = function_name("test")
        >>> result.success
        True
    """
```

### Class Docstring

```python
class ClassName:
    """Brief description of the class purpose.

    Extended description of the class, its responsibilities,
    and typical usage patterns.

    Attributes:
        attr1: Description of attribute.
        attr2: Description of attribute.

    Example:
        >>> obj = ClassName(config)
        >>> obj.method()
    """
```

## Error Message Templates

### User-Facing Errors

```python
# Informative error with action
raise ValueError(
    f"Invalid configuration: {setting!r} must be a positive number. "
    f"Current value: {value}. "
    f"Set PARA_FILES_{setting.upper()} environment variable."
)

# Missing dependency
raise ImportError(
    "MLX is required but not installed. "
    "This package requires macOS with Apple Silicon. "
    "Install with: uv sync --all-extras"
)

# File operation error
raise FileNotFoundError(
    f"Reference tree not found: {path}. "
    f"Create one at {default_path} or set PARA_FILES_REFERENCE_TREE_PATH."
)
```

## Test Documentation Template

```python
"""Tests for module_name functionality.

This module tests:
- Feature A behavior
- Feature B edge cases
- Integration between A and B
"""

class TestFeatureA:
    """Tests for Feature A."""

    def test_basic_functionality(self):
        """Feature A should do X when given Y."""

    def test_edge_case_empty_input(self):
        """Feature A should handle empty input gracefully."""

    def test_error_condition(self):
        """Feature A should raise ValueError for invalid input."""
```

## PR Description Template

```markdown
## Summary

Brief description of what this PR does (1-2 sentences).

## Changes

- Change 1 with context
- Change 2 with context
- Change 3 with context

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing performed

## Documentation

- [ ] README.md updated (if CLI changes)
- [ ] CHANGELOG.md entry added
- [ ] Docstrings added for new functions

## Breaking Changes

None / Description of breaking changes and migration path

## Related Issues

Closes #123
```

## Commit Message Templates

### Feature

```
feat: add new-feature to component

- Implement X functionality
- Add Y support
- Update tests for new behavior

Closes #123
```

### Bug Fix

```
fix: resolve issue with feature

The problem was caused by X when Y occurred.
Fixed by changing Z.

Fixes #456
```

### Documentation

```
docs: update README with new command

- Add command-name section
- Update configuration table
- Fix outdated examples
```

### Refactor

```
refactor: simplify classification logic

- Extract common code into helper function
- Reduce cyclomatic complexity
- No functional changes
```

## Issue Templates

### Bug Report

```markdown
## Bug Description

Brief description of the bug.

## Steps to Reproduce

1. Step one
2. Step two
3. See error

## Expected Behavior

What should happen.

## Actual Behavior

What actually happens.

## Environment

- OS: macOS [version]
- Python: [version]
- para-files: [version]

## Logs/Output

\`\`\`
Paste relevant output here
\`\`\`
```

### Feature Request

```markdown
## Feature Description

Brief description of the desired feature.

## Use Case

Why this feature would be useful.

## Proposed Solution

How this could be implemented (optional).

## Alternatives Considered

Other approaches considered (optional).
```
