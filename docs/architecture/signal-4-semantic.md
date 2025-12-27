---
title: Signal 4 - Semantic Router (MLX Embeddings)
layout: default
parent: Architecture
nav_order: 5
---

# Signal 4: Semantic Router with MLX Embeddings

How para-files matches documents to categories using AI embeddings.

## How It Works

1. **Extract content** from document (first 2000 characters)
2. **Convert to embedding** - 768-dimensional vector via MLX
3. **Compare to utterances** - Each route has utterance embeddings
4. **Calculate similarity** - Cosine similarity score (0.0-1.0)
5. **Match if above threshold** - Default: 0.75

```
Document: "electricity invoice from EDF"
    ↓ Embed (768 dims)
    ↓ Compare to utterances: ["electricity bill", "power usage", ...]
    ↓ Cosine similarity = 0.87
    ↓ Above threshold (0.75)? YES
    ↓ Match: factures-utilities (85% confidence)
```

## The MLX Model

**Model**: `nomic-embed-text-v1.5` (default)

**Why this model?**
- Optimized for Apple Neural Engine (MLX)
- Small (~100MB)
- Fast (10-15ms)
- Good quality (768 dimensions)
- 8192 token context

**Download**: Automatic on first use, cached in `~/.cache/huggingface/`

## Utterances Are Key

Routes have utterances (semantic keywords):

```yaml
routes:
  - name: factures-utilities
    path: "4_Archives/factures/_Utilities"
    utterances:
      - "electricity bill"
      - "power usage"
      - "energy invoice"
      - "water consumption"
```

When you add utterances:

```bash
uv run para-files add-utterance factures-utilities "electrical consumption"
```

It learns to match documents about electricity better.

## Similarity Scoring

Cosine similarity ranges from 0.0 to 1.0:

| Score | Meaning |
|-------|---------|
| 0.95+ | Excellent match |
| 0.85-0.95 | Good match |
| 0.75-0.85 | Acceptable match |
| <0.75 | Poor match (rejected) |

Default threshold: `0.75`

## Configuring Semantic Matching

### Adjust Sensitivity

```bash
# Lower = more matches, more false positives
export PARA_FILES_MLX_SCORE_THRESHOLD=0.70

# Higher = fewer matches, more to Inbox
export PARA_FILES_MLX_SCORE_THRESHOLD=0.85
```

### Add Better Utterances

```bash
# Instead of lowering threshold, add utterances
uv run para-files add-utterance route "more specific phrase"
```

## Performance

- **First classification**: ~30 seconds (model downloads + loads)
- **Model embedding**: ~10-15ms
- **Subsequent classifications**: <1 second total

Model loads once and stays in memory.

## Advantages

✓ Works without manual training
✓ Fast inference (ML on Apple Silicon)
✓ Deterministic (same input = same output)
✓ Works with any language
✓ Content-based (doesn't need company name)

## Limitations

✗ Needs good utterances
✗ Generic documents may not match
✗ Needs 2000+ char content to work well
✗ Doesn't understand domain context

## Related

- **[Signal 3: Domain KB](signal-3-domain-kb.md)** - Known companies (90%)
- **[Improve Matching](../tasks/improve-matching.md)** - Add utterances
- **[Configuration](../configuration/mlx-model.md)** - Model settings
