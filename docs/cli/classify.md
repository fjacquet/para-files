---
title: classify Command
layout: default
parent: CLI Reference
nav_order: 2
---

# classify Command

Determine the category for one or more files without moving them.

## Basic Usage

```bash
# Single file
uv run para-files classify document.pdf

# Multiple files
uv run para-files classify file1.pdf file2.docx file3.txt

# All PDFs in Downloads
uv run para-files classify ~/Downloads/*.pdf
```

## Output

```
File: document.pdf
Category: 4_Archives/factures/2024/utilities
Confidence: 90% (Domain KB)
```

Shows:

- **File**: Input filename
- **Category**: Suggested PARA path
- **Confidence**: How sure (90%) and which signal matched (Domain KB)

## Options

### `-v, --verbose`

Show detailed matching information:

```bash
uv run para-files classify document.pdf -v

# Shows: which signals were tried, why they matched/didn't match, etc.
```

### `--json`

Output as JSON (useful for scripts):

```bash
uv run para-files classify document.pdf --json

# Output:
# {
#   "file": "document.pdf",
#   "category": "4_Archives/factures/2024/utilities",
#   "confidence": {
#     "value": 0.90,
#     "source": "Domain KB"
#   }
# }
```

### `-r, --reference-tree PATH`

Use a custom YAML reference tree:

```bash
uv run para-files classify document.pdf -r /path/to/custom_tree.yaml
```

## Examples

### Classify Multiple Files

```bash
# All PDFs
uv run para-files classify ~/Downloads/*.pdf

# All documents
uv run para-files classify ~/Downloads/*.{pdf,docx,xlsx}

# Show results as JSON
uv run para-files classify *.pdf --json > results.json
```

### Verbose Output

```bash
# See why each signal did or didn't match
uv run para-files classify confusing_file.pdf -v
```

### Batch Processing

```bash
# Process many files and capture output
for file in ~/Downloads/*.pdf; do
  uv run para-files classify "$file" --json >> classifications.json
done
```

## Confidence Levels

| Level | Source | Description |
|-------|--------|-------------|
| 100% | Validated DB | Previously approved by you |
| 95% | Rules Engine | Matches filename/path pattern |
| 92% | Book Detector | Identified as a technical book |
| 90% | Domain KB | Matches known issuer (bank, company) |
| 85% | Semantic Router | ML embedding match |
| Variable | LLM Fallback | AI classification (if enabled) |

Higher confidence = more certain.

## What Classify Does

1. **Analyzes** the file (name, type, content)
2. **Runs 6 signals** in priority order
3. **Returns** the first confident match
4. **Does NOT move** the file

## Next Steps

- **[move](move.md)** - Actually move files to PARA folders
- **[scan](scan.md)** - Preview classifications for directory
- **[Troubleshooting](../troubleshooting/files-going-to-inbox.md)** - Wrong categories
