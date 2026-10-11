---
title: Classify a Single File
layout: default
parent: Tasks
nav_order: 2
---

# Classify a Single File

Determine the category for one file without moving it.

## Basic Classification

```bash
# Classify a file
uv run para-files classify document.pdf

# Output:
# File: document.pdf
# Category: 4_Archives/factures/2024
# Confidence: 85% (Semantic Router)
```

## Understand the Output

- **File**: The document you classified
- **Category**: Where it would be placed in PARA
- **Confidence**: How sure (higher = more certain)
- **Signal**: Which classification method was used

## View More Details

```bash
# Show how each signal performed
uv run para-files classify document.pdf -v

# Output as JSON for processing
uv run para-files classify document.pdf --json
```

## Confidence Levels

| Confidence | Signal | Meaning |
|-----------|--------|---------|
| 100% | Validated DB | You approved this before |
| 95% | Rules Engine | Matches filename pattern |
| 92% | Book Detector | Technical book detected |
| 90% | Domain KB | Matches known company |
| 85% | Semantic Router | Matches via embeddings |
| Variable | LLM Fallback | AI classification |

## What NOT to Do

This command **does not move** the file. It only shows the classification.

To actually move: Use `uv run para-files move`

## Examples

### Single File

```bash
uv run para-files classify invoice.pdf
```

### Multiple Files

```bash
uv run para-files classify *.pdf
uv run para-files classify file1.pdf file2.docx file3.txt
```

### Verbose Output

```bash
# See detailed matching info
uv run para-files classify confusing_file.pdf -v

# See which signals matched/didn't match
```

### JSON Output

```bash
# Process results programmatically
uv run para-files classify document.pdf --json
```

## Next Steps

- **[Move Files](move-files.md)** - Actually move classified files
- **[Batch Classify](batch-classify.md)** - Classify multiple files
- **[Troubleshooting](../troubleshooting/files-going-to-inbox.md)** - Wrong classifications

## See Also

- **[classify Command Reference](../cli/classify.md)** - Full command details
