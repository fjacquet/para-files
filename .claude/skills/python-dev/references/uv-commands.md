# uv Quick Reference

## Environment Management

```bash
# Create virtual environment
uv venv .venv

# Create with specific Python version
uv venv .venv --python 3.12
```

## Package Installation

```bash
# Install package
uv pip install requests

# Install with extras
uv pip install "fastapi[all]"

# Install from requirements
uv pip install -r requirements.txt

# Install in development mode
uv pip install -e .

# Specify Python interpreter
uv pip install package --python .venv/bin/python
```

## Dependency Management

```bash
# Freeze current environment
uv pip freeze > requirements.txt

# Compile requirements (lock versions)
uv pip compile requirements.in -o requirements.txt

# Sync environment with requirements
uv pip sync requirements.txt
```

## Project Commands

```bash
# Initialize new project
uv init project-name

# Add dependency to pyproject.toml
uv add requests

# Add dev dependency
uv add --dev pytest

# Remove dependency
uv remove requests

# Update all dependencies
uv lock --upgrade
```

## Running Scripts

```bash
# Run with uv-managed Python
uv run python script.py

# Run tool installed via uv
uv run pytest

# Run with specific Python
uv run --python 3.12 script.py
```

## pyproject.toml Example

```toml
[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "httpx>=0.25",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.1",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
]
```
