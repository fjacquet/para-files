# Thema Book Classification

## Overview

Books use the **THEMA v1.6** international book classification standard.
Source: `config/thema.json` (9,187 codes)

## Hybrid Naming Convention

Path format: `{CodeValue}_{ShortName}`

Examples:
- `A_Arts` (code A = Arts)
- `AB_Generalites` (code AB = Arts : généralités)
- `U_Informatique` (code U = Informatique et traitement de l'information)
- `UB_Programmation` (code UB = Informatique : logiciels et programmation)

## Path Building

Full PARA path: `3_Resources/livres/{L1_Code_ShortName}/{L2_Code_ShortName}`

```python
from para_files.taxonomies.models import ThemaTaxonomy

taxonomy.build_para_path("UB")
# → "3_Resources/livres/U_Informatique/UB_Programmation"
```

## Key Design Decisions

1. **Max 2 levels** after `livres/` to avoid deep hierarchies
2. **Accents removed** (é→e, ç→c) for filesystem compatibility
3. **Colon handling**: Take part after colon ("Arts : généralités" → "Generalites")
4. **Slash handling**: Take first part ("Radio / podcasts" → "Radio")
5. **ShortName max length**: 20 characters (truncated at word boundary)
6. **Folder name max length**: 35 characters

## Key Files

- `src/para_files/taxonomies/models.py` - `_make_short_name()`, `_make_folder_name()`, `build_para_path()`
- `src/para_files/utils/thema_lookup.py` - `ThemaLookup.build_para_path()` (delegates to taxonomy)
- `src/para_files/classifiers/book_detector.py` - Uses `thema_lookup.build_para_path()`
