"""MOBI metadata extraction utilities.

MOBI files (Mobipocket format) are ebook files commonly used by Kindle devices.
PyMuPDF (fitz) can open and extract metadata and text from MOBI files.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from para_files.utils.pdf_metadata import extract_all_isbns


# ISBN regex patterns
ISBN_PATTERN = re.compile(r"\b(?:97[89])?\d{9}[\dXx]\b")

# Minimum title length to consider valid
MIN_TITLE_LENGTH = 3


@dataclass
class MobiMetadata:
    """Metadata extracted from a MOBI file."""

    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    isbns: list[str] = field(default_factory=list)
    file_size_mb: float = 0.0


def _extract_title_from_mobi_metadata(metadata: dict[Any, Any]) -> str | None:
    """Extract and validate title from MOBI metadata dict.

    Args:
        metadata: Metadata dictionary from PyMuPDF.

    Returns:
        Title string if valid, None otherwise.
    """
    title = metadata.get("title") or metadata.get("Subject")

    if not isinstance(title, str):
        return None

    title = title.strip()
    if len(title) < MIN_TITLE_LENGTH:
        return None

    return title


def _scan_mobi_pages_for_isbns(doc: Any, filename_isbns: list[str]) -> list[str]:  # noqa: ANN401
    """Scan MOBI document pages for ISBNs.

    Args:
        doc: PyMuPDF document object.
        filename_isbns: ISBNs already found in filename.

    Returns:
        List of all ISBNs found (filename + content).
    """
    all_isbns = list(filename_isbns)
    seen_isbns = set(filename_isbns)

    # Scan first 5 pages for ISBNs
    max_pages = min(5, doc.page_count)
    for page_num in range(max_pages):
        try:
            page = doc[page_num]
            text = page.get_text()

            # Extract ISBNs using the same pattern as PDF
            matches = extract_all_isbns(text)
            for isbn in matches:
                if isbn not in seen_isbns:
                    seen_isbns.add(isbn)
                    all_isbns.append(isbn)
        except OSError:
            # Skip pages that can't be read
            continue

    return all_isbns


def extract_mobi_metadata(path: Path) -> MobiMetadata | None:
    """Extract metadata from a MOBI file.

    Uses PyMuPDF to extract title from metadata and scan content for ISBNs.

    Args:
        path: Path to the MOBI file.

    Returns:
        MobiMetadata object or None if extraction fails.
    """
    if not path.exists() or path.suffix.lower() != ".mobi":
        return None

    try:
        import fitz
    except ImportError:
        logger.warning("PyMuPDF (fitz) not available for MOBI extraction")
        return None

    # Check filename for ISBN first
    filename_isbns = extract_all_isbns(path.stem)
    if filename_isbns:
        logger.debug("Found ISBN(s) {} in filename of {}", filename_isbns, path.name)

    # Calculate file size
    file_size_mb = path.stat().st_size / (1024 * 1024)

    try:
        # Open MOBI file with PyMuPDF
        doc = fitz.open(path)

        # Extract metadata
        metadata = doc.metadata or {}
        title = _extract_title_from_mobi_metadata(metadata)
        author = metadata.get("author") or metadata.get("Author")

        # Scan pages for ISBNs
        all_isbns = _scan_mobi_pages_for_isbns(doc, filename_isbns)

        if all_isbns:
            logger.debug("Found {} ISBN(s) in {}", len(all_isbns), path.name)

        doc.close()

        return MobiMetadata(
            title=title,
            author=author,
            isbn=all_isbns[0] if all_isbns else None,
            isbns=all_isbns,
            file_size_mb=file_size_mb,
        )

    except (OSError, RuntimeError) as e:
        logger.debug("Failed to extract MOBI metadata from {}: {}", path.name, e)
        # Return partial metadata if we found ISBN in filename
        if filename_isbns:
            return MobiMetadata(
                title=None,
                isbn=filename_isbns[0],
                isbns=filename_isbns,
                file_size_mb=file_size_mb,
            )
        return None
