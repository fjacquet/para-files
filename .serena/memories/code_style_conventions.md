# Code Style and Conventions

## Python Version

- Python 3.12+ required
- Use `from __future__ import annotations` in all modules

## Type Hints

- **Strict mypy** enabled - all public functions must be fully typed
- Package is typed (`py.typed` marker present)
- Use `TYPE_CHECKING` imports for type-only imports

## Formatting

- **Line length**: 100 characters
- **Formatter**: ruff format
- **Quote style**: Double quotes
- **Indent style**: Spaces (4)
- Docstring code is also formatted

## Import Style

- Use ruff/isort for import sorting
- Known first-party: `para_files`
- No force single line imports
- 2 blank lines after imports

## Naming Conventions

- Standard PEP 8 naming (enforced by ruff N rules)
- Classes: PascalCase
- Functions/methods: snake_case
- Constants: UPPER_SNAKE_CASE
- Private: \_single_leading_underscore

## Documentation

- **Diagrams**: Always use Mermaid, NEVER ASCII box art
- **Markdown**: GitHub-flavored markdown
- For simple component lists: Use markdown tables instead of ASCII boxes
- Update CHANGELOG.md for all changes

## Code Patterns

### Lazy Loading

MLX models use lazy loading - they download automatically on first use:

```python
encoder = MLXEncoder(model_name="mlx-community/nomic-embed-text-v1.5")
# Model loads on first call
embeddings = encoder(["text"])
```

### Error Handling

- Use specific exceptions, not bare except
- Follow flake8-bugbear (B) and tryceratops (TRY) rules

### Security

- Follow flake8-bandit (S) rules
- Be careful with: command injection, XSS, SQL injection

## Linting Rules

Comprehensive ruff ruleset enabled including:

- Pyflakes (F), pycodestyle (E, W), isort (I)
- flake8-annotations (ANN), flake8-bandit (S)
- flake8-bugbear (B), flake8-comprehensions (C4)
- Pylint (PL), and many more

See `pyproject.toml` for complete configuration.

## Test Conventions

- Tests in `tests/` directory
- pytest with strict markers
- Some rules relaxed for tests (S101 for assert, etc.)
- Target: 80% coverage minimum
