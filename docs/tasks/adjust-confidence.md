---
title: Adjust Confidence Threshold
layout: default
parent: Tasks
nav_order: 12
---

# Adjust Confidence Threshold

Configure how sensitive semantic matching is.

## What Is the Threshold?

The minimum confidence score (0.0-1.0) for semantic matching to accept a classification.

Default: `0.75` (75%)

## Change Threshold

```bash
# Lower threshold (more matches)
export PARA_FILES_MLX_SCORE_THRESHOLD=0.70

# Higher threshold (fewer matches)
export PARA_FILES_MLX_SCORE_THRESHOLD=0.85

# Or in .env:
PARA_FILES_MLX_SCORE_THRESHOLD=0.80
```

## When to Adjust

### Too Many Files Going to Inbox?

Files not matching any route → Lower threshold:

```bash
export PARA_FILES_MLX_SCORE_THRESHOLD=0.70
```

This accepts matches with 70% confidence instead of 75%.

### Too Many Misclassifications?

Files matching wrong routes → Raise threshold:

```bash
export PARA_FILES_MLX_SCORE_THRESHOLD=0.85
```

Only accepts very confident matches.

## Testing

```bash
# Set new threshold
export PARA_FILES_MLX_SCORE_THRESHOLD=0.80

# Test classification
uv run para-files classify problematic_file.pdf

# See if it improves
```

## Recommended Values

| Value | Behavior |
|-------|----------|
| 0.65 | Lenient (more matches, more errors) |
| 0.70 | Permissive (good coverage) |
| 0.75 | Balanced (default, recommended) |
| 0.80 | Strict (fewer errors, more misses) |
| 0.85 | Very strict (only certain matches) |

## Better Alternative

Instead of changing threshold, consider:
- Adding utterances to routes
- Registering issuers
- Using interactive learning

These improve accuracy without lowering confidence.

## Related

- **[Configuration](../configuration/mlx-model.md)** - Threshold details
- **[Improve Matching](improve-matching.md)** - Add utterances
- **[Troubleshooting](../troubleshooting/confidence-too-low.md)** - Low confidence issues
