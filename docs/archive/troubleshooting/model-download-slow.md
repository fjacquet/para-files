---
title: MLX Model Download Slow
layout: default
parent: Troubleshooting
nav_order: 3
---

# MLX Model Download Is Slow

First classification takes time because MLX model is downloading.

## What's Happening

On first use, para-files downloads the embedding model (~100MB) from Hugging Face:

```
First classification:  30-60 seconds (downloads + loads model)
Second classification: <1 second (cached)
```

This is normal behavior.

## Speed It Up

### Check Download Progress

```bash
# First classification (shows download)
uv run para-files classify test.pdf

# Watch ~/Library/Caches/huggingface/ directory
ls -lah ~/Library/Caches/huggingface/

# Should see nomic-embed-text-v1.5
```

### Pre-Download the Model

If you want to download before using:

```python
# Pre-download programmatically
from para_files.encoders import MLXEncoder

encoder = MLXEncoder()
# This loads/downloads the model

# Now first classification will be fast
```

Or just run classify once and let it download.

### Network Issues

If download is very slow:

```bash
# Check internet connection
ping huggingface.co

# Try again later
uv run para-files classify test.pdf
```

## After First Time

Once downloaded and cached:

- **Classification**: <1 second
- **Batch of 100 files**: ~2-3 minutes
- **Model size**: ~100MB (one-time)

Cache location: `~/.cache/huggingface/` (~100MB permanent)

## Offline Use

Model works offline after first download. No network needed for subsequent classifications.

## Related

- **[Configuration](../configuration/mlx-model.md)** - Model settings
- **[Architecture: Semantic Router](../architecture/signal-4-semantic.md)** - How model works
