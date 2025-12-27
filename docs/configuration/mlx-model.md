---
title: MLX Model Configuration
layout: default
parent: Configuration
nav_order: 5
---

# MLX Model Configuration

Configure the embedding model and confidence threshold for semantic matching.

## MLX_MODEL_NAME

The embedding model to use for semantic matching.

### Default

```
mlx-community/nomic-embed-text-v1.5
```

**Why this model?**

- Optimized for Apple Neural Engine
- 768-dimensional embeddings
- 8192 token context window
- ~100MB (cached after first download)
- 10-15ms inference time

### Set Model Name

```bash
# Environment variable (rare)
export PARA_FILES_MLX_MODEL_NAME=mlx-community/nomic-embed-text-v1.5

# .env file (not recommended to change)
PARA_FILES_MLX_MODEL_NAME=mlx-community/nomic-embed-text-v1.5

# YAML config (not recommended to change)
config:
  mlx:
    model_name: "mlx-community/nomic-embed-text-v1.5"
```

**Note:** You'll rarely need to change this. The default model is well-tested.

## MLX_SCORE_THRESHOLD

Minimum confidence score (0.0 to 1.0) for semantic matching to be accepted.

### Default

```
0.75
```

### How It Works

Para-files compares document embeddings to route utterances:

- Score 0.95 = Very similar
- Score 0.75 = Moderately similar (default minimum)
- Score 0.50 = Somewhat similar
- Score 0.25 = Vaguely similar

If score < threshold, matching continues to next signal or goes to Inbox.

### Adjust Threshold

```bash
# Environment variable
export PARA_FILES_MLX_SCORE_THRESHOLD=0.80

# .env file
PARA_FILES_MLX_SCORE_THRESHOLD=0.80

# YAML config
config:
  mlx:
    score_threshold: 0.80
```

## Understanding Threshold

### Lower Threshold (0.65)

```bash
export PARA_FILES_MLX_SCORE_THRESHOLD=0.65
```

**Pros:**

- More matches (fewer files to Inbox)
- Faster classification

**Cons:**

- More false positives (wrong category)
- May need more learning/correction

**When to use:**

- You have good utterances
- You prefer action over precision

### Higher Threshold (0.85)

```bash
export PARA_FILES_MLX_SCORE_THRESHOLD=0.85
```

**Pros:**

- More accurate (fewer misclassifications)
- High confidence matches only

**Cons:**

- More files go to Inbox
- Requires fallback signals (rules, issuers)

**When to use:**

- You need high accuracy
- You have other signals (issuers, rules)

### Balanced (0.75, Default)

Recommended for most users.

## Examples

### Stricter (Higher Accuracy)

```bash
# Only accept high-confidence matches
export PARA_FILES_MLX_SCORE_THRESHOLD=0.80

uv run para-files classify file.pdf
```

### Looser (More Coverage)

```bash
# Accept good-enough matches
export PARA_FILES_MLX_SCORE_THRESHOLD=0.70

uv run para-files classify file.pdf
```

## Troubleshooting

**Too many files going to Inbox?**

```bash
# Lower the threshold slightly
export PARA_FILES_MLX_SCORE_THRESHOLD=0.70

# Or improve utterances:
uv run para-files add-utterance route "better description"
```

**Too many misclassifications?**

```bash
# Raise the threshold
export PARA_FILES_MLX_SCORE_THRESHOLD=0.80

# Add more specific utterances
uv run para-files add-utterance route "specific phrase"
```

## Model Loading

The MLX model downloads automatically on first use:

```bash
# First classification (~30 seconds)
uv run para-files classify file.pdf
# Model downloads and caches (~100MB)

# Second classification (~1 second)
uv run para-files classify another_file.pdf
# Model already cached
```

Cache location: `~/.cache/huggingface/`

## Related

- **[Configuration Overview](overview.md)** - All configuration
- **[Semantic Router](../architecture/signal-4-semantic.md)** - How matching works
- **[Troubleshooting](../troubleshooting/confidence-too-low.md)** - Low confidence issues
