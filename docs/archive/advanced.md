---
title: Advanced
layout: default
nav_order: 8
has_children: true
---

# Advanced Usage

Advanced topics for power users and developers.

## Topics

| Topic | Description |
|-------|-------------|
| [Programmatic Usage](advanced/programmatic-usage.md) | Use para-files as a Python library |

## Python API Example

```python
from para_files.pipeline import ClassificationPipeline
from para_files.config import load_config

# Load configuration
config = load_config()

# Create pipeline
pipeline = ClassificationPipeline(config)

# Classify a file
result = pipeline.classify("/path/to/document.pdf")
print(f"Category: {result.category}")
print(f"Confidence: {result.confidence}")
print(f"Signal: {result.signal_name}")
```

## Extending para-files

para-files is designed to be extensible:

- **Custom signals**: Add your own classification signals to the pipeline
- **Custom encoders**: Implement alternative embedding models
- **Webhooks**: Trigger actions on classification events

See the [Developer Guide](../CLAUDE.md) for contribution guidelines.
