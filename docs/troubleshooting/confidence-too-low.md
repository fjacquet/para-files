---
title: Confidence Too Low
layout: default
parent: Troubleshooting
nav_order: 2
---

# Confidence Scores Too Low

Files match but confidence is below threshold (default 0.75).

## What This Means

Files are being classified but with <75% confidence.

Example:
```
Category: 4_Archives/factures/utilities
Confidence: 65% (Semantic Router)
```

Since 65% < 75%, it's rejected and goes to Inbox.

## Solutions

### 1. Add Better Utterances

```bash
# For the correct route, add more specific phrases
uv run para-files add-utterance factures-utilities "monthly power bill"
uv run para-files add-utterance factures-utilities "electricity consumption statement"

# Re-test
uv run para-files classify problem-file.pdf
```

### 2. Register the Issuer

```bash
# If from known company
uv run para-files add-issuer "Energy Company" -c utilities

# Now matches with 90% confidence automatically
uv run para-files classify invoice.pdf
```

### 3. Lower Threshold Slightly

```bash
# If utterances/issuers don't help
export PARA_FILES_MLX_SCORE_THRESHOLD=0.70

# Test
uv run para-files classify problem-file.pdf
```

**Note:** Better to improve utterances than lower threshold.

## Debugging

See why confidence is low:

```bash
# Test against the route
uv run para-files test-route expected-route --file problem-file.pdf -v

# Shows similarity calculation details

# Check utterances
uv run para-files routes --utterances
```

## Best Approach

Order by effectiveness:

1. **Register issuer** (if known company) → 90% confidence
2. **Add utterances** (specific phrases) → Usually 80%+ confidence
3. **Lower threshold** (only if needed) → Risk of errors
4. **Use learning** (interactive) → Build training data

## Prevention

- Add 5-10 utterances per route
- Register all known senders
- Test before moving many files

## Related

- **[Adjust Confidence](../tasks/adjust-confidence.md)** - Threshold details
- **[Improve Matching](../tasks/improve-matching.md)** - Add utterances
- **[Manage Issuers](../tasks/manage-issuers.md)** - Register companies
