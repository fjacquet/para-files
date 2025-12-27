---
title: Manage Issuers (Companies/Banks)
layout: default
parent: Tasks
nav_order: 5
---

# Manage Issuers

Register companies and banks to improve classification accuracy.

## What Is an Issuer?

An issuer is a known sender of documents:

- Banks (UBS, Credit Suisse)
- Telecom companies (Swisscom, Sunrise)
- Utilities (electricity, water, gas)
- Insurance companies
- Any regular sender

Registering an issuer enables **Domain KB matching** (90% confidence).

## Add an Issuer

```bash
# Register a bank
uv run para-files add-issuer "My Bank" -c banques

# Register a telecom company
uv run para-files add-issuer "My Telecom" -c telecom

# Register utility company
uv run para-files add-issuer "Energy Company" -c utilities
```

## Common Categories

```bash
-c banques      # Banks
-c telecom      # Telecom providers
-c utilities    # Electricity, water, gas
-c assurances   # Insurance
-c cloud        # Cloud services (AWS, Google, etc.)
```

See your actual categories:

```bash
uv run para-files issuers
```

## How It Works

After registering an issuer, para-files matches via:

- Email sender domain: `invoice@mybank.com` → Your Bank
- Company name in filename: `Invoice_MyBank.pdf`
- Subject line: "Your Bank statement"

**Confidence: 90%** (higher than semantic matching)

## Examples

### Register Common Issuers

```bash
# Banks
uv run para-files add-issuer "UBS Switzerland" -c banques
uv run para-files add-issuer "Credit Suisse" -c banques

# Telecom
uv run para-files add-issuer "Swisscom" -c telecom
uv run para-files add-issuer "Sunrise" -c telecom

# Utilities
uv run para-files add-issuer "EDF Energy" -c utilities
uv run para-files add-issuer "Water Company" -c utilities
```

### Build Over Time

```bash
# As you classify files, add issuers
uv run para-files learn invoice.pdf

# When asked about issuer, add it:
uv run para-files add-issuer "New Company" -c category
```

## View All Issuers

```bash
# List registered issuers
uv run para-files issuers

# Shows all by category
```

## Test After Adding

```bash
# Test if issuer matching works
uv run para-files classify document_from_new_issuer.pdf

# Should show 90% confidence from Domain KB
```

## When to Add Issuers

**Add issuer when:**

- You get regular documents from this sender
- You want reliable, fast matching
- You want consistency

**Don't need to add when:**

- One-time document
- Very generic name
- Already have good utterances

## Next Steps

- **[Add Utterances](../cli/add-utterance.md)** - Improve semantic matching
- **[Learn from Files](learn-from-files.md)** - Interactive improvement
- **[add-issuer Command](../cli/add-issuer.md)** - Full reference
