---
title: Improve Semantic Matching
layout: default
parent: Tasks
nav_order: 7
---

# Improve Semantic Matching with Utterances

Add keywords to improve how para-files matches documents.

## What Are Utterances?

Utterances are phrases that describe what a document is about. They help with **semantic matching** (Signal 4).

Example:

- Route `factures-utilities`
- Utterance: `"electricity bill"`
- Matches: Documents about electricity

## Add Utterances

```bash
uv run para-files add-utterance factures-utilities "electricity bill"
uv run para-files add-utterance factures-utilities "power usage"
uv run para-files add-utterance factures-utilities "energy invoice"
```

Now documents with similar content match this route.

## Build Matching Keywords

For each route, add multiple utterances:

```bash
# Utilities
uv run para-files add-utterance factures-utilities "electricity bill"
uv run para-files add-utterance factures-utilities "water consumption"
uv run para-files add-utterance factures-utilities "gas invoice"

# Telecom
uv run para-files add-utterance factures-telecom "mobile invoice"
uv run para-files add-utterance factures-telecom "internet billing"

# Cloud
uv run para-files add-utterance factures-cloud "AWS invoice"
uv run para-files add-utterance factures-cloud "cloud storage billing"
```

## See Current Utterances

```bash
uv run para-files routes --utterances

# Shows all utterances you've added
```

## Best Practices

### Use Descriptive Phrases

Good:

```bash
uv run para-files add-utterance route "electricity monthly bill"
uv run para-files add-utterance route "power consumption statement"
```

Avoid:

```bash
uv run para-files add-utterance route "bill"  # Too generic
uv run para-files add-utterance route "electricity"  # Single word
```

### Add Variations

Different ways to describe the same thing:

```bash
uv run para-files add-utterance route "electricity invoice"
uv run para-files add-utterance route "power bill"
uv run para-files add-utterance route "electric utility statement"
```

### Build Over Time

```bash
# As you use the system, add utterances
# for documents that don't match well
uv run para-files learn unclear_document.pdf

# If it's right category but low confidence:
# Add an utterance describing it
```

## When Utterances Help

Use utterances when:

- Documents are from unknown companies
- Filenames are generic (`invoice.pdf`)
- You need content-based matching
- No issuer is registered

## Examples

### New Route? Build Utterances

```bash
# Creating new route for cloud services
uv run para-files add-utterance factures-cloud "AWS"
uv run para-files add-utterance factures-cloud "Google Cloud"
uv run para-files add-utterance factures-cloud "cloud billing"
uv run para-files add-utterance factures-cloud "storage subscription"
```

### Improve Existing Route

```bash
# Route not matching well?
uv run para-files add-utterance route "more specific description"
```

## Related

- **[add-utterance Command](../cli/add-utterance.md)** - Full reference
- **[Semantic Router](../architecture/signal-4-semantic.md)** - How it works
- **[Manage Issuers](manage-issuers.md)** - 90% confidence alternative
