# ADR-010: Replace MLX with litellm/Ollama for Embeddings and LLM

**Date**: 2026-03-01
**Status**: Accepted
**Deciders**: Frederic Jacquet
**Supersedes**: [ADR-002](ADR-002-apple-silicon-only.md), [ADR-004](ADR-004-mlx-embeddings.md)

---

## Context

The classification pipeline previously depended on Apple Silicon-only MLX libraries for two capabilities:

1. **Embeddings** (`mlx-embedding-models` + `nomic-embed-text-v1.5`) used by SemanticClassifier
2. **LLM fallback** (`mlx-lm` + `Qwen2.5-1.5B-Instruct-4bit`) used by MLXLLMClassifier

Three problems emerged:

| Problem | Impact |
|---------|--------|
| 1.5B parameter LLM too small | Misclassifies tech docs as Swiss admin categories; most PDFs fall to `0_Inbox` |
| macOS-only platform lock | `mlx`, `mlx-lm`, `mlx-embedding-models` only work on Apple Silicon |
| Ollama already running locally | User already has `ministral-3:8b` (8B) and `nomic-embed-text` available |

## Decision

Replace both MLX dependencies with **litellm** calls to **Ollama**:

- `litellm.embedding(model="ollama/nomic-embed-text", ...)` for 768-dim embeddings (same model)
- `litellm.completion(model="ollama/ministral-3:8b", ...)` for LLM classification (5x larger)

## Rationale

### Same embedding quality, cross-platform

Ollama's `nomic-embed-text` produces identical 768-dimensional vectors. The semantic classifier's cosine similarity scores are unchanged.

### 5x larger LLM model

`ministral-3:8b` (8B parameters) vs `Qwen2.5-1.5B-Instruct-4bit` (1.5B). The larger model:

- Correctly classifies English tech docs to `3_Resources/documentation/{technology}`
- Distinguishes French admin categories (fiscalite, banques, assurances)
- Produces valid JSON output more reliably

### litellm as abstraction layer

litellm provides a unified interface to 100+ LLM providers. If the user switches from Ollama to OpenAI, Anthropic, or any other provider, only the model string and API key change.

### OCR remains macOS-only

Vision Framework OCR (via PyObjC) is still macOS-specific. This is acceptable because:

- OCR is optional (only used for scanned PDFs)
- No cross-platform OCR library matches Vision Framework quality on documents
- The core classification pipeline now works on any platform with Ollama

## Consequences

- `mlx`, `mlx-lm`, and `mlx-embedding-models` are removed from dependencies
- `litellm` (already a dependency) handles all LLM and embedding calls
- A running Ollama server is required for classification (previously ran in-process)
- Configuration moved from `PARA_FILES_MLX_LLM_*` to `PARA_FILES_LLM_*` env vars
- OCR features (`pyobjc-framework-vision`) remain macOS-only
- The `MLXEncoder` and `MLXLLMClassifier` names are preserved as backward-compat aliases
