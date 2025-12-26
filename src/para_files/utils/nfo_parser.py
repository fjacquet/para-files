"""NFO file parser for classification hints.

NFO files are text files commonly used to store metadata about media files.
They can contain structured information like title, category, year, etc.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)

# Encodings to try when reading NFO files (in order)
NFO_ENCODINGS = ["utf-8", "cp437", "latin-1", "utf-16", "windows-1252"]

# Year range for validation
MIN_VALID_YEAR = 1900
MAX_VALID_YEAR = 2100


@dataclass
class NfoHints:
    """Hints extracted from an .nfo file."""

    title: str | None = None
    category: str | None = None
    year: int | None = None
    source: str | None = None
    language: str | None = None
    author: str | None = None
    publisher: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    raw_text: str = ""

    def has_hints(self) -> bool:
        """Check if any useful hints were extracted."""
        return any(
            [
                self.title,
                self.category,
                self.year,
                self.source,
                self.language,
                self.author,
                self.publisher,
                self.description,
                self.tags,
            ]
        )


def _read_nfo_file(path: Path) -> str | None:
    """Read NFO file with encoding fallback.

    Args:
        path: Path to the .nfo file

    Returns:
        File content as string, or None if unreadable
    """
    for encoding in NFO_ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError as e:
            logger.warning("Error reading NFO file %s: %s", path, e)
            return None

    logger.warning("Could not decode NFO file with any known encoding: %s", path)
    return None


def _extract_field(text: str, patterns: list[str]) -> str | None:
    """Extract a field value using multiple regex patterns.

    Args:
        text: Text to search
        patterns: List of regex patterns with one capture group

    Returns:
        Extracted value or None
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def _extract_year(text: str) -> int | None:
    """Extract a year from text.

    Args:
        text: Text to search

    Returns:
        Year as integer or None
    """
    # Look for year patterns
    patterns = [
        r"year[:\s]+(\d{4})",
        r"date[:\s]+.*?(\d{4})",
        r"release[:\s]+.*?(\d{4})",
        r"\b(19\d{2}|20[0-2]\d)\b",  # Standalone year 1900-2029
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                year = int(match.group(1))
                if MIN_VALID_YEAR <= year <= MAX_VALID_YEAR:
                    return year
            except ValueError:
                continue

    return None


def _extract_tags(text: str) -> list[str]:
    """Extract tags/keywords from text.

    Args:
        text: Text to search

    Returns:
        List of extracted tags
    """
    tags: list[str] = []

    # Look for explicit tag lines
    patterns = [
        r"tags?[:\s]+(.+?)(?:\n|$)",
        r"keywords?[:\s]+(.+?)(?:\n|$)",
        r"genre[:\s]+(.+?)(?:\n|$)",
        r"type[:\s]+(.+?)(?:\n|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Split on common delimiters
            raw_tags = re.split(r"[,;|/]", match.group(1))
            tags.extend(t.strip() for t in raw_tags if t.strip())

    return list(set(tags))  # Deduplicate


def parse_nfo(path: Path) -> NfoHints:
    """Parse an .nfo file and extract classification hints.

    Args:
        path: Path to the .nfo file

    Returns:
        NfoHints with extracted information
    """
    hints = NfoHints()

    content = _read_nfo_file(path)
    if not content:
        return hints

    hints.raw_text = content

    # Extract title
    hints.title = _extract_field(
        content,
        [
            r"title[:\s]+(.+?)(?:\n|$)",
            r"name[:\s]+(.+?)(?:\n|$)",
            r"^(.+?)(?:\n|$)",  # First non-empty line as fallback
        ],
    )

    # Extract category
    hints.category = _extract_field(
        content,
        [
            r"category[:\s]+(.+?)(?:\n|$)",
            r"type[:\s]+(.+?)(?:\n|$)",
            r"genre[:\s]+(.+?)(?:\n|$)",
        ],
    )

    # Extract year
    hints.year = _extract_year(content)

    # Extract source
    hints.source = _extract_field(
        content,
        [
            r"source[:\s]+(.+?)(?:\n|$)",
            r"from[:\s]+(.+?)(?:\n|$)",
            r"origin[:\s]+(.+?)(?:\n|$)",
        ],
    )

    # Extract language
    hints.language = _extract_field(
        content,
        [
            r"language[:\s]+(.+?)(?:\n|$)",
            r"lang[:\s]+(.+?)(?:\n|$)",
        ],
    )

    # Extract author
    hints.author = _extract_field(
        content,
        [
            r"author[:\s]+(.+?)(?:\n|$)",
            r"by[:\s]+(.+?)(?:\n|$)",
            r"creator[:\s]+(.+?)(?:\n|$)",
            r"artist[:\s]+(.+?)(?:\n|$)",
        ],
    )

    # Extract publisher
    hints.publisher = _extract_field(
        content,
        [
            r"publisher[:\s]+(.+?)(?:\n|$)",
            r"label[:\s]+(.+?)(?:\n|$)",
            r"studio[:\s]+(.+?)(?:\n|$)",
        ],
    )

    # Extract description
    hints.description = _extract_field(
        content,
        [
            r"description[:\s]+(.+?)(?:\n\n|\Z)",
            r"summary[:\s]+(.+?)(?:\n\n|\Z)",
            r"about[:\s]+(.+?)(?:\n\n|\Z)",
        ],
    )

    # Extract tags
    hints.tags = _extract_tags(content)

    return hints


def find_associated_nfo(file_path: Path) -> Path | None:
    """Find an .nfo file associated with a given file.

    Search order:
    1. {filename}.nfo (same name, different extension)
    2. {folder}.nfo (folder name as nfo)
    3. Any *.nfo in the same directory

    Args:
        file_path: Path to the file to find NFO for

    Returns:
        Path to associated .nfo file, or None if not found
    """
    if not file_path.exists():
        return None

    parent = file_path.parent
    result: Path | None = None

    # 1. Check for file.nfo (same basename)
    nfo_same_name = parent / f"{file_path.stem}.nfo"
    if nfo_same_name.exists() and nfo_same_name.is_file():
        result = nfo_same_name
    else:
        # Also check case-insensitive
        for f in parent.iterdir():
            if f.suffix.lower() == ".nfo" and f.stem.lower() == file_path.stem.lower():
                result = f
                break

    # 2. Check for folder.nfo if not found
    if result is None:
        folder_nfo = parent / f"{parent.name}.nfo"
        if folder_nfo.exists() and folder_nfo.is_file():
            result = folder_nfo

    # 3. Find any .nfo in the directory if still not found
    if result is None:
        nfo_files = list(parent.glob("*.nfo"))
        if nfo_files:
            # Prefer shorter names (likely the "main" one)
            nfo_files.sort(key=lambda p: len(p.name))
            result = nfo_files[0]

    return result


def get_nfo_hints_for_file(file_path: Path) -> NfoHints | None:
    """Get classification hints from an associated .nfo file.

    Args:
        file_path: Path to the file

    Returns:
        NfoHints if an associated .nfo was found and parsed, None otherwise
    """
    nfo_path = find_associated_nfo(file_path)
    if nfo_path:
        hints = parse_nfo(nfo_path)
        if hints.has_hints():
            logger.debug("Found NFO hints for %s from %s", file_path.name, nfo_path.name)
            return hints

    return None
