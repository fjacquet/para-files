# Classification Issues Report

Generated: 2024-12-29
**Last Updated: 2024-12-30**

## Summary

| Category | Total Files | Issues Detected | Status |
|----------|-------------|-----------------|--------|
| Mobilité | 888 | 23 | ✅ Resolved |
| Energie | 84 | 3 | ✅ Resolved |
| Assurances | 393 | 1 | ✅ Resolved |

## Orphan Year Folders - ALL RESOLVED ✅

All ~40 orphan year folders have been consolidated into issuer-based structure.

### Energie (3 folders) - COMPLETED 2025-12-29
| Original Folder | Files | Action Taken |
|----------------|-------|--------------|
| Energie/2022 | 1 | → divers (unidentified) |
| Energie/2001 | 1 | → GDF/2011 (was mislabeled year) |
| Energie/2016 | 1 | → Eau/2016 (water bill) |

### Assurances (11 folders) - COMPLETED 2025-12-29
| Original Folder | Files | Action Taken |
|----------------|-------|--------------|
| Assurances/2008-2022 | 14 | → Pacifica, Orion, banques, divers |

Key reclassifications:
- Pacifica insurance documents → Assurances/Pacifica/{YYYY}
- Orion legal protection → Assurances/Orion/{YYYY}
- Bank statements → banques/Credit Agricole/{YYYY}

### Santé (8 folders, 16 files) - COMPLETED 2025-12-29
| Original Folder | Files | Action Taken |
|----------------|-------|--------------|
| Santé/2011-2025 | 16 | → AVS, CAF, Kuoni, impots, divers |

Key reclassifications:
- AVS documents → administratif/AVS/{YYYY}
- CAF allocations → administratif/CAF/{YYYY}
- Kuoni travel → voyages/Kuoni/{YYYY}
- Tax documents → impots-suisse/{YYYY}

### Materiels (18 folders, 76 files) - COMPLETED 2025-12-30
| Category | Files | Destination |
|----------|-------|-------------|
| 5àSec tickets | ~20 | Services/5aSec/{YYYY} |
| IT hardware | ~10 | Materiels/Informatique/{YYYY} |
| Home/Kitchen | ~8 | Materiels/Maison/{YYYY} |
| Real estate | ~12 | immobilier/{issuer}/{YYYY} |
| Travel | ~5 | voyages/{issuer}/{YYYY} |
| Insurance | ~5 | Assurances/{issuer}/{YYYY} |
| Leisure | ~5 | loisirs/{type}/{YYYY} |
| Fines | 2 | administratif/amendes/{YYYY} |
| Unreadable scans | 7 | Materiels/divers/scans-non-classes/ |

**Correction:** `20111226-lavevaiselle.pdf` was incorrectly in 1980 folder → moved to Maison/2011

## Misclassified Files - RESOLVED ✅

### Mobilité Issues - COMPLETED 2025-12-29

#### ByJuno → CFF (17 files)
- **Problem:** `C00*_1_*.pdf` files were CFF invoices misclassified as ByJuno
- **Solution:** Moved to `CFF/{YYYY}` based on filename date
- **Status:** ✅ Completed

#### SNCF/CFF International Tickets (4 files)
- **Decision:** Keep in SNCF (vendor-based classification)
- **Reason:** These are SNCF purchases for international routes
- **Status:** ✅ No action needed

#### EasyPark - VERIFIED CORRECT
- `Receipt_BI_1022743311.pdf` correctly classified
- "Mobility Hub Parkservice GmbH" is parking operator, not Mobility car-sharing
- **Status:** ✅ Verified

#### MOB folder - CLEANED
- Train ticket correctly classified
- 3 CV files moved to `2_Areas/carriere/CV/`
- **Status:** ✅ Completed

### Energie Issues - COMPLETED 2025-12-29

#### Crédit Agricole Bank Statements (6 files)
- **Problem:** `Compte_23316454000_*` files were in EDF, GDF, Maif folders
- **Solution:** Moved to `banques/Credit Agricole/{YYYY}`
- **Status:** ✅ Completed

### Assurances Issues - COMPLETED 2025-12-29

#### Maif folder bank statement
- **Problem:** Crédit Agricole statement misclassified as Pacifica
- **Solution:** Moved to `banques/Credit Agricole/2013`
- **Status:** ✅ Completed

## Route Updates - COMPLETED ✅

### Rules Added 2025-12-29

| Rule | Patterns | Destination |
|------|----------|-------------|
| CFF invoices | `C00*_1_*.pdf`, `*CFF*`, `*sbb*` | Mobilité/CFF/{YYYY} |
| Mobility receipts | `Receipt_BI_*`, `*Mobility*` | Mobilité/Mobility/{YYYY} |
| Pacifica | `*Pacifica*`, `611*_*.pdf` | Assurances/Pacifica/{YYYY} |
| Orion | `*Orion*Private*`, `*Protection*Juridique*` | Assurances/Orion/{YYYY} |
| Eau | `*Eau*Facture*`, `*Services*Eaux*` | Energie/Eau/{YYYY} |
| AVS | `*AVS*`, `*assurance*vieillesse*` | administratif/AVS/{YYYY} |
| CAF | `*CAF*`, `*allocations*familiales*` | administratif/CAF/{YYYY} |
| Kuoni | `*Kuoni*`, `*DER*Touristik*` | voyages/Kuoni/{YYYY} |

### Rules Added 2025-12-30

| Rule | Patterns | Destination |
|------|----------|-------------|
| 5àSec | `*5àSec*`, `Ticket [0-9]*` | Services/5aSec/{YYYY} |
| DFi Service | `*DFi*Service*`, `*zimbra*` | Materiels/Informatique/{YYYY} |
| Corsica Ferries | `*Corsica*Ferries*` | voyages/Corsica-Ferries/{YYYY} |
| American Airlines | `*American*Airlines*` | voyages/American-Airlines/{YYYY} |
| Tryba | `*Tryba*` | immobilier/Tryba/{YYYY} |
| Bleu Marine | `*Bleu*Marine*`, `*CRG*DU*AU*` | immobilier/Bleu-Marine/{YYYY} |
| Editions Diamond | `*Diamond*`, `*Linux*Magazine*` | loisirs/magazines/{YYYY} |
| Ninja Kitchen | `*Ninja*`, `*SharkNinja*` | Materiels/Maison/Cuisine/{YYYY} |

## Remaining Items

### Low Priority
1. [ ] Review `Invoice_*` pattern (generic, may catch multiple issuers)
2. [ ] Consider OCR for scanned documents in `divers/scans-non-classes/`
3. [ ] SNCF/CFF international tickets - consider `Transport International` category

### Manual Review Needed
7 scanned PDFs in `Materiels/divers/scans-non-classes/` have no extractable text:
- `200506-2007.pdf`
- `20110926-blackcaviar.pdf`
- `20111027.pdf`
- `devoir.pdf`
- `Numériser 2015-3-1 16.37.04.pdf`
- `Numériser 2015-6-2 18.04.53.pdf`
- `S28C-117031009370.pdf`

## Statistics

| Metric | Value |
|--------|-------|
| Total orphan folders processed | 40 |
| Total files reclassified | ~120 |
| New routing rules added | 16 |
| Commits | 3 |

## Commits

- `16c0dcc` - Initial route additions (CFF, Mobility, Pacifica, Orion, Eau, AVS, CAF, Kuoni)
- `00b86ef` - File moves and corrections
- `559934c` - Additional routes (5àSec, DFi, Corsica, American Airlines, Tryba, Bleu Marine, Diamond, Ninja)
