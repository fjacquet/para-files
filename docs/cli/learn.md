---
title: learn Command
layout: default
parent: CLI Reference
nav_order: 5
---

# learn Command

Interactively improve classifications by learning from files.

## Basic Usage

```bash
# Learn from single file
uv run para-files learn document.pdf

# Learn from multiple files
uv run para-files learn file1.pdf file2.docx
```

## What learn Does

For each file:

1. **Classifies** it using the current pipeline
2. **Shows** the suggested category and confidence
3. **Asks** if the classification is correct
4. **Optionally adds** new knowledge to improve future matches

## Workflow

```bash
uv run para-files learn invoice.pdf
```

Output:

```
File: invoice.pdf
Suggested: 4_Archives/factures/2024/utilities
Confidence: 75% (Semantic Router)

Is this correct? (y/n): _
```

**If you answer `y` (yes):**

- Nothing changes (system learns to accept this)

**If you answer `n` (no):**

```
What should it be categorized as?
Type route name (e.g., factures-utilities): factures-electricity
```

Then system asks:

```
Add any keywords to improve future matching?
(e.g., "electricity bill", "power consumption"):
```

You can add:

- Issuer name: "EDF Energy"
- File type: "electricity invoice"
- Anything that helps future matching

## Options

### `-v, --verbose`

Show detailed matching information:

```bash
uv run para-files learn document.pdf -v
```

### `-r, --reference-tree`

Use custom reference tree:

```bash
uv run para-files learn document.pdf -r custom_tree.yaml
```

## Examples

### Learn from One File

```bash
uv run para-files learn problematic_file.pdf

# Correct it and add keywords for future files
```

### Batch Learning

```bash
# Interactively learn from all PDFs
for file in ~/Downloads/*.pdf; do
  uv run para-files learn "$file"
done
```

### With Verbose Output

```bash
# See detailed matching info while learning
uv run para-files learn invoice.pdf -v
```

## How Learning Works

When you correct a classification, para-files:

1. **Stores** the correct mapping in its database
2. **Suggests improvements** to your reference tree
3. **Learns** new keywords (utterances) for semantic matching

Over time, learning improves accuracy for:

- Your specific issuers (banks, companies)
- Your specific document types
- Your specific preferences

## Best Practices

### Learn from Misclassifications

If a file goes to the wrong category, use learn to correct it:

```bash
uv run para-files learn wrong_file.pdf

# Correct it to the right route
# Add keywords to prevent future mistakes
```

### Add Issuers While Learning

If you don't have an issuer registered:

```bash
# First learn from a file
uv run para-files learn bank_statement.pdf

# Then add issuer for next time
uv run para-files add-issuer "My Bank" -c banques
```

### Regular Improvement

Learn from 10-20 files regularly to:

- Build up your validated database
- Improve semantic matching
- Handle your specific document types

## Related Commands

- **[add-issuer](add-issuer.md)** - Register companies/banks permanently
- **[add-utterance](add-utterance.md)** - Improve semantic matching keywords
- **[classify](classify.md)** - Classify without learning
- **[Task Guide: Learn from Files](../tasks/learn-from-files.md)** - Full guide

## Troubleshooting

**"Route not found"?**
The route you entered doesn't exist in your reference tree. Use valid route names:

```bash
uv run para-files routes  # See all available routes
```

**Keys not being learned?**
Make sure your reference tree is writable and you have file permissions.
