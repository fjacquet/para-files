# ADR-007: Typer for CLI Framework

**Date**: 2024-01-01
**Status**: Accepted
**Deciders**: Frédéric Jacquet

---

## Context

para-files is a CLI tool. A CLI framework handles argument parsing, help text, error messages, and command grouping.

Options evaluated:
| Framework | Typing | Auto-help | Pros | Cons |
|-----------|--------|-----------|------|------|
| `argparse` | Manual | Minimal | stdlib, no deps | Verbose, no typing integration |
| `click` | Decorators | Good | Mature, large ecosystem | No type hint integration |
| `typer` | Type hints | Excellent | Built on Click, fully typed | Slightly opinionated |
| `docopt` | Docstring | Auto | Elegant | Not maintained |

## Decision

Use **Typer** (`typer>=0.21.0`) built on Click for all CLI commands.

## Rationale

### Type-Hint-Driven Interface

Typer derives argument types, defaults, and completions directly from Python type annotations:

```python
def move(
    files: list[Path],
    dry_run: bool = typer.Option(False, "--dry-run"),
    workers: int = typer.Option(4, "--workers", "-w"),
) -> None: ...
```

This integrates naturally with the project's strict `mypy` typing discipline — argument types are verified at analysis time, not just at runtime.

### Built on Click

Typer compiles down to Click, which means:
- The full Click ecosystem (testing with `CliRunner`, shell completion) works out of the box.
- `typer.testing.CliRunner` is used in tests to invoke CLI commands without subprocess overhead.

### Automatic Help Generation

Docstrings become help text automatically. This reduces duplication between code documentation and user-facing help:

```
$ para-files move --help
Move files to their PARA destination folders.
```

### Command Groups

`app = typer.Typer()` supports sub-commands cleanly:
```
para-files classify
para-files move
para-files learn
para-files add-issuer
```

Each command lives in its own module under `src/para_files/cli/`, keeping the main entry point (`main.py`) thin.

## Consequences

- `typer>=0.21.0` is a core dependency.
- All CLI commands must use type annotations for parameters — no untyped `click.argument()` calls.
- Boolean flags use `typer.Option(False, "--flag/--no-flag")` or default parameters with `FBT002` suppressed (standard Typer pattern).
- Commands with many parameters may trigger `PLR0913` (too many arguments) — suppressed for CLI files in `pyproject.toml`.
- Shell completion is available via `typer` out of the box but is not documented as a primary feature.
