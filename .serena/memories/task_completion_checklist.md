# Task Completion Checklist

## Before Committing Code

### 1. Run Quality Checks

```bash
# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

### 2. Run Tests

```bash
# All tests
uv run pytest

# With coverage (ensure ≥80%)
uv run pytest --cov
```

### 3. Update Documentation

| Change Type         | What to Update                                      |
| ------------------- | --------------------------------------------------- |
| New feature/command | `CHANGELOG.md` (Unreleased), `README.md`            |
| Bug fix             | `CHANGELOG.md` (Unreleased)                         |
| Architecture change | `CHANGELOG.md`, `docs/architecture.md`              |
| Config change       | `CHANGELOG.md`, `README.md` (Configuration section) |
| Breaking change     | `CHANGELOG.md` with migration notes                 |

### 4. Verify Checklist

- [ ] `CHANGELOG.md` has entry under `[Unreleased]`
- [ ] README reflects any new CLI options
- [ ] Docstrings added for new public functions
- [ ] No security vulnerabilities introduced
- [ ] Type hints added for all new public functions

## Code Review Considerations

### Do NOT:

- Introduce security vulnerabilities (OWASP top 10)
- Over-engineer solutions
- Add features beyond what was requested
- Add unnecessary error handling
- Create abstractions for one-time operations
- Use ASCII box art in markdown (use Mermaid instead)

### Do:

- Keep solutions simple and focused
- Read code before suggesting modifications
- Follow existing patterns and conventions
- Use specific exceptions
- Validate at system boundaries only

## Pre-commit Hooks

If pre-commit hooks are installed, they will run automatically:

```bash
# Run manually if needed
pre-commit run --all-files
```
