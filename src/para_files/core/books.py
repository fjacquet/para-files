"""Signal 2, books: ISBN with a coherent lookup, else a book heuristic (spec §4.2).

An ISBN match is confidence 1.0 (may be green). The heuristic is 0.7 and stays yellow, since
the preliminary bake-off showed records pulled into the library without an ISBN.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable
from dataclasses import dataclass

from para_files.core.cache import Cache
from para_files.core.evidence import Evidence
from para_files.core.thema import lookup_thema_code, thema_folders
from para_files.core.tree import Tree
from para_files.utils.filename_sanitizer import sanitize_filename
from para_files.utils.isbn_lookup import BookInfo, is_title_coherent_with_filename, lookup_isbn


# Patterns that indicate book structure
BOOK_STRUCTURE_PATTERNS = [
    re.compile(r"table\s+of\s+contents", re.IGNORECASE),
    re.compile(r"chapter\s+\d+", re.IGNORECASE),
    re.compile(r"part\s+[IVX]+", re.IGNORECASE),
    re.compile(r"ISBN[:\s-]*[\d-]+", re.IGNORECASE),
    re.compile(r"copyright\s+\d{4}", re.IGNORECASE),
    re.compile(r"all\s+rights\s+reserved", re.IGNORECASE),
    re.compile(r"published\s+by", re.IGNORECASE),
    re.compile(r"first\s+edition", re.IGNORECASE),
    re.compile(r"\b(preface|foreword|acknowledgments)\b", re.IGNORECASE),
    re.compile(r"printed\s+in", re.IGNORECASE),
]


def score_book_structure(content: str) -> float:
    """Score content based on book structure patterns.

    Args:
        content: Text content to analyze.

    Returns:
        Score between 0.0 and 1.0 based on pattern matches.
    """
    matches = sum(1 for pattern in BOOK_STRUCTURE_PATTERNS if pattern.search(content))
    # 4+ patterns = max score of 1.0
    return min(matches / 4, 1.0)


Lookup = Callable[[str], BookInfo | None]

BOOK_EXTENSIONS = frozenset({".pdf", ".epub", ".mobi"})
EBOOK_EXTENSIONS = frozenset({".epub", ".mobi"})
ISBN_CONFIDENCE = 1.0
HEURISTIC_CONFIDENCE = 0.7
MAX_ISBNS = 3
MIN_PAGES = 50
MIN_STRUCTURE = 0.3
YEAR = re.compile(r"\d{4}")


@dataclass(frozen=True)
class BookMatch:
    """A book: its leaf, confidence, the ISBN that proved it, thema folders and a new name."""

    leaf_id: str
    confidence: float
    isbn: str | None = None
    thema: str | None = None
    suggested_name: str | None = None


def book_leaf(tree: Tree) -> str | None:
    """The library leaf whose subkey holds {thema}: where books go."""
    return next(
        (
            leaf_id
            for leaf_id, leaf in tree.leaves.items()
            if leaf.kind == "library" and "{thema}" in (leaf.subkey or "")
        ),
        None,
    )


def cached_lookup(isbn: str, cache: Cache, lookup: Lookup) -> BookInfo | None:
    """Lookup through the cache; only hits are stored, so a network failure is retried."""
    data = cache.get_isbn(isbn)
    if data is not None:
        return BookInfo(**data)
    info = lookup(isbn)
    if info is not None:
        cache.put_isbn(isbn, dataclasses.asdict(info))
    return info


def thema_segments(info: BookInfo) -> str | None:
    """Thema folders below the library root, e.g. 'U_Informatique/UB_Programmation'."""
    code = lookup_thema_code(info.subjects) if info.subjects else None
    if code is None:
        return None
    return thema_folders(code)


def suggested_name(info: BookInfo, ext: str) -> str | None:
    """'Author - Title (Year)' + ext, sanitized; None without a title."""
    if not info.title:
        return None
    base = f"{info.authors[0]} - {info.title}" if info.authors else info.title
    year = YEAR.match(info.publish_date or "")
    if year:
        base += f" ({year.group(0)})"
    return sanitize_filename(base) + ext


def _looks_like_book(evidence: Evidence) -> bool:
    if evidence.ext in EBOOK_EXTENSIONS:
        return True
    pages = evidence.doc_meta.get("page_count", "")
    return (
        pages.isdigit()
        and int(pages) >= MIN_PAGES
        and score_book_structure(evidence.text_preview) >= MIN_STRUCTURE
    )


def match_book(
    evidence: Evidence, tree: Tree, cache: Cache, lookup: Lookup = lookup_isbn
) -> BookMatch | None:
    """ISBN match (1.0), else heuristic match (0.7), else None."""
    if evidence.ext not in BOOK_EXTENSIONS:
        return None
    leaf_id = book_leaf(tree)
    if leaf_id is None:
        return None
    for isbn in evidence.isbns[:MAX_ISBNS]:
        info = cached_lookup(isbn, cache, lookup)
        if info and info.title and is_title_coherent_with_filename(info.title, evidence.name):
            return BookMatch(
                leaf_id,
                ISBN_CONFIDENCE,
                isbn,
                thema_segments(info),
                suggested_name(info, evidence.ext),
            )
    return BookMatch(leaf_id, HEURISTIC_CONFIDENCE) if _looks_like_book(evidence) else None
