---
title: Files Going to Inbox
layout: default
parent: Troubleshooting
nav_order: 1
---

# Files Going to Inbox

Why are files ending up in 0_Inbox/ instead of correct categories?

## Reasons for Inbox Classification

1. **No signals matched** - All 6 signals failed
2. **Low confidence** - Below threshold (default 0.75)
3. **Unrecognizable content** - Not enough text to match
4. **Ambiguous document** - Doesn't fit any route well

## Solutions

### 1. Add Utterances

Help semantic matching by adding keywords:

```bash
# What should this document match?
uv run para-files add-utterance correct-route "describe the document"

# Re-classify
uv run para-files classify problem-file.pdf
```

### 2. Register Issuer

If from a known company:

```bash
uv run para-files add-issuer "Company Name" -c category

# Now matches with 90% confidence
uv run para-files classify document.pdf
```

### 3. Use Interactive Learning

```bash
uv run para-files learn wrong-file.pdf

# Correct the classification
# Add keywords for future files
```

### 4. Add Confidence to Routes

Check if utterances are too weak:

```bash
# View current utterances
uv run para-files routes --utterances

# Add more specific ones
uv run para-files add-utterance route "very specific phrase"
```

### 5. Lower Threshold (Last Resort)

```bash
export PARA_FILES_MLX_SCORE_THRESHOLD=0.70

# Only if other methods don't work
# Better to improve utterances instead
```

## Debugging

See why a file went to Inbox:

```bash
# Verbose output shows all signals tried
uv run para-files classify problem-file.pdf -v

# Check confidence for specific route
uv run para-files test-route expected-route --file problem-file.pdf

# See what utterances exist
uv run para-files routes --utterances
```

## Common Causes

**Generic filename** (invoice.pdf)
→ Add content-based utterances

**Unknown company**
→ Register as issuer or add utterances

**Too few characters**
→ Ensure 2000+ chars readable (try `-v` flag)

**Empty or binary file**
→ Can't extract content, needs manual categorization

## Prevention

- Add utterances for each route before moving many files
- Register known issuers early
- Use `learn` regularly to build training data

## Related

- **[Improve Matching](../tasks/improve-matching.md)** - Add utterances
- **[Manage Issuers](../tasks/manage-issuers.md)** - Register companies
- **[Learn from Files](../tasks/learn-from-files.md)** - Interactive training
