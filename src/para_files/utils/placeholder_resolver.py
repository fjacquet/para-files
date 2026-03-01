"""Centralized placeholder resolution for classification path patterns.

Provides a single canonical function for replacing and cleaning up
{placeholder} tokens in PARA path patterns used by all classifiers.
"""

from __future__ import annotations

import re


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


def clean_unreplaced_placeholders(category: str) -> str:
    """Remove any remaining {placeholder} tokens and normalize slashes.

    Handles both known placeholders ({year}, {issuer}, {location},
    {country}, {YYYY}, {MM}, {DD}, {month}, {day}) and any unknown
    placeholders left over from partial pattern resolution.

    Collapses double-slashes and strips trailing slash.

    Args:
        category: Category path potentially containing unreplaced placeholders.

    Returns:
        Cleaned category path without empty segments.
    """
    # Remove any remaining {placeholder} tokens (known or unknown)
    result = re.sub(r"\{[^}]+\}", "", category)
    # Collapse consecutive slashes produced by placeholder removal
    result = re.sub(r"/+", "/", result)
    # Strip trailing slash
    return result.rstrip("/")
