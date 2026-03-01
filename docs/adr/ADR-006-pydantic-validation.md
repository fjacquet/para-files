# ADR-006: Pydantic for Data Validation and Settings

**Date**: 2024-01-01
**Status**: Accepted
**Deciders**: Frédéric Jacquet

---

## Context

The classification pipeline passes structured data between components:
- File metadata (path, size, dates, EXIF, PDF metadata)
- Classification results (category, confidence, extracted params)
- Configuration (PARA root, MLX settings, LLM settings)
- Reference tree data (routes, issuers, routing rules)

Without validation, a malformed YAML config or unexpected file metadata could propagate as silent bugs deep into the pipeline.

## Decision

Use **Pydantic v2** (`pydantic>=2.12.0`) for all data models and **pydantic-settings** (`pydantic-settings>=2.6.0`) for settings/configuration.

## Rationale

### Type Safety at Runtime

Python's type hints are erased at runtime. Pydantic enforces them:
- `FileMetadata.size_bytes: int = Field(ge=0)` raises a `ValidationError` if a negative size is passed.
- `Confidence.value: float = Field(ge=0.0, le=1.0)` rejects invalid confidence scores.

### YAML Deserialization

Pydantic models act as the schema for YAML loading. Rather than manually checking `isinstance(data['routes'], list)`, the model constructor handles coercion and reports all validation errors at once.

### Settings Hierarchy

`pydantic-settings`' `BaseSettings` automatically reads environment variables with a configured prefix (`PARA_FILES_`), merges them with defaults, and provides a typed settings object. This is simpler and less error-prone than a custom `os.environ.get()` chain.

### Immutability and Serialization

Pydantic models support `.model_dump()` and `.model_json_schema()` out of the box. `ClassificationResult` can be serialized to JSON for logging or debugging without custom serializers.

### IDE Integration

Pydantic's type annotations provide full autocomplete in IDEs — developers can discover available fields on `FileMetadata` or `ClassificationResult` without reading docs.

## Consequences

- `pydantic>=2.12.0` and `pydantic-settings>=2.6.0` are required core dependencies.
- Pydantic v2's model syntax (`model_config`, `Field(...)`, `model_validator`) is used throughout — not v1 compatibility shims.
- `mypy` with strict mode enforces that Pydantic models are used correctly at analysis time.
- Mutable state (e.g., appending to `signals` list) requires careful handling — the `signals` field uses `default_factory=list` to avoid shared state between instances.
- `model_config = {"arbitrary_types_allowed": True}` is required for `FileMetadata` because `Path` and `datetime` fields use non-JSON-native types.
