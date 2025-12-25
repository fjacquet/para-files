---
name: python-dev
description: |
  Python development skill enforcing best practices: uv package manager, venv virtual environments, functional programming, DRY, KISS principles. Mandatory Pydantic for AI agent integrations. Use when: (1) Creating Python scripts, (2) Setting up Python projects, (3) Developing AI agent tools, (4) Refactoring Python code.
---

# Python Development Skill

## Environment Setup (Mandatory)

```bash
# Create venv with uv
uv venv .venv

# Activate venv
source .venv/bin/activate

# Install packages (NEVER use pip directly)
uv pip install <package> --python .venv/bin/python

# Run scripts
.venv/bin/python script.py
```

## Core Principles

### 1. Functional Programming First

```python
# GOOD: Pure functions, immutable data
from functools import reduce
from typing import Sequence

def calculate_total(items: Sequence[float]) -> float:
    return reduce(lambda acc, x: acc + x, items, 0.0)

# BAD: Side effects, mutations
total = 0
def add_to_total(x):
    global total
    total += x
```

### 2. DRY (Don't Repeat Yourself)

```python
# GOOD: Single source of truth
def format_name(first: str, last: str) -> str:
    return f"{first.strip().title()} {last.strip().title()}"

# BAD: Duplicated logic
name1 = f"{first1.strip().title()} {last1.strip().title()}"
name2 = f"{first2.strip().title()} {last2.strip().title()}"
```

### 3. KISS (Keep It Simple)

```python
# GOOD: Simple and direct
def is_valid_email(email: str) -> bool:
    return "@" in email and "." in email.split("@")[-1]

# BAD: Over-engineered
class EmailValidatorFactory:
    def create_validator(self, validator_type: str) -> "BaseValidator":
        ...
```

## Pydantic for AI Agents (Mandatory)

All AI agent tools MUST use Pydantic for input/output validation.

```python
from pydantic import BaseModel, Field

class ToolInput(BaseModel):
    """Input schema - always validated."""
    query: str = Field(..., description="Search query", min_length=1)
    limit: int = Field(default=10, ge=1, le=100)

class ToolOutput(BaseModel):
    """Output schema - structured response."""
    results: list[str]
    count: int

def my_tool(input_data: ToolInput) -> ToolOutput:
    # Process...
    return ToolOutput(results=["..."], count=1)
```

See [references/pydantic-patterns.md](references/pydantic-patterns.md) for advanced patterns.

## Script Template

Use `scripts/template.py` as starting point for new scripts.

## Project Structure

```
project/
├── .venv/              # Virtual environment (gitignored)
├── pyproject.toml      # Project config with uv
├── src/
│   └── module/
│       ├── __init__.py
│       ├── models.py   # Pydantic models
│       └── main.py
└── tests/
```

## Checklist Before Commit

- [ ] Type hints on all functions
- [ ] Pydantic models for external data
- [ ] No global mutable state
- [ ] Functions < 20 lines
- [ ] No code duplication
- [ ] uv for all dependencies
