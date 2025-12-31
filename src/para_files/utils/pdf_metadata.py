"""PDF metadata extraction for book detection.

Extracts PDF metadata, page count, and ISBN for intelligent book classification.
Uses pypdf for efficient metadata access without reading full content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


@dataclass
class PdfMetadata:
    """Metadata extracted from a PDF file."""

    title: str | None = None
    author: str | None = None
    subject: str | None = None
    creator: str | None = None
    producer: str | None = None
    page_count: int | None = None
    isbn: str | None = None
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
    try:
        import isbnlib  # type: ignore[import-untyped]

        # isbnlib has its own extraction function
        isbns = isbnlib.get_isbnlike(text)
        for candidate in isbns:
            canonical = isbnlib.canonical(candidate)
            if canonical and (isbnlib.is_isbn10(canonical) or isbnlib.is_isbn13(canonical)):
                result: str | None = isbnlib.to_isbn13(canonical)  # Normalize to ISBN-13
                return result
        return None  # noqa: TRY300

    except ImportError:
        # Fallback to regex-based extraction
        for pattern in ISBN_PATTERNS:
            for match in pattern.finditer(text):
                candidate = re.sub(r"[-\s]", "", match.group(1)).upper()
                # Basic length check
                if len(candidate) in (10, 13):
                    return candidate
        return None


def extract_pdf_metadata(path: Path, max_pages_for_isbn: int = 5) -> PdfMetadata | None:
    """Extract metadata from a PDF file.

    Reads PDF metadata fields and searches the first few pages for ISBN.

    Args:
        path: Path to the PDF file.
        max_pages_for_isbn: Maximum number of pages to search for ISBN.

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

        # Calculate file size in MB
        file_size_mb = path.stat().st_size / (1024 * 1024)

        # Search for ISBN in first few pages
        isbn = None
        pages_to_check = min(max_pages_for_isbn, page_count)

        for i in range(pages_to_check):
            try:
                page_text = reader.pages[i].extract_text() or ""
                found_isbn = extract_isbn(page_text)
                if found_isbn:
                    isbn = found_isbn
                    logger.debug("Found ISBN %s on page %d of %s", isbn, i + 1, path.name)
                    break
            except Exception:  # noqa: BLE001, S112
                # Skip pages that fail to extract (corrupted/encrypted pages)
                continue

        return PdfMetadata(
            title=str(title) if title else None,
            author=str(author) if author else None,
            subject=str(subject) if subject else None,
            creator=str(creator) if creator else None,
            producer=str(producer) if producer else None,
            page_count=page_count,
            isbn=isbn,
            file_size_mb=file_size_mb,
        )

    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to extract PDF metadata from %s: %s", path, e)
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
