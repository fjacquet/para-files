---
title: Learn from Files
layout: default
parent: Tasks
nav_order: 6
---

# Learn from Files Interactively

Improve classification accuracy by learning from misclassifications.

## Basic Learning

```bash
# Learn from one file
uv run para-files learn document.pdf

# Learn from multiple
uv run para-files learn file1.pdf file2.docx
```

## The Learn Workflow

```bash
uv run para-files learn invoice.pdf

# Output:
# File: invoice.pdf
# Suggested: 4_Archives/factures/utilities
# Confidence: 75% (Semantic Router)
# 
# Is this correct? (y/n): _
```

**Press `y`** if correct → Nothing changes (accepted)
**Press `n`** if wrong → System asks you to correct it

## Correcting a Misclassification

```bash
uv run para-files learn wrong_file.pdf

# System shows it matched wrong category
# Is this correct? (y/n): n

# What should it be?
# Type route name: factures-cloud

# Any keywords to add? 
# (e.g., "AWS invoice"): AWS billing monthly statement
```

Para-files now learns:

- This file goes to `factures-cloud`
- Files matching "AWS billing monthly statement" go to that category

## Building Knowledge

```bash
# Learn from 10-20 files regularly
for file in ~/Downloads/*.pdf; do
  uv run para-files learn "$file"
done

# Your personalized knowledge grows
```

## When to Learn

**Learn when:**

- File went to wrong category
- Classification confidence is low
- You're training the system
- You want to improve accuracy

**Don't need to learn when:**

- Classification is correct
- Confidence is high

## Benefits

As you learn from files:

- **Validated DB grows** - 100% confidence for approved mappings
- **Utterances improve** - Better semantic matching
- **Issuers register** - Fast Domain KB matching
- **System adapts** - To your specific documents

## Examples

### Improve Over Time

```bash
# Week 1: Learn from 20 files
for file in ~/Downloads/*.pdf; do
  uv run para-files learn "$file"
done

# Week 2: Classification is much better
# Files are classified correctly with high confidence

# Week 3: System is fully trained on your documents
```

### Fix Systematic Errors

```bash
# If utilities invoices keep getting wrong category:
uv run para-files learn utilities_invoice.pdf

# Correct it and add keywords
# All future utilities invoices match better
```

## Related Commands

- **[add-issuer](../cli/add-issuer.md)** - Register companies
- **[add-utterance](../cli/add-utterance.md)** - Add keywords
- **[learn Command](../cli/learn.md)** - Full reference
