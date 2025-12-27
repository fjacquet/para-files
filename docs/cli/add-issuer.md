---
title: add-issuer Command
layout: default
parent: CLI Reference
nav_order: 9
---

# add-issuer Command

Register a new company or bank to improve classification.

## Basic Usage

```bash
# Add an issuer to a category
uv run para-files add-issuer "Company Name" -c category

# Example: Add a bank
uv run para-files add-issuer "My Bank SA" -c banques

# Example: Add a telecom company
uv run para-files add-issuer "Mobile Provider" -c telecom
```

## Options

### `-c, --category CATEGORY` (Required)
Which category does this issuer belong to:

```bash
uv run para-files add-issuer "Company" -c banques
uv run para-files add-issuer "Company" -c telecom
uv run para-files add-issuer "Company" -c utilities
uv run para-files add-issuer "Company" -c assurances
```

## Common Categories

- `banques` - Banks
- `telecom` - Telecommunications companies
- `utilities` - Electricity, water, gas
- `assurances` - Insurance companies
- `cloud` - Cloud service providers
- Other custom categories defined in your tree

## Examples

### Add a Bank

```bash
uv run para-files add-issuer "UBS Switzerland" -c banques

# Now documents from UBS match with 90% confidence (Domain KB signal)
```

### Add a Telecom Company

```bash
uv run para-files add-issuer "Swisscom" -c telecom

# Future Swisscom invoices are classified automatically
```

### Add Multiple Issuers

```bash
# Add different issuers
uv run para-files add-issuer "EDF Energy" -c utilities
uv run para-files add-issuer "Netflix" -c cloud
uv run para-files add-issuer "Helvetia Insurance" -c assurances
```

## How It Works

When you add an issuer:

1. **Stores** the issuer → category mapping
2. **Updates** your reference tree
3. **Enables** automatic matching (90% confidence)

Next time para-files sees a document from that issuer (via email sender, filename, content), it matches automatically without needing semantic analysis.

## When to Use

**Add an issuer when:**
- You get regular documents from a company
- You want faster classification (90% vs 85%)
- You want reliable, consistent routing

**Don't add when:**
- It's a one-time document
- The company name is very generic

## Finding Issuer Names

```bash
# Look at misclassified files:
uv run para-files learn problematic_file.pdf

# When asked about the issuer, add it:
uv run para-files add-issuer "Company Name" -c category
```

## See What You've Added

```bash
# List all issuers by category
uv run para-files issuers

# Shows everything you've registered
```

## Related Commands

- **[issuers](issuers.md)** - List all registered issuers
- **[learn](learn.md)** - Interactively classify and add issuers
- **[add-utterance](add-utterance.md)** - Add semantic matching keywords
- **[Task: Manage Issuers](../tasks/manage-issuers.md)** - Full guide
