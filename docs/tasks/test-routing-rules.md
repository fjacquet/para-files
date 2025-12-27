---
title: Test Routing Rules
layout: default
parent: Tasks
nav_order: 11
---

# Test Routing Rules and Debug Routes

Test and debug why files are matching specific routes.

## Test a Route

```bash
# Show route details
uv run para-files test-route factures-utilities

# Shows:
# - Route path
# - All utterances
# - Configuration
```

## Test File Against Route

```bash
# Does this file match this route?
uv run para-files test-route factures-utilities --file invoice.pdf

# Shows:
# - Does it match?
# - Confidence score
# - Why/why not
```

## Verbose Debugging

```bash
# See detailed matching info
uv run para-files test-route factures-utilities --file invoice.pdf -v

# Shows how semantic similarity is calculated
```

## Debugging Workflow

File going to wrong route?

```bash
# 1. Classify to see which route it matched
uv run para-files classify problematic_file.pdf

# 2. Test against expected route
uv run para-files test-route expected-route --file problematic_file.pdf

# 3. Check confidence - maybe too low

# 4. Add utterances to improve matching
uv run para-files add-utterance expected-route "better description"

# 5. Test again
uv run para-files test-route expected-route --file problematic_file.pdf
```

## Examples

### Debug Low Confidence

```bash
# File matching with 70% confidence (below threshold)
uv run para-files test-route my-route --file invoice.pdf -v

# Shows why similarity is only 70%
# Add utterances to improve

uv run para-files add-utterance my-route "more specific keywords"
uv run para-files test-route my-route --file invoice.pdf
# Now 85% confidence!
```

### Test New Route

```bash
# Created new custom route?
uv run para-files test-route new-route

# Check it's configured correctly

uv run para-files test-route new-route --file sample_file.pdf
# Test if files match it
```

## Related

- **[test-route Command](../cli/test-route.md)** - Full reference
- **[improve-matching](improve-matching.md)** - Add utterances
- **[Troubleshooting](../troubleshooting/files-going-to-inbox.md)** - Wrong routes
