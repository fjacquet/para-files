---
title: issuers Command
layout: default
parent: CLI Reference
nav_order: 8
---

# issuers Command

List all known issuers (companies, banks, etc.) by category.

## Basic Usage

```bash
# List all issuers
uv run para-files issuers
```

## Output

```
Issuers by category:

banques (Banks):
  - UBS Switzerland
  - Credit Suisse
  - BCGE
  - Raiffeisen

telecom (Telecom):
  - Swisscom
  - Sunrise
  - Salt

utilities (Utilities):
  - Genève Energy
  - SIG (Water)

assurances (Insurance):
  - CSS Insurance
  - Helvetia

cloud (Cloud Services):
  - AWS
  - Google Cloud
  - Azure
```

## Understanding Issuers

An "issuer" is a known company or bank that sends you documents.

When para-files finds a document from a known issuer, it uses the **Domain KB signal** (90% confidence):
- Email sender domain: `invoice@ubs.com` → UBS
- Company name in filename: `Invoice_from_Swisscom.pdf`
- Subject line matches: "Your Swisscom bill"

## Using Issuers

```bash
# After seeing classified documents, add known issuers:
uv run para-files add-issuer "My Bank" -c banques

# Then future documents from that issuer match automatically
uv run para-files classify bank_statement.pdf
# → Matches as 90% (Domain KB) without needing semantic matching
```

## See All Issuers and Their Routes

```bash
# Which issuer goes to which category?
uv run para-files issuers

# Tells you the mapping between companies and routes
```

## Related Commands

- **[add-issuer](add-issuer.md)** - Register a new issuer
- **[tree](tree.md)** - See complete tree with issuers
- **[Task: Manage Issuers](../tasks/manage-issuers.md)** - How-to guide
