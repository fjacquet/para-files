"""Generic filename detection for OCR-based renaming.

This module identifies filenames that are generic/non-descriptive and would
benefit from being renamed based on OCR content before classification.
"""

from __future__ import annotations

import re
from pathlib import Path


# Patterns that indicate a generic/non-descriptive filename
_GENERIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Scanner output patterns
    re.compile(r"^scan[_\-]?\d*\.pdf$", re.IGNORECASE),
    re.compile(r"^numérisation[_\-]?\d*\.pdf$", re.IGNORECASE),
    re.compile(r"^scanned[_\-]?\d*\.pdf$", re.IGNORECASE),
    # Camera/phone patterns
    re.compile(r"^IMG[_\-]?\d+\.pdf$", re.IGNORECASE),
    re.compile(r"^DSC[_\-]?\d+\.pdf$", re.IGNORECASE),
    re.compile(r"^DCIM[_\-]?\d+\.pdf$", re.IGNORECASE),
    re.compile(r"^photo[_\-]?\d*\.pdf$", re.IGNORECASE),
    re.compile(r"^image[_\-]?\d*\.pdf$", re.IGNORECASE),
    # Generic document names
    re.compile(r"^document[_\-]?\d*\.pdf$", re.IGNORECASE),
    re.compile(r"^doc[_\-]?\d+\.pdf$", re.IGNORECASE),
    re.compile(r"^file[_\-]?\d*\.pdf$", re.IGNORECASE),
    re.compile(r"^pdf[_\-]?\d*\.pdf$", re.IGNORECASE),
    re.compile(r"^nouveau[_\-]?document[_\-]?\d*\.pdf$", re.IGNORECASE),
    re.compile(r"^new[_\-]?document[_\-]?\d*\.pdf$", re.IGNORECASE),
    # Timestamp-only names (8+ digits)
    re.compile(r"^\d{8,}\.pdf$"),
    # Hex hash names (8+ hex chars)
    re.compile(r"^[a-f0-9]{8,}\.pdf$", re.IGNORECASE),
    # UUID-like names
    re.compile(
        r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\.pdf$",
        re.IGNORECASE,
    ),
    # Copy patterns (often indicate unnamed copies)
    re.compile(r"^copy[_\-]?\d*\.pdf$", re.IGNORECASE),
    re.compile(r"^copie[_\-]?\d*\.pdf$", re.IGNORECASE),
    # Untitled patterns
    re.compile(r"^untitled[_\-]?\d*\.pdf$", re.IGNORECASE),
    re.compile(r"^sans[_\-]?titre[_\-]?\d*\.pdf$", re.IGNORECASE),
    # Number-only names
    re.compile(r"^\d+\.pdf$"),
    # Download patterns
    re.compile(r"^download[_\-]?\d*\.pdf$", re.IGNORECASE),
    re.compile(r"^téléchargement[_\-]?\d*\.pdf$", re.IGNORECASE),
    # Attachment patterns
    re.compile(r"^attachment[_\-]?\d*\.pdf$", re.IGNORECASE),
    re.compile(r"^pièce[_\-]?jointe[_\-]?\d*\.pdf$", re.IGNORECASE),
)

# Minimum meaningful name length (excluding extension)
_MIN_MEANINGFUL_LENGTH = 4


def is_generic_filename(filename: str | Path) -> bool:
    """Check if a filename is generic and would benefit from OCR-based renaming.

    A filename is considered generic if it:
    - Matches common scanner/camera output patterns (scan_001.pdf, IMG_1234.pdf)
    - Is just numbers or a hash
    - Is a common placeholder name (document.pdf, file.pdf)
    - Has no meaningful descriptive content

    Args:
        filename: The filename or path to check (only the name is evaluated)

    Returns:
        True if the filename is generic and should be renamed, False otherwise
    """
    name = filename.name if isinstance(filename, Path) else filename

    # Only process PDF files
    if not name.lower().endswith(".pdf"):
        return False

    # Check against all generic patterns
    for pattern in _GENERIC_PATTERNS:
        if pattern.match(name):
            return True

    # Check for very short names (likely not descriptive)
    stem = name[:-4]  # Remove .pdf
    return len(stem) < _MIN_MEANINGFUL_LENGTH


def get_generic_pattern_match(filename: str | Path) -> str | None:
    """Get the pattern that matched a generic filename.

    Useful for logging/debugging which pattern triggered the detection.

    Args:
        filename: The filename to check

    Returns:
        Description of the matching pattern, or None if not generic
    """
    name = filename.name if isinstance(filename, Path) else filename

    if not name.lower().endswith(".pdf"):
        return None

    pattern_descriptions = [
        (r"^scan", "scanner output"),
        (r"^numérisation", "scanner output (French)"),
        (r"^scanned", "scanner output"),
        (r"^IMG", "camera photo"),
        (r"^DSC", "camera photo"),
        (r"^DCIM", "camera photo"),
        (r"^photo", "photo"),
        (r"^image", "image"),
        (r"^document", "generic document"),
        (r"^doc[_\-]", "generic document"),
        (r"^file", "generic file"),
        (r"^pdf", "generic pdf"),
        (r"^nouveau", "new document (French)"),
        (r"^new", "new document"),
        (r"^\d{8,}\.pdf$", "timestamp"),
        (r"^[a-f0-9]{8,}\.pdf$", "hash"),
        (r"^[a-f0-9]{8}-", "UUID"),
        (r"^copy", "copy"),
        (r"^copie", "copy (French)"),
        (r"^untitled", "untitled"),
        (r"^sans", "untitled (French)"),
        (r"^\d+\.pdf$", "number only"),
        (r"^download", "download"),
        (r"^téléchargement", "download (French)"),
        (r"^attachment", "attachment"),
        (r"^pièce", "attachment (French)"),
    ]

    for prefix, description in pattern_descriptions:
        if re.match(prefix, name, re.IGNORECASE):
            return description

    stem = name[:-4]
    if len(stem) < _MIN_MEANINGFUL_LENGTH:
        return "too short"

    return None
