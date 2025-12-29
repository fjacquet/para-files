# Classification Issues Report

Generated: 2024-12-29

## Summary

| Category | Total Files | Issues Detected |
|----------|-------------|-----------------|
| Mobilité | 888 | 23 |
| Energie | 84 | 3 |
| Assurances | 393 | 1 |

## Orphan Year Folders

These folders contain files by year but should be organized by issuer:

### Energie (3 folders)
| Folder | File Count |
|--------|------------|
| Energie/2022 | 1 |
| Energie/2001 | 1 |
| Energie/2016 | 1 |

### Assurances (11 folders)
| Folder | File Count |
|--------|------------|
| Assurances/2008 | 1 |
| Assurances/2011 | 1 |
| Assurances/2012 | 1 |
| Assurances/2013 | 1 |
| Assurances/2014 | 1 |
| Assurances/2015 | 4 |
| Assurances/2016 | 1 |
| Assurances/2019 | 1 |
| Assurances/2020 | 1 |
| Assurances/2022 | 1 |

### Santé (8 folders, 16 files)
| Folder | File Count |
|--------|------------|
| Santé/2011 | 1 |
| Santé/2012 | 5 |
| Santé/2013 | 2 |
| Santé/2015 | 1 |
| Santé/2016 | 1 |
| Santé/2022 | 4 |
| Santé/2024 | 1 |
| Santé/2025 | 1 |

### Materiels (18 folders, 76 files)
| Folder | File Count |
|--------|------------|
| Materiels/1980 | 1 |
| Materiels/2007 | 2 |
| Materiels/2008 | 1 |
| Materiels/2010 | 1 |
| Materiels/2011 | 5 |
| Materiels/2012 | 10 |
| Materiels/2013 | 3 |
| Materiels/2014 | 10 |
| Materiels/2015 | 5 |
| Materiels/2016 | 3 |
| Materiels/2017 | 4 |
| Materiels/2018 | 1 |
| Materiels/2019 | 1 |
| Materiels/2021 | 4 |
| Materiels/2022 | 11 |
| Materiels/2023 | 12 |
| Materiels/2024 | 1 |
| Materiels/2050 | 1 |

## Misclassified Files

### Mobilité Issues

#### ByJuno folder contains CFF invoices (17 files)
- Pattern: `C00*_1_*.pdf` files are CFF invoices, not ByJuno
- Files like `C004828398_1_20220809053711.pdf` should go to `CFF/{YYYY}`

#### SNCF folder contains CFF-related files (4 files)
- These are international tickets (Paris-Geneva) that mention both SNCF and CFF
- Files like `GENEVE_CFF-BOURGES_*.pdf` or `PARIS_GARE_LYON-GENEVE_CFF_*.pdf`
- **Decision needed**: Keep in SNCF (origin) or move to CFF?

#### EasyPark folder - VERIFIED CORRECT
- `Receipt_BI_1022743311.pdf` is correctly an **EasyPark receipt**
- Mentions "Mobility Hub Parkservice GmbH" as parking operator (NOT Mobility car-sharing)

#### MOB folder - CLEANED
- `3100015203-1787806.pdf` is correctly a **MOB train ticket** (Montreux-Schönried)
- Removed 3 CV files (CV.pdf, CV UK LAN.pdf, CV UK EMC.pdf) → moved to `2_Areas/carriere/CV/`

### Energie Issues - CORRECTED

#### EDF folder contained misclassified bank statements (4 files)
- `Compte_23316454000_*` files were **Crédit Agricole bank statements**, not GDF
- Moved to `banques/Credit Agricole/{YYYY}`
- `facture*` files are correctly EDF invoices

#### GDF folder contained bank statement (1 file)
- `Compte_23316454000_*` was Crédit Agricole, moved to `banques/Credit Agricole/2011`

### Assurances Issues - CORRECTED

#### Maif folder contained bank statement (1 file)
- `Compte_23316454000_*` was **Crédit Agricole bank statement**, not Pacifica
- Moved to `banques/Credit Agricole/2013`

## Recommended Route Fixes

### 1. ByJuno Pattern Fix
The current `byjuno` rule is capturing CFF invoices. Need to:
- Make ByJuno pattern more specific (require "ByJuno" in content)
- OR create specific pattern for CFF invoices with `C00*_1_*.pdf` format

```yaml
# Proposed fix in personal_file_tree.yaml
cff_invoices:
  patterns:
    - "C00*_1_*.pdf"  # CFF invoice pattern
  destination: "4_Archives/factures/Mobilité/CFF/{YYYY}"
  date_source: "filename"
  date_pattern: "(\\d{4})(\\d{2})(\\d{2})"
```

### 2. SNCF/CFF International Tickets
These are valid SNCF purchases for CFF routes. Consider:
- Keeping in SNCF (vendor) - current behavior
- Creating `Transport International` category

### 3. Content-Based Classification Needed
Current rules rely on filename patterns. Files with generic names like `Invoice_*` or `C00*` need content-based classification:

| Pattern | Detected Issuer | Destination |
|---------|----------------|-------------|
| `Invoice_*` | Multiple | Need content check |
| `C00*_1_*.pdf` | CFF | Mobilité/CFF |
| `Receipt_BI_*` | Mobility | Mobilité/Mobility |

## Action Items

### Immediate Fixes (Move Files) - COMPLETED 2025-12-29
1. [x] Move 17 ByJuno files to CFF ✓ (C00*_1_*.pdf → CFF/{YYYY})
2. [x] EasyPark file verified ✓ (Receipt_BI_1022743311.pdf is correctly EasyPark, mentions "Mobility Hub" as parking operator)
3. [x] MOB file verified ✓ (3100015203-1787806.pdf is correct MOB train ticket Montreux-Schönried)
4. [x] Move 6 Crédit Agricole statements ✓ (Compte_23316454000_* files moved from EDF, GDF, Maif to banques/Credit Agricole/{YYYY})
5. [x] Maif file corrected ✓ (was Crédit Agricole bank statement, not Pacifica)

### Route Updates Needed

Add these rules to `config/personal_file_tree.yaml`:

```yaml
# CFF invoices with specific pattern (prevents ByJuno confusion)
cff_invoices_pattern:
  patterns:
    - "C00*_1_*.pdf"
    - "*CFF*.pdf"
    - "*sbb*.pdf"
  extensions: [".pdf"]
  destination: "4_Archives/factures/Mobilité/CFF/{YYYY}"
  date_source: "filename"
  date_pattern: "(\\d{4})(\\d{2})(\\d{2})"

# Mobility receipts
mobility_receipts:
  patterns:
    - "Receipt_BI_*.pdf"
    - "*Mobility*.pdf"
  extensions: [".pdf"]
  destination: "4_Archives/factures/Mobilité/Mobility/{YYYY}"
  date_source: "filename"

# GDF invoices (separate from EDF)
gdf_invoices:
  patterns:
    - "*GDF*"
    - "*gdf*"
  extensions: [".pdf"]
  destination: "4_Archives/factures/Energie/GDF/{YYYY}"

# ERDF invoices (separate from EDF)
erdf_invoices:
  patterns:
    - "*ERDF*"
    - "*erdf*"
  extensions: [".pdf"]
  destination: "4_Archives/factures/Energie/ERDF/{YYYY}"
```

### Structural Issues
7. [ ] Consolidate ~40 orphan year folders into issuer-based structure
8. [ ] Consider content-based classification for generic filenames
9. [ ] Review Invoice_* pattern (too generic, catches multiple issuers)
