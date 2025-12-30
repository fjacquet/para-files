#!/usr/bin/env python3
"""Update documents.json to add retention prefixes to para_pattern fields."""

from __future__ import annotations

import json
from pathlib import Path

# Retention prefix mapping (same as in taxonomy_classifier.py)
# Permanent items have no prefix (they go to 3_Resources)
RETENTION_PREFIXES = {
    "permanent": "",  # No prefix
    "retirement": "ret_",
    "10_years": "10y_",
    "5_years": "5y_",
    "contract_duration": "ctr_",
    "warranty_2_years": "2y_",
}


def add_retention_prefix(pattern: str, retention: str) -> str:
    """Add retention prefix to the category folder in a para_pattern.

    Examples:
        4_Archives/fiscalite/{year} + 10_years -> 4_Archives/10y_fiscalite/{year}
        3_Resources/administratif/identite + permanent -> 3_Resources/administratif/identite (no change)
    """
    prefix = RETENTION_PREFIXES.get(retention, "")
    if not prefix:
        return pattern  # No prefix for permanent items

    # Pattern: PARA_folder/category[/subpath]
    # We want to add prefix to the second component (after PARA folder)
    parts = pattern.split("/")
    if len(parts) < 2:
        return pattern

    # Check if prefix already present
    if any(parts[1].startswith(p) for p in RETENTION_PREFIXES.values() if p):
        return pattern  # Already has a prefix

    # Add prefix to the category folder (second part)
    parts[1] = prefix + parts[1]
    return "/".join(parts)


def update_documents_json(filepath: Path) -> tuple[dict, list]:
    """Update documents.json with retention prefixes in para_patterns."""
    with filepath.open() as f:
        data = json.load(f)

    updates_made = []

    for category in data.get("categories", []):
        category_pattern = category.get("para_pattern", "")

        for doc in category.get("documents", []):
            retention = doc.get("retention")
            if not retention:
                continue

            # Get the effective pattern (document-level overrides category-level)
            original_pattern = doc.get("para_pattern") or category_pattern
            if not original_pattern:
                continue

            # Add retention prefix
            new_pattern = add_retention_prefix(original_pattern, retention)

            if new_pattern != original_pattern:
                # Store the new pattern at document level
                doc["para_pattern"] = new_pattern
                updates_made.append({
                    "sub_id": doc.get("sub_id"),
                    "name": doc.get("name"),
                    "retention": retention,
                    "old": original_pattern,
                    "new": new_pattern,
                })

    return data, updates_made


def main():
    """Main entry point."""
    filepath = Path(__file__).parent.parent / "config" / "documents.json"

    print(f"Processing: {filepath}")
    print("-" * 60)

    data, updates = update_documents_json(filepath)

    print(f"\nPrefix updates to be made: {len(updates)}")
    print("-" * 60)

    for u in updates:
        print(f"\n{u['sub_id']} ({u['name']}):")
        print(f"  Retention: {u['retention']}")
        print(f"  Old: {u['old']}")
        print(f"  New: {u['new']}")

    # Write updated JSON
    output_path = filepath
    with output_path.open("w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")  # Trailing newline

    print(f"\n{'=' * 60}")
    print(f"Updated {filepath}")
    print(f"Total patterns updated: {len(updates)}")


if __name__ == "__main__":
    main()
