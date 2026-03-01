# ADR-008: uv as Package Manager

**Date**: 2024-01-01
**Status**: Accepted
**Deciders**: Frédéric Jacquet

---

## Context

Python project packaging requires a tool to:
- Manage virtual environments
- Resolve and lock dependencies
- Run scripts in the correct environment
- Build distribution artifacts

Options in the Python ecosystem:

| Tool | Lock file | Speed | PEP 517 build | Maturity |
|------|-----------|-------|---------------|----------|
| `pip` + `venv` | No | Slow | No | Mature |
| `poetry` | Yes | Medium | Yes | Mature |
| `pipenv` | Yes | Slow | No | Declining |
| `pdm` | Yes | Fast | Yes | Growing |
| `uv` | Yes | ~10–100× faster | Yes | New (2024) |

## Decision

Use **uv** (from Astral, the makers of Ruff) as the sole package manager.

## Rationale

### Speed

`uv` is written in Rust and resolves dependencies 10–100× faster than pip. Installing the full dependency tree (MLX, PyObjC, Pydantic, etc.) takes ~10s vs ~90s with pip. This matters for CI/CD and local development iterations.

### Lockfile Compatibility

`uv.lock` provides reproducible installs equivalent to `poetry.lock` — all transitive dependencies are pinned. The lockfile is checked into version control.

### Single Tool

`uv` replaces:
- `python -m venv`
- `pip install`
- `pip-compile`
- `python setup.py`

The project uses `uv sync --all-extras` for full installation and `uv run <cmd>` for script execution. No separate activation step is required.

### PEP 517 Compliance

`uv` builds with `hatchling` (declared in `pyproject.toml`) — standard PEP 517 compliance. The project can also be built with any other PEP 517-compatible frontend.

### Alignment with Ruff

Both `uv` and `ruff` come from Astral. Using the same vendor for packaging and linting reduces cognitive overhead and ensures compatibility.

## Consequences

- `uv` must be installed before running any project commands (documented in the getting-started guide).
- All `CLAUDE.md` and `Makefile` commands use `uv run` prefix instead of direct script invocation.
- CI/CD uses `astral-sh/setup-uv` GitHub Action.
- `uv.lock` is committed and must be updated when dependencies change (`uv sync`).
- Developers familiar only with `pip`/`poetry` need to learn `uv` syntax (minimal, similar to `pip`).
