"""PDF metadata extraction for book detection.

Extracts PDF metadata, page count, and ISBN for intelligent book classification.
Uses pypdf for efficient metadata access without reading full content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger


# Track paths that already triggered a warning to avoid duplicate log lines
# when multiple callers (file_utils, book_detector) process the same file.
_warned_paths: set[Path] = set()


@dataclass
class PdfMetadata:
    """Metadata extracted from a PDF file."""

    title: str | None = None
    author: str | None = None
    subject: str | None = None
    creator: str | None = None
    producer: str | None = None
    page_count: int | None = None
    isbn: str | None = None  # First ISBN found (for backwards compatibility)
    isbns: list[str] = field(default_factory=list)  # All ISBNs found in order
    file_size_mb: float = 0.0


# ISBN extraction patterns
# ISBN-13: 978-0-596-51774-8 or 9780596517748
# ISBN-10: 0-596-51774-X or 0596517742
ISBN_PATTERNS = [
    # ISBN-13 with prefix and separators
    re.compile(
        r"ISBN[:\s-]*(?:13)?[:\s-]*(97[89][-\s]?\d{1,5}[-\s]?\d{1,7}[-\s]?\d{1,7}[-\s]?\d)",
        re.IGNORECASE,
    ),
    # ISBN-10 with prefix and separators
    re.compile(
        r"ISBN[:\s-]*(?:10)?[:\s-]*(\d{1,5}[-\s]?\d{1,7}[-\s]?\d{1,7}[-\s]?[\dXx])",
        re.IGNORECASE,
    ),
    # ISBN-13 without prefix (just digits starting with 978/979)
    re.compile(r"\b(97[89]\d{10})\b"),
    # ISBN-10 without prefix (10 digits ending with digit or X)
    re.compile(r"\b(\d{9}[\dXx])\b"),
]


def extract_isbn(text: str) -> str | None:
    """Extract the first valid ISBN from text.

    Uses isbnlib for validation if available, otherwise uses regex patterns.

    Args:
        text: Text content to search for ISBN.

    Returns:
        Normalized ISBN (digits only) or None if not found.
    """
    isbns = extract_all_isbns(text)
    return isbns[0] if isbns else None


def extract_all_isbns(text: str) -> list[str]:  # noqa: C901
    """Extract all valid unique ISBNs from text.

    Uses regex patterns to find candidates, then validates with isbnlib.
    This catches ISBNs with unusual formatting that isbnlib.get_isbnlike() misses.

    Args:
        text: Text content to search for ISBNs.

    Returns:
        List of unique normalized ISBN-13s in order of appearance.
    """
    seen: set[str] = set()
    result: list[str] = []

    # Step 1: Use regex patterns to find all candidates (catches unusual formats)
    regex_candidates: list[str] = []
    for pattern in ISBN_PATTERNS:
        for match in pattern.finditer(text):
            # Remove separators to get raw digits
            candidate = re.sub(r"[-\s]", "", match.group(1)).upper()
            if len(candidate) in (10, 13) and candidate not in regex_candidates:
                regex_candidates.append(candidate)

    try:
        import isbnlib  # type: ignore[import-untyped]

        # Step 2: Also get candidates from isbnlib (may find some regex missed)
        isbnlib_candidates = isbnlib.get_isbnlike(text)
        for candidate in isbnlib_candidates:
            canonical = isbnlib.canonical(candidate)
            if canonical and canonical not in regex_candidates:
                regex_candidates.append(canonical)

        # Step 3: Validate all candidates with isbnlib
        for candidate in regex_candidates:
            canonical = isbnlib.canonical(candidate)
            if canonical and (isbnlib.is_isbn10(canonical) or isbnlib.is_isbn13(canonical)):
                isbn13: str | None = isbnlib.to_isbn13(canonical)
                if isbn13 and isbn13 not in seen:
                    seen.add(isbn13)
                    result.append(isbn13)

    except ImportError:
        # No isbnlib: just use regex candidates as-is
        for candidate in regex_candidates:
            if candidate not in seen:
                seen.add(candidate)
                result.append(candidate)

    return result


def extract_pdf_metadata(path: Path, max_pages_for_isbn: int = 20) -> PdfMetadata | None:  # noqa: C901
    """Extract metadata from a PDF file.

    Reads PDF metadata fields and searches the first pages for all ISBNs.
    ISBN typically appears on copyright page which can be up to page 15.

    Args:
        path: Path to the PDF file.
        max_pages_for_isbn: Maximum number of pages to search for ISBNs.

    Returns:
        PdfMetadata object or None if extraction fails.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning("pypdf not available for PDF metadata extraction")
        return None

    if not path.exists() or path.suffix.lower() != ".pdf":
        return None

    # Check filename for ISBN FIRST (common pattern: "9781234567890-Title.pdf")
    # This works even if the PDF is corrupted
    filename_isbns = extract_all_isbns(path.stem)  # stem = filename without extension
    if filename_isbns:
        logger.debug("Found ISBN(s) {} in filename of {}", filename_isbns, path.name)

    # Calculate file size in MB (works even if PDF is corrupted)
    file_size_mb = path.stat().st_size / (1024 * 1024)

    try:
        reader = PdfReader(path)
        meta: dict[str, object] = dict(reader.metadata) if reader.metadata else {}

        # Extract standard metadata fields
        title = meta.get("/Title")
        author = meta.get("/Author")
        subject = meta.get("/Subject")
        creator = meta.get("/Creator")
        producer = meta.get("/Producer")
        page_count = len(reader.pages)

        # Collect all ISBNs: start with filename ISBNs, then add from content
        all_isbns: list[str] = list(filename_isbns)
        seen_isbns: set[str] = set(filename_isbns)

        # Search for ISBNs in content
        pages_to_check = min(max_pages_for_isbn, page_count)
        for i in range(pages_to_check):
            try:
                page_text = reader.pages[i].extract_text() or ""
                page_isbns = extract_all_isbns(page_text)
                for found_isbn in page_isbns:
                    if found_isbn not in seen_isbns:
                        seen_isbns.add(found_isbn)
                        all_isbns.append(found_isbn)
                        logger.debug("Found ISBN {} on page {} of {}", found_isbn, i + 1, path.name)
            except Exception as e:  # noqa: BLE001
                logger.debug(
                    "Failed to extract text from page {} of {}: {} {}",
                    i + 1,
                    path.name,
                    type(e).__name__,
                    e,
                )
                continue

        if all_isbns:
            logger.debug("Total ISBNs found in {}: {}", path.name, all_isbns)

        return PdfMetadata(
            title=str(title) if title else None,
            author=str(author) if author else None,
            subject=str(subject) if subject else None,
            creator=str(creator) if creator else None,
            producer=str(producer) if producer else None,
            page_count=page_count,
            isbn=all_isbns[0] if all_isbns else None,  # First for backwards compat
            isbns=all_isbns,
            file_size_mb=file_size_mb,
        )

    except Exception as e:  # noqa: BLE001
        if path not in _warned_paths:
            _warned_paths.add(path)
            logger.warning("Failed to extract PDF metadata from {}: {}", path, e)
        # If we found ISBN in filename, return partial metadata
        if filename_isbns:
            logger.info("Returning partial metadata with filename ISBN for {}", path.name)
            return PdfMetadata(
                title=None,
                author=None,
                subject=None,
                creator=None,
                producer=None,
                page_count=0,
                isbn=filename_isbns[0],
                isbns=filename_isbns,
                file_size_mb=file_size_mb,
            )
        return None


# Book-related keywords in titles
BOOK_TITLE_KEYWORDS = [
    "edition",
    "guide",
    "handbook",
    "manual",
    "cookbook",
    "reference",
    "introduction to",
    "learning",
    "mastering",
    "professional",
    "practical",
    "beginning",
    "advanced",
    "complete",
    "definitive",
    "fundamentals",
    "essentials",
    "programming",
    "for dummies",
    "in action",
    "in depth",
    "head first",
]

# Creator tools that indicate a book
BOOK_CREATOR_PATTERNS = [
    "latex",
    "tex",
    "indesign",
    "acrobat distiller",
    "calibre",
    "quarkxpress",
    "framemaker",
]


def contains_book_keywords(title: str) -> bool:
    """Check if a title contains book-related keywords.

    Args:
        title: PDF title to check.

    Returns:
        True if title contains book-like keywords.
    """
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in BOOK_TITLE_KEYWORDS)


def is_book_creator(creator: str) -> bool:
    """Check if the PDF creator tool suggests this is a book.

    Args:
        creator: PDF creator field value.

    Returns:
        True if creator suggests book production.
    """
    creator_lower = creator.lower()
    return any(pattern in creator_lower for pattern in BOOK_CREATOR_PATTERNS)
