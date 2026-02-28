# Routing Rules Fix Plan

## Problem Summary

Images/photos are being misrouted to fiscal folders during rescan:

- `20140314204821-Honey Moon.png` → should be in photos
- `2022-01-17 20.58.20.heic` → should be in photos
- `acl-add.png`, `acl1.png`, `acl2.png` → should be in screenshots

## Root Causes Identified

| # | Issue | Severity | File |
|---|-------|----------|------|
| 1 | Rescan bypasses RulesEngineClassifier | CRITICAL | `rescan_cmd.py` |
| 2 | `source:` constraint never enforced | CRITICAL | `rules_engine.py` |
| 3 | No photo taxonomy in documents.json | MEDIUM | `documents.json` |
| 4 | Duplicate rule definitions | LOW | `personal_file_tree.yaml` |

## Fix Plan

### Fix 1: Rescan Command (CRITICAL)

**File:** `src/para_files/cli/rescan_cmd.py`

**Problem:** Uses `TaxonomyClassifier` directly, bypassing rules engine.

**Solution:** Use `ClassificationPipeline` which includes all classifiers in order:

1. ValidatedDBClassifier (100%)
2. RulesEngineClassifier (95%) ← This handles photo extensions
3. BookDetector (92%)
4. DomainKBClassifier (90%)
5. SemanticClassifier (85%)
6. MLXLLMClassifier (configurable)

**Status:** [x] COMPLETED

---

### Fix 2: Source Constraint Enforcement (CRITICAL)

**File:** `src/para_files/classifiers/rules_engine.py`

**Problem:** `source: "0_Inbox"` is defined in YAML but never checked.

**Solution:** Add source path validation in `_matches_extension_and_pattern()`:

```python
def _matches_extension_and_pattern(self, rule: RoutingRule, metadata: FileMetadata) -> bool:
    # Check source constraint if defined
    if rule.source:
        source_path = self.config.para_root / rule.source
        if not str(metadata.path).startswith(str(source_path)):
            return False
    # ... rest of matching logic
```

**Status:** [x] COMPLETED

---

### Fix 3: Photo Categories in Taxonomy (MEDIUM)

**File:** `config/documents.json`

**Problem:** No categories for image file types (.jpg, .heic, .png).

**Solution:** Add media category with photo/video/screenshot sub-documents.

**Status:** [x] COMPLETED

---

### Fix 4: Duplicate Rules Cleanup (LOW)

**File:** `config/personal_file_tree.yaml`

**Duplicates found:**

- `credit_agricole` (2x)
- `vmware_documentation` (3x)
- `bleu_marine_immobilier` (2x)
- `travaux_maison` (2x)

**Solution:** Remove duplicates, keep most comprehensive version.

**Status:** [x] COMPLETED

---

## Testing Plan

1. Run existing test suite: `uv run pytest`
2. Test photo classification: `uv run para-files scan test-image.heic`
3. Test rescan dry-run: `uv run para-files rescan --category fiscalite --dry-run`
4. Verify coverage maintained: `uv run pytest --cov`

## Progress Tracking

- [x] Fix 1: Rescan command
- [x] Fix 2: Source constraint
- [x] Fix 3: Photo taxonomy
- [x] Fix 4: Duplicate cleanup
- [x] Tests pass (976 passed, 3 skipped)
- [x] CHANGELOG updated
