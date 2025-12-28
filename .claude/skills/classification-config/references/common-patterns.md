# Common Patterns Reference

Quick reference for common routing patterns and issuer categories in para-files.

## Pattern Syntax

Patterns use glob syntax:
- `*` matches any characters
- `?` matches single character
- `[abc]` matches a, b, or c
- Case-insensitive matching with `[Xx]`

## Common Document Type Patterns

### Financial Documents

```yaml
# Bank statements
banques:
  patterns:
    - "*[Rr]elev*"
    - "*[Ss]tatement*"
    - "*[Ee]xtrait*"
    - "*[Bb]ank*"

# Tax documents
impots:
  patterns:
    - "*[Ii]mpot*"
    - "*[Tt]ax*"
    - "*[Dd]eclaration*"
    - "*[Ff]iscal*"

# Invoices (general)
factures:
  patterns:
    - "*[Ff]acture*"
    - "*[Ii]nvoice*"
    - "*[Rr]echnung*"
```

### Insurance Documents

```yaml
assurances:
  patterns:
    - "*[Aa]ssurance*"
    - "*[Pp]olice*"
    - "*[Ss]inistre*"
    - "*[Rr]emboursement*"
```

### Real Estate

```yaml
immobilier:
  patterns:
    - "*[Cc]adastre*"
    - "*[Nn]otaire*"
    - "*[Ff]oncier*"
    - "*[Ss]afer*"
    - "*[Aa]cte*vente*"
```

### Health Documents

```yaml
sante:
  patterns:
    - "*[Oo]rdonnance*"
    - "*[Pp]rescription*"
    - "*[Mm]edical*"
    - "*[Rr]emboursement*[Ss]ante*"
```

### Photos and Media

```yaml
photos:
  extensions:
    - ".jpg"
    - ".jpeg"
    - ".png"
    - ".heic"
    - ".raw"
    - ".dng"
  # Uses EXIF date + GPS location
```

## Pre-configured Issuer Categories

| Category | Description | Example Issuers |
|----------|-------------|-----------------|
| `banques` | Banks, financial institutions | UBS, Credit Suisse, PostFinance, Neon |
| `telecom` | Phone, internet providers | Swisscom, Sunrise, Salt, Orange |
| `energie` | Electricity, gas, water | EDF, Romande Energie, Services Industriels |
| `assurances` | Insurance companies | CSS, Visana, Swica, Generali |
| `sante` | Healthcare providers | CHUV, HUG, pharmacies |
| `cloud` | Cloud service providers | AWS, Azure, Google Cloud, Infomaniak |
| `materiels` | Retail, hardware stores | digitec, Galaxus, Brack, Apple |
| `dons` | Charities | Unicef, Amnesty, Croix Rouge, Rega |
| `transport` | Airlines, car rental, transport | SwissAir, Hertz, CFF, Mobility |
| `licences` | Software licenses | Microsoft, Adobe, Apple, Commvault |

## Path Variable Examples

### Year-based organization
```yaml
destination: "4_Archives/banques/{issuer}/{YYYY}"
# Result: 4_Archives/banques/UBS/2025
```

### Monthly organization
```yaml
destination: "4_Archives/photos/{YYYY}/{MM}"
# Result: 4_Archives/photos/2025/06
```

### Location-based (photos with GPS)
```yaml
destination: "4_Archives/photos/{YYYY}/{country}/{location}/{MM}"
# Result: 4_Archives/photos/2025/Switzerland/Geneva/06
```

### Technology-based (books)
```yaml
destination: "3_Resources/livres/{technology}"
# Result: 3_Resources/livres/Python
```

## Swiss-specific Patterns

```yaml
# Billag/Serafe (TV tax)
redevance_tv:
  patterns: ["*[Ss]erafe*", "*[Bb]illag*"]
  known_issuers: ["Serafe", "Billag"]

# Cantonal tax
impots_canton:
  patterns: ["*[Ii]mpot*[Cc]anton*", "*[Tt]axation*"]

# AVS/AI (social security)
avs:
  patterns: ["*AVS*", "*AI*", "*[Rr]ente*"]

# LPP (pension)
prevoyance:
  patterns: ["*LPP*", "*[Pp]ilier*", "*[Pp]revision*"]
```

## French-specific Patterns

```yaml
# CAF (family benefits)
caf:
  patterns: ["*CAF*", "*[Aa]llocations*"]

# Impots France
impots_france:
  patterns: ["*[Ii]mpots*[Ff]rance*", "*[Ff]isc*"]

# EDF (electricity)
energie_france:
  patterns: ["*EDF*", "*[Ee]lectricite*[Ff]rance*"]
```

## Testing Patterns

After adding patterns, verify with:

```bash
# Test specific file
uv run para-files classify document.pdf -v

# Test route matching
uv run para-files test-route route_name document.pdf

# Scan folder
uv run para-files scan /path --recursive
```
