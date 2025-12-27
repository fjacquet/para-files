---
title: add-utterance Command
layout: default
parent: CLI Reference
nav_order: 10
---

# add-utterance Command

Add semantic matching keywords to improve classification accuracy.

## Basic Usage

```bash
# Add an utterance to a route
uv run para-files add-utterance route-name "description of what this is about"

# Example
uv run para-files add-utterance factures-utilities "electricity bill"
uv run para-files add-utterance factures-telecom "mobile phone invoice"
```

## What Are Utterances?

Utterances are keywords and phrases that help para-files match documents via **semantic matching** (MLX embeddings).

When you add an utterance:

- `"electricity bill"` → factures-utilities
- `"water consumption invoice"` → factures-utilities
- `"mobile plan"` → factures-telecom

Para-files converts these to embeddings and matches new documents by semantic similarity.

## Examples

### Add Utterances for Utilities

```bash
uv run para-files add-utterance factures-utilities "electricity bill"
uv run para-files add-utterance factures-utilities "water consumption"
uv run para-files add-utterance factures-utilities "gas invoice"
uv run para-files add-utterance factures-utilities "power usage"
```

### Add Utterances for Telecom

```bash
uv run para-files add-utterance factures-telecom "mobile phone invoice"
uv run para-files add-utterance factures-telecom "internet billing"
uv run para-files add-utterance factures-telecom "phone plan"
```

### Add Utterances for Cloud Services

```bash
uv run para-files add-utterance factures-cloud "AWS invoice"
uv run para-files add-utterance factures-cloud "Google Cloud billing"
uv run para-files add-utterance factures-cloud "cloud storage"
```

## Best Practices

### Use Descriptive Phrases

Good:

- `"electricity invoice"` ✓
- `"power consumption bill"` ✓
- `"water usage statement"` ✓

Avoid:

- Too generic: `"bill"` ✗
- Too specific: `"Invoice from EDF Energy dated 2024-01-15"` ✗
- Single words: `"electricity"` (usually okay but phrases better) ✓

### Add Multiple Variations

```bash
# Different ways to describe the same thing
uv run para-files add-utterance factures-utilities "electricity invoice"
uv run para-files add-utterance factures-utilities "power bill"
uv run para-files add-utterance factures-utilities "electric usage statement"
```

### Build Over Time

```bash
# As you classify files, add utterances for common documents
uv run para-files learn document.pdf
# > Add utterance? "cloud storage monthly billing"
```

## When Utterances Help

Utterances work best when:

- Document filenames are generic (`invoice.pdf`)
- No known issuer registered yet
- Content-based matching is needed

Example: An electricity bill from an unknown company. Utterances help match it correctly even without knowing the company.

## See Current Utterances

```bash
# View all utterances for routes
uv run para-files routes --utterances

# Shows what you've added so far
```

## Related Commands

- **[routes](routes.md)** - See current utterances
- **[add-issuer](add-issuer.md)** - Register companies/banks
- **[learn](learn.md)** - Interactively add utterances
- **[task: Improve Matching](../tasks/improve-matching.md)** - Full guide
