#!/usr/bin/env python3
"""Update documents.json to add retention suffixes to para_pattern fields."""

from __future__ import annotations

import json
import re
from pathlib import Path

# Retention suffix mapping (same as in taxonomy_classifier.py)
RETENTION_SUFFIXES = {
    "permanent": "_perm",
    "retirement": "_ret",
    "10_years": "_10y",
    "5_years": "_5y",
    "contract_duration": "_ctr",
    "warranty_2_years": "_2y",
}


def add_retention_suffix(pattern: str, retention: str) -> str:
    """Add retention suffix to the category folder in a para_pattern.

    Examples:
        4_Archives/fiscalite/{year} + 10_years -> 4_Archives/fiscalite_10y/{year}
        3_Resources/administratif/identite + permanent -> 3_Resources/administratif/identite_perm
    """
    suffix = RETENTION_SUFFIXES.get(retention, "")
    if not suffix:
        return pattern

    # Pattern: PARA_folder/category[/subpath]
    # We want to add suffix to the second component (after PARA folder)
    parts = pattern.split("/")
    if len(parts) < 2:
        return pattern

    # Check if suffix already present
    if any(s in parts[1] for s in RETENTION_SUFFIXES.values()):
        return pattern  # Already has a suffix

    # Add suffix to the category folder (second part)
    parts[1] = parts[1] + suffix
    return "/".join(parts)


def update_documents_json(filepath: Path) -> dict:
    """Update documents.json with retention suffixes in para_patterns."""
    with filepath.open() as f:
        data = json.load(f)

    updates_made = []

    for category in data.get("categories", []):
        category_pattern = category.get("para_pattern", "")
        category_retention = None  # Will be determined from documents

        for doc in category.get("documents", []):
            retention = doc.get("retention")
            if not retention:
                continue

            # Get the effective pattern (document-level overrides category-level)
            original_pattern = doc.get("para_pattern") or category_pattern
            if not original_pattern:
                continue

            # Add retention suffix
            new_pattern = add_retention_suffix(original_pattern, retention)

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

    print(f"\nUpdates to be made: {len(updates)}")
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
