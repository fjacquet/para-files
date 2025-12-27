---
title: Programmatic Usage (Python API)
layout: default
parent: Advanced
nav_order: 1
---

# Using para-files as a Python Library

Integrate para-files classification into your Python code.

## Basic Classification

```python
from pathlib import Path
from para_files.config import load_config
from para_files.pipeline import ClassificationPipeline

# Load configuration
config = load_config()

# Create pipeline
pipeline = ClassificationPipeline(config)

# Classify a file
result = pipeline.classify_file(Path("document.pdf"))

print(f"Category: {result.category}")
print(f"Confidence: {result.confidence.value:.0%}")
print(f"Source: {result.confidence.source.value}")
```

## Moving Files Programmatically

```python
from para_files.mover import FileMover

mover = FileMover(config)
result = mover.move_file(
    src=Path("document.pdf"),
    conflict="rename"
)

print(f"Moved to: {result.destination}")
```

## Classification Result

```python
result = pipeline.classify_file(Path("file.pdf"))

# Attributes:
result.category        # str: "4_Archives/factures/utilities"
result.confidence.value  # float: 0.85
result.confidence.source  # str: "Semantic Router"
result.file_path       # Path: original file
```

## Loading Custom Config

```python
from para_files.config import load_config

# Explicit values
config = load_config(
    para_root=Path("~/Documents/PARA"),
    reference_tree_path=Path("config/personal_file_tree.yaml"),
    mlx_score_threshold=0.80,
)

# Or from environment
config = load_config()  # Reads PARA_FILES_* variables
```

## Batch Processing

```python
from pathlib import Path

files = list(Path("~/Downloads").glob("*.pdf"))

for file in files:
    result = pipeline.classify_file(file)
    print(f"{file.name} → {result.category}")
```

## Error Handling

```python
from para_files.exceptions import ParaFilesError

try:
    result = pipeline.classify_file(Path("file.pdf"))
except ParaFilesError as e:
    print(f"Classification failed: {e}")
```

## Related

- **[Configuration](../configuration/overview.md)** - Config programmatically
- **[Architecture](overview.md)** - How classification works
