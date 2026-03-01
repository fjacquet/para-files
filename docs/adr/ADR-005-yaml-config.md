# ADR-005: YAML Reference Tree for Routing Configuration

**Date**: 2024-01-01
**Status**: Accepted
**Deciders**: Frédéric Jacquet

---

## Context

Users need to define:
- Their personal PARA folder structure
- Known issuers (banks, utilities, insurers) and their destination paths
- Semantic utterances (example phrases) for route matching
- Special routing rules (photos, videos, courses, books)

This configuration must be:
- Human-readable and hand-editable
- Expressive enough for complex routing logic
- Loadable at startup without recompilation

Options considered:
- **TOML** — good for flat configs, limited for nested data
- **JSON** — verbose, no comments
- **Python DSL** — too flexible, security risk, requires code editing
- **Database** — overkill, not diff-friendly
- **YAML** — human-readable, supports anchors/aliases, widely understood

## Decision

Use a **single YAML file** (`config/personal_file_tree.yaml`) as the primary routing configuration. This file is loaded at startup by `ReferenceTree` and validated via Pydantic models.

## Rationale

### Human Editability

The primary user is a developer who understands YAML syntax. The configuration contains:
- Nested issuer lists (banks → list of bank names)
- Route patterns with placeholders (`{year}`, `{issuer}`, `{location}`)
- Utterance lists for semantic matching

YAML's multi-line strings, indentation-based nesting, and support for comments make this more maintainable than JSON.

### Schema Validation via Pydantic

The YAML is deserialized into `ReferenceTreeData` and its nested Pydantic models. Invalid config produces clear validation errors before any file is touched.

### Layered Configuration

A four-level priority stack allows overrides without editing the YAML directly:

```
Env vars (PARA_FILES_*) > .env file > YAML config section > Defaults
```

This enables CI/CD or headless usage via environment variables while keeping user routing rules in YAML.

### Single File Policy

All routing, issuers, semantic routes, and global config live in one file. This:
- Simplifies backup/version control (one file to track)
- Makes sharing or moving configurations trivial
- Avoids configuration drift between multiple files

## Consequences

- `personal_file_tree.yaml` is the required configuration artifact for a useful installation.
- A default/example file ships at `config/personal_file_tree.yaml` in the repository.
- The `ReferenceTree` class is responsible for loading and validating the file.
- YAML anchors/aliases are supported (PyYAML `safe_load` resolves them).
- No hot-reloading — changes require restarting `para-files`.
- The config section supports `mlx.model_name`, `mlx.score_threshold`, `llm.enabled`, `llm.model`, and `para_root`.
