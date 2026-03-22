"""ISBN lookup service for enriching book metadata.

Uses isbnlib for robust ISBN handling and metadata lookup from multiple sources
(Google Books, Open Library, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger


# ISBN-10 has exactly 10 characters
ISBN_10_LENGTH = 10

# isbnlib can raise various exceptions: network errors, parse errors, import failures,
# and internal RuntimeError from its decorators/caching layer
_ISBNLIB_ERRORS = (
    ConnectionError, TimeoutError, OSError, ValueError,
    KeyError, ImportError, RuntimeError,
)


@dataclass
class BookInfo:
    """Book information retrieved from ISBN lookup."""

    title: str | None = None
    authors: list[str] = field(default_factory=list)
    publishers: list[str] = field(default_factory=list)
    publish_date: str | None = None
    subjects: list[str] = field(default_factory=list)
    isbn_10: str | None = None
    isbn_13: str | None = None
    language: str | None = None
    description: str | None = None
    cover_url: str | None = None


def lookup_isbn(isbn: str, service: str = "default") -> BookInfo | None:  # noqa: C901
    """Look up book information by ISBN using isbnlib.

    Tries multiple metadata services for best results.

    Args:
        isbn: ISBN-10 or ISBN-13 (with or without separators).
        service: Metadata service to use ('goob' for Google, 'openl' for Open Library,
                 'wiki' for Wikipedia, or 'default' to try all).

    Returns:
        BookInfo with enriched metadata, or None if lookup fails.
    """
    try:
        import isbnlib  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("isbnlib not available for ISBN lookup")
        return None

    # Normalize and validate ISBN
    canonical = isbnlib.canonical(isbn)
    if not canonical:
        logger.debug("Invalid ISBN: {}", isbn)
        return None

    if not isbnlib.is_isbn10(canonical) and not isbnlib.is_isbn13(canonical):
        logger.debug("ISBN validation failed: {}", isbn)
        return None

    # Convert to ISBN-13 for consistency
    isbn_13 = isbnlib.to_isbn13(canonical)
    isbn_10 = isbnlib.to_isbn10(canonical) if len(canonical) == ISBN_10_LENGTH else None

    # Try to get metadata
    # Order: Open Library (best for books), Wikipedia, Google Books (often has wrong data)
    meta = None
    services_to_try = ["openl", "wiki", "goob"] if service == "default" else [service]

    for svc in services_to_try:
        try:
            meta = isbnlib.meta(canonical, service=svc)
            if meta and meta.get("Title"):
                logger.debug("Found metadata via {} for ISBN {}", svc, isbn)
                break
        except _ISBNLIB_ERRORS as e:
            logger.debug("Service {} failed for ISBN {}: {}", svc, isbn, e)
            continue

    if not meta or not meta.get("Title"):
        logger.debug("No metadata found for ISBN {}", isbn)
        return None

    # Build BookInfo from isbnlib metadata
    info = BookInfo(
        title=meta.get("Title"),
        authors=meta.get("Authors", []),
        publishers=[meta.get("Publisher")] if meta.get("Publisher") else [],
        publish_date=meta.get("Year"),
        language=meta.get("Language"),
        isbn_10=isbn_10,
        isbn_13=isbn_13,
    )

    # Try to get description (optional enrichment)
    try:
        desc = isbnlib.desc(canonical)
        if desc:
            info.description = desc
    except _ISBNLIB_ERRORS as e:
        logger.warning(
            "ISBN description enrichment failed for {}: {} {}",
            canonical,
            type(e).__name__,
            e,
        )

    # Try to get cover URL (optional enrichment)
    try:
        cover = isbnlib.cover(canonical)
        if cover and "thumbnail" in cover:
            info.cover_url = cover["thumbnail"]
    except _ISBNLIB_ERRORS as e:
        logger.warning(
            "ISBN cover URL enrichment failed for {}: {} {}",
            canonical,
            type(e).__name__,
            e,
        )

    # Extract subjects from description if available
    if info.description:
        info.subjects = _extract_subjects_from_description(info.description)

    logger.debug(
        "Found book: %s by %s",
        info.title,
        ", ".join(info.authors) if info.authors else "Unknown",
    )

    return info


def _extract_subjects_from_description(description: str) -> list[str]:
    """Extract potential subject keywords from a book description.

    Simple heuristic extraction - looks for technical terms.

    Args:
        description: Book description text.

    Returns:
        List of extracted subject keywords.
    """
    # Technical keywords to look for
    tech_keywords = [
        "python",
        "java",
        "javascript",
        "typescript",
        "go",
        "golang",
        "rust",
        "kubernetes",
        "docker",
        "linux",
        "devops",
        "cloud",
        "aws",
        "azure",
        "machine learning",
        "deep learning",
        "artificial intelligence",
        "database",
        "sql",
        "nosql",
        "mongodb",
        "postgresql",
        "security",
        "networking",
        "microservices",
        "api",
        "react",
        "angular",
        "vue",
        "node.js",
        "fastapi",
        "django",
    ]

    description_lower = description.lower()
    return [keyword.title() for keyword in tech_keywords if keyword in description_lower]


def validate_isbn(isbn: str) -> bool:
    """Check if a string is a valid ISBN.

    Args:
        isbn: String to validate.

    Returns:
        True if valid ISBN-10 or ISBN-13.
    """
    try:
        import isbnlib

        canonical = isbnlib.canonical(isbn)
        return bool(canonical and (isbnlib.is_isbn10(canonical) or isbnlib.is_isbn13(canonical)))
    except _ISBNLIB_ERRORS as e:
        logger.debug("validate_isbn failed for {!r}: {} {}", isbn, type(e).__name__, e)
        return False


def normalize_isbn(isbn: str) -> str | None:
    """Normalize an ISBN to canonical form (digits only).

    Args:
        isbn: ISBN with possible separators.

    Returns:
        Canonical ISBN or None if invalid.
    """
    try:
        import isbnlib

        return isbnlib.canonical(isbn) or None
    except _ISBNLIB_ERRORS as e:
        logger.debug("normalize_isbn failed for {!r}: {} {}", isbn, type(e).__name__, e)
        return None


def isbn_to_isbn13(isbn: str) -> str | None:
    """Convert any ISBN to ISBN-13.

    Args:
        isbn: ISBN-10 or ISBN-13.

    Returns:
        ISBN-13 or None if invalid.
    """
    try:
        import isbnlib

        canonical = isbnlib.canonical(isbn)
        if canonical:
            result: str | None = isbnlib.to_isbn13(canonical)
            return result
    except _ISBNLIB_ERRORS as e:
        logger.debug("isbn_to_isbn13 failed for {!r}: {} {}", isbn, type(e).__name__, e)
    return None


# Minimum overlap ratio for title coherence validation
MIN_TITLE_OVERLAP_RATIO = 0.3


def _normalize_for_comparison(text: str) -> set[str]:
    """Normalize text for title comparison.

    Extracts significant words (3+ chars, lowercased) from text.

    Args:
        text: Text to normalize.

    Returns:
        Set of normalized words.
    """
    import re

    # Remove common file extensions and suffixes
    text = re.sub(r"\.(pdf|epub|mobi)$", "", text, flags=re.IGNORECASE)
    # Replace punctuation and separators with spaces
    text = re.sub(r"[_\-\.\[\]\(\)\{\}]", " ", text)
    # Extract words (3+ chars) and lowercase
    words = {w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", text)}
    # Remove very common words
    stopwords = {"the", "and", "for", "with", "from", "this", "that", "pdf", "book"}
    return words - stopwords


def is_title_coherent_with_filename(lookup_title: str, filename: str) -> bool:
    """Check if an ISBN lookup title matches the filename.

    Detects false positive ISBNs by verifying title coherence.
    For example, if filename is "Python_For_Dummies.pdf" but lookup returns
    "In Justice - David Iglesias", it's a false positive.

    Args:
        lookup_title: Title from ISBN lookup.
        filename: Original PDF filename.

    Returns:
        True if titles are coherent, False if likely false positive.
    """
    if not lookup_title or not filename:
        return False

    title_words = _normalize_for_comparison(lookup_title)
    filename_words = _normalize_for_comparison(filename)

    if not title_words or not filename_words:
        return False

    # Calculate word overlap
    common_words = title_words & filename_words
    # Need at least 1 significant word in common
    # OR the filename contains at least 30% of title words
    if common_words:
        return True

    # Check if filename is a partial match (e.g., abbreviations)
    overlap_ratio = len(common_words) / min(len(title_words), len(filename_words))
    return overlap_ratio >= MIN_TITLE_OVERLAP_RATIO


def find_matching_book_info(
    isbns: list[str],
    filename: str,
    *,
    require_coherence: bool = True,
) -> tuple[BookInfo | None, str | None]:
    """Find the first ISBN that returns a book matching the filename.

    Iterates through ISBNs and validates each lookup result against the filename
    to avoid false positives from promotional ISBNs embedded in PDFs.

    Args:
        isbns: List of ISBNs to try (in order of priority).
        filename: Original filename to validate against.
        require_coherence: If True, reject ISBNs with mismatched titles.

    Returns:
        Tuple of (BookInfo, matched_isbn) if found, (None, None) otherwise.
    """
    if not isbns:
        return None, None

    for candidate_isbn in isbns:
        book_info = lookup_isbn(candidate_isbn)
        if book_info is None or not book_info.title:
            continue

        # Validate title coherence with filename
        if require_coherence:
            if is_title_coherent_with_filename(book_info.title, filename):
                logger.debug(
                    "ISBN {} matches filename {} (title: {})",
                    candidate_isbn,
                    filename,
                    book_info.title,
                )
                return book_info, candidate_isbn
            logger.debug(
                "ISBN {} rejected - title '{}' doesn't match filename '{}'",
                candidate_isbn,
                book_info.title,
                filename,
            )
        else:
            # Accept first successful lookup
            return book_info, candidate_isbn

    return None, None


def infer_technology_from_subjects(
    subjects: list[str], known_technologies: list[str]
) -> str | None:
    """Infer technology category from book subjects.

    Args:
        subjects: List of subject strings from Open Library.
        known_technologies: List of known technology categories.

    Returns:
        Best matching technology or None.
    """
    if not subjects or not known_technologies:
        return None

    # Normalize for comparison
    subjects_lower = [s.lower() for s in subjects]
    subjects_text = " ".join(subjects_lower)

    # Direct match attempts
    for tech in known_technologies:
        tech_lower = tech.lower()
        # Check if tech appears in any subject
        if any(tech_lower in subj for subj in subjects_lower):
            return tech
        # Check for common variations
        if tech_lower in subjects_text:
            return tech

    # Common mappings for subjects that don't match directly
    subject_to_tech = {
        "python (computer program language)": "Python",
        "java (computer program language)": "Java",
        "javascript (computer program language)": "JavaScript",
        "c++ (computer program language)": "C++",
        "go (computer program language)": "Go",
        "kubernetes": "Kubernetes",
        "docker": "Containers",
        "linux": "Linux",
        "devops": "DevOps",
        "machine learning": "AI",
        "artificial intelligence": "AI",
        "cloud computing": "Cloud",
        "amazon web services": "Cloud",
        "microsoft azure": "Cloud",
        "database management": "Databases",
        "sql": "Databases",
        "network security": "Security",
        "cybersecurity": "Security",
        "computer security": "Security",
    }

    for subject in subjects_lower:
        for pattern, tech in subject_to_tech.items():
            if pattern in subject and tech in known_technologies:
                return tech

    return None
