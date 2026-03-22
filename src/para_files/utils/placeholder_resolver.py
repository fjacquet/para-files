"""Centralized placeholder resolution for classification path patterns.

Provides a single canonical function for replacing and cleaning up
{placeholder} tokens in PARA path patterns used by all classifiers.
"""

from __future__ import annotations

import re

from loguru import logger


# All known placeholder names the classifiers use
_KNOWN_PLACEHOLDERS = frozenset(
    {
        "year",
        "YYYY",
        "MM",
        "DD",
        "month",
        "day",
        "issuer",
        "location",
        "country",
    }
)

# Required placeholders: if any remain unresolved, classification is rejected
_REQUIRED_PLACEHOLDERS = frozenset({"issuer", "technology", "location", "country"})

# Optional placeholders: if remaining after resolution, they are silently stripped
_OPTIONAL_PLACEHOLDERS = frozenset({"year", "YYYY", "MM", "DD", "month", "day"})


def resolve_placeholders(pattern: str, params: dict[str, str]) -> str:
    """Replace {key} placeholders in pattern with values from params.

    Args:
        pattern: Path pattern containing {key} placeholders.
        params: Mapping of placeholder names to replacement values.

    Returns:
        Pattern with all matching placeholders replaced.
    """
    result = pattern
    for key, value in params.items():
        result = result.replace(f"{{{key}}}", value)
    return result


def clean_unreplaced_placeholders(category: str) -> str | None:
    """Remove optional {placeholder} tokens; reject paths with required ones.

    Required placeholders (issuer, technology, location, country): if any
    remain unresolved, returns None to signal rejection. A path like
    "2_Areas/{issuer}/docs" is worse than no classification at all.

    Optional placeholders (year, YYYY, MM, DD, month, day): if remaining,
    they are stripped cleanly and the path is returned without them.

    Collapses double-slashes produced by removal and strips trailing slash.

    Args:
        category: Category path potentially containing unreplaced placeholders.

    Returns:
        Cleaned category path without empty segments, or None if required
        placeholders remain unresolved.
    """
    # Find all remaining placeholders
    remaining = re.findall(r"\{([^}]+)\}", category)

    # Check for required placeholders that are still unresolved
    required_missing = [p for p in remaining if p in _REQUIRED_PLACEHOLDERS]
    if required_missing:
        logger.warning(
            "Rejecting classification: required placeholders unresolved: {} in '{}'",
            required_missing,
            category,
        )
        return None

    # Remove any remaining {placeholder} tokens (optional or unknown)
    result = re.sub(r"\{[^}]+\}", "", category)
    # Collapse consecutive slashes produced by placeholder removal
    result = re.sub(r"/+", "/", result)
    # Strip trailing slash
    return result.rstrip("/")
