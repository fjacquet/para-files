# ADR-004: MLX Embeddings with nomic-embed-text-v1.5

**Date**: 2024-01-01
**Status**: Accepted
**Deciders**: Frédéric Jacquet

---

## Context

Semantic classification requires converting file content into dense vector representations (embeddings) for similarity comparison. Options considered:

| Option | Pros | Cons |
|--------|------|------|
| OpenAI `text-embedding-ada-002` | High quality | API cost, requires internet, privacy concern |
| `sentence-transformers` (CPU) | Free, offline | Slow on CPU, no Apple Silicon optimization |
| `sentence-transformers` (CUDA) | Fast | Not available on macOS |
| MLX + `nomic-embed-text-v1.5` | Fast on ANE, offline, free | macOS only |
| `all-MiniLM-L6-v2` (MLX) | Smaller model | Lower quality for long documents |

## Decision

Use **`mlx-embedding-models`** with the **`nomic-embed-text-v1.5`** model via a custom `MLXEncoder` class that adapts the model to the `semantic-router` interface.

## Rationale

### nomic-embed-text-v1.5

- **768 dimensions** — rich enough for nuanced document matching.
- **8192 token context** — handles multi-page document previews.
- **Strong multilingual performance** — covers French, German, English documents common in Swiss/French administrative files.
- **Apache 2.0 license** — permissive, no commercial restrictions.

### MLX Runtime

- Leverages the Apple Neural Engine (ANE) — embedding a 2,000-character document takes ~50ms vs ~500ms on CPU-only.
- Unified Memory means the model lives in RAM shared with GPU/ANE — no data transfer bottleneck.
- Model is cached in `~/.cache/huggingface/` after first download (~270MB).

### Lazy Loading

The encoder is instantiated lazily on first use to avoid a ~3s model load penalty for commands that do not require semantic matching (e.g., `classify` when the rules engine matches).

### Progressive Truncation for Dense Content

Technical documents, source code, and symbol-dense PDFs exceed embedding limits. A 4-level retry strategy was implemented:

```
Full text → 700 chars → 400 chars → 200 chars → 100 chars
```

This ensures real embeddings instead of zero-vectors for hard-to-encode content.

## Consequences

- `mlx>=0.30.1` and `mlx-embedding-models>=0.0.11` are required dependencies.
- The `MLXEncoder` class wraps `mlx-embedding-models` to implement the `semantic-router` `BaseEncoder` interface.
- Model download is required on first run (~270MB) — documented in the getting-started guide.
- Embeddings are not cached between runs — each classification re-encodes the content preview.
- The `score_threshold` config default of `0.75` was empirically tuned; users can lower it to increase recall or raise it to improve precision.
