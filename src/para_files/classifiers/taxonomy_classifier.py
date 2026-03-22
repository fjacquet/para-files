"""Taxonomy-based classifier using documents.json.

Replaces DomainKB + SemanticRouter with a unified classifier that matches:
1. Issuers - Known entities with patterns (90% confidence)
2. Keywords - Document type keywords (85% confidence)
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from difflib import SequenceMatcher
from functools import lru_cache
from typing import TYPE_CHECKING, ClassVar

from loguru import logger

from para_files.classifiers.base import BaseClassifier
from para_files.taxonomies.loader import TaxonomyLoader, get_taxonomy_loader
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
)
from para_files.utils.placeholder_resolver import clean_unreplaced_placeholders


if TYPE_CHECKING:
    from para_files.taxonomies.models import DocumentCategory, DocumentType, Issuer


def normalize_ocr_text(text: str) -> str:
    """Normalize OCR-corrupted text by collapsing isolated single characters.

    Handles common OCR issues like "bi gl i etto" → "biglietto".
    This occurs when OCR inserts spaces between characters.

    Args:
        text: Input text potentially with OCR corruption

    Returns:
        Normalized text with collapsed single-char sequences
    """
    # Pattern: single letter followed by space followed by single letter
    # Replace iteratively until no more matches
    result = text
    prev_result = None

    while prev_result != result:
        prev_result = result
        # Collapse: "a b" → "ab" when both are single lowercase letters
        result = re.sub(r"\b([a-z])\s+([a-z])\b", r"\1\2", result)
        # Also handle uppercase
        result = re.sub(r"\b([A-Z])\s+([A-Z])\b", r"\1\2", result)

    return result


@lru_cache(maxsize=128)
def _normalize_cached(text: str) -> str:
    """Cached version of normalize_ocr_text for performance."""
    return normalize_ocr_text(text)


class TaxonomyClassifier(BaseClassifier):
    """Classifier using documents.json taxonomy for issuers and keywords.

    Matching priority:
    1. Issuer patterns (90% confidence) - Most specific
    2. Keyword matching (85% confidence) - Semantic match

    Path resolution uses para_pattern from category/document with placeholders:
    - {year} - Extracted from content or file date
    - {issuer} - Matched issuer name
    - {month}, {day} - From file date
    """

    # Confidence levels
    ISSUER_CONFIDENCE = 0.90
    KEYWORD_CONFIDENCE = 0.85

    # Header length for priority matching
    HEADER_LENGTH = 1000
    # Keyword header boost threshold (shorter than issuer matching)
    KEYWORD_HEADER_THRESHOLD = 500
    # Length normalization factor for keyword scoring
    KEYWORD_LENGTH_FACTOR = 50

    # Minimum path parts for retention prefix injection (PARA prefix + category)
    MIN_PATH_PARTS_FOR_PREFIX = 2

    # Fuzzy matching configuration
    FUZZY_MATCH_THRESHOLD = 0.85  # Minimum similarity ratio for fuzzy matches
    FUZZY_CONFIDENCE_MULTIPLIER = 0.95  # Confidence penalty for fuzzy matches

    # Retention prefix mapping for folder names (no prefix for permanent items)
    RETENTION_PREFIXES: ClassVar[dict[str, str]] = {
        "permanent": "",  # No prefix - goes to 3_Resources
        "retirement": "ret_",
        "10_years": "10y_",
        "5_years": "5y_",
        "contract_duration": "ctr_",
        "warranty_2_years": "2y_",
    }

    def __init__(
        self,
        loader: TaxonomyLoader | None = None,
    ) -> None:
        """Initialize with taxonomy loader.

        Args:
            loader: TaxonomyLoader instance (uses global cached if None)
        """
        self._loader = loader or get_taxonomy_loader()
        self._issuer_cache: dict[str, tuple[Issuer, DocumentType, DocumentCategory]] | None = None
        self._keyword_cache: dict[str, tuple[DocumentType, DocumentCategory, list[str]]] | None = (
            None
        )

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "TaxonomyClassifier"

    @property
    def source(self) -> ClassificationSource:
        """Return classification source."""
        return ClassificationSource.TAXONOMY_CLASSIFIER

    @property
    def default_confidence(self) -> float:
        """Return default confidence (issuer match)."""
        return self.ISSUER_CONFIDENCE

    def _build_issuer_cache(self) -> dict[str, tuple[Issuer, DocumentType, DocumentCategory]]:
        """Build cache of issuer patterns to issuer/doc/category tuples."""
        if self._issuer_cache is not None:
            return self._issuer_cache

        taxonomy = self._loader.load_documents()
        cache: dict[str, tuple[Issuer, DocumentType, DocumentCategory]] = {}

        for issuer, doc_type, category in taxonomy.get_all_issuers():
            for pattern in issuer.patterns:
                # Store with lowercase pattern as key
                cache[pattern.lower()] = (issuer, doc_type, category)

        self._issuer_cache = cache
        return cache

    def _build_keyword_cache(
        self,
    ) -> dict[str, tuple[DocumentType, DocumentCategory, list[str]]]:
        """Build cache of keywords to doc/category/required_context tuples."""
        if self._keyword_cache is not None:
            return self._keyword_cache

        taxonomy = self._loader.load_documents()
        self._keyword_cache = taxonomy.get_all_keywords()
        return self._keyword_cache

    def _fuzzy_match_issuer(
        self,
        text: str,
    ) -> tuple[Issuer, DocumentType, DocumentCategory, float] | None:
        """Fuzzy match text against known issuer names.

        Uses difflib.SequenceMatcher to find similar issuer names.
        Only returns matches above FUZZY_MATCH_THRESHOLD.

        Args:
            text: Text to search for issuer-like patterns

        Returns:
            Tuple of (Issuer, DocumentType, DocumentCategory, similarity_ratio) or None
        """
        cache = self._build_issuer_cache()
        if not cache:
            return None

        text_lower = text.lower()
        best_match: tuple[Issuer, DocumentType, DocumentCategory, float] | None = None
        best_ratio = 0.0

        # Extract words from text that could be issuer names (3+ chars)
        words = list(re.findall(r"\b[a-zA-Z]{3,}\b", text_lower))

        for word in words:
            for pattern, (issuer, doc_type, category) in cache.items():
                # Compare word against each issuer pattern
                ratio = SequenceMatcher(None, word, pattern).ratio()
                if ratio >= self.FUZZY_MATCH_THRESHOLD and ratio > best_ratio:
                    best_ratio = ratio
                    best_match = (issuer, doc_type, category, ratio)

        return best_match

    def _match_issuer(
        self,
        content: str,
        filename: str | None = None,
        metadata: FileMetadata | None = None,
    ) -> tuple[Issuer, DocumentType, DocumentCategory] | None:
        """Match content against known issuer patterns.

        Priority: pdf_author > filename > header (first 1000 chars) > full content
        Within each area, the issuer appearing earliest (by position) wins.

        Args:
            content: Text content to search
            filename: Optional filename for priority matching
            metadata: Optional file metadata with PDF author/title

        Returns:
            Tuple of (Issuer, DocumentType, DocumentCategory) if matched, None otherwise
        """
        cache = self._build_issuer_cache()
        if not cache:
            return None

        # Search priority: pdf_author first (most reliable), then filename, then content
        search_areas: list[tuple[str, str]] = []

        # PDF author is the most reliable source for issuer identification
        if metadata and metadata.pdf_author:
            search_areas.append(("pdf_author", metadata.pdf_author.lower()))

        if filename:
            search_areas.append(("filename", filename.lower()))

        if content:
            header = content[: self.HEADER_LENGTH].lower()
            search_areas.append(("header", header))
            if len(content) > self.HEADER_LENGTH:
                search_areas.append(("content", content.lower()))

        # Try each search area in priority order
        for _area_name, text in search_areas:
            # Find ALL matches with their positions, then return the earliest
            matches: list[tuple[int, Issuer, DocumentType, DocumentCategory]] = []

            for pattern, (issuer, doc_type, category) in cache.items():
                # Use word boundary matching for accuracy
                pattern_regex = r"\b" + re.escape(pattern) + r"\b"
                match = re.search(pattern_regex, text, re.IGNORECASE)
                if match:
                    matches.append((match.start(), issuer, doc_type, category))

            if matches:
                # Return the match with the earliest position
                matches.sort(key=lambda x: x[0])
                _, issuer, doc_type, category = matches[0]
                return (issuer, doc_type, category)

        return None

    def _has_required_context(self, content_lower: str, required_context: list[str]) -> bool:
        """Check if at least one required context word is present.

        Args:
            content_lower: Lowercase content to search
            required_context: List of context words (at least one must match)

        Returns:
            True if no context required OR at least one context word found
        """
        if not required_context:
            return True  # No context required

        for context_word in required_context:
            pattern = r"\b" + re.escape(context_word.lower()) + r"\b"
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True

        return False

    def _enrich_content_with_metadata(
        self,
        content: str,
        metadata: FileMetadata | None,
    ) -> str:
        """Prepend PDF title and subject to content for better keyword matching.

        Args:
            content: Original text content
            metadata: Optional file metadata with PDF title/subject

        Returns:
            Enriched content string
        """
        if not metadata:
            return content

        pdf_parts = []
        if metadata.pdf_title:
            pdf_parts.append(metadata.pdf_title)
        if metadata.pdf_subject:
            pdf_parts.append(metadata.pdf_subject)

        if pdf_parts:
            return " ".join(pdf_parts) + " " + content
        return content

    def _calculate_keyword_score(
        self,
        position: int,
        content_length: int,
        keyword_length: int,
        *,
        match_in_normalized: bool,
    ) -> float:
        """Calculate score for a keyword match based on position and length.

        Args:
            position: Match position in content
            content_length: Total content length
            keyword_length: Length of matched keyword
            match_in_normalized: Whether match was in OCR-normalized content

        Returns:
            Score value (higher is better)
        """
        # Score based on position (earlier = better)
        position_score = 1.0 - (position / content_length) if content_length > 0 else 0.5

        # Boost for header matches
        header_boost = 1.5 if position < self.KEYWORD_HEADER_THRESHOLD else 1.0

        # Boost for longer keywords (more specific)
        length_boost = 1.0 + (keyword_length / self.KEYWORD_LENGTH_FACTOR)

        # Slight penalty for matches only in normalized content (less certain)
        ocr_penalty = 0.95 if match_in_normalized else 1.0

        return position_score * header_boost * length_boost * ocr_penalty

    def _match_keywords(
        self,
        content: str,
        metadata: FileMetadata | None = None,
    ) -> tuple[DocumentType, DocumentCategory, str] | None:
        """Match content against document type keywords with position weighting and AND logic.

        Keywords found in the header (first 500 chars) are weighted higher.
        Longer keywords are weighted higher (more specific).
        If required_context is specified, at least one context word must also be present.
        Also tries matching against OCR-normalized text for corrupted PDFs.
        PDF title/subject are prepended to content for better matching.

        Args:
            content: Text content to search
            metadata: Optional file metadata with PDF title/subject

        Returns:
            Tuple of (DocumentType, DocumentCategory, matched_keyword) if matched, None otherwise
        """
        cache = self._build_keyword_cache()
        if not cache:
            return None

        # Enrich content with PDF metadata
        enriched_content = self._enrich_content_with_metadata(content, metadata)
        content_lower = enriched_content.lower()
        content_length = len(content_lower)

        # Prepare normalized version for OCR-corrupted text
        normalized_content = None
        if re.search(r"\b[a-z]\s+[a-z]\s+[a-z]\b", content_lower):
            normalized_content = _normalize_cached(content_lower)

        # Find all matches with scores
        matches: list[tuple[float, str, DocumentType, DocumentCategory]] = []

        for keyword, (doc_type, category, required_context) in cache.items():
            # Check AND logic: required_context must be present
            has_context = self._has_required_context(content_lower, required_context)
            if not has_context and normalized_content:
                has_context = self._has_required_context(normalized_content, required_context)
            if not has_context:
                continue

            pattern = r"\b" + re.escape(keyword) + r"\b"
            match = re.search(pattern, content_lower, re.IGNORECASE)
            match_in_normalized = False

            if not match and normalized_content:
                match = re.search(pattern, normalized_content, re.IGNORECASE)
                match_in_normalized = True

            if match:
                score = self._calculate_keyword_score(
                    match.start(),
                    content_length,
                    len(keyword),
                    match_in_normalized=match_in_normalized,
                )
                matches.append((score, keyword, doc_type, category))

        if not matches:
            return None

        # Return best match (highest score)
        matches.sort(key=lambda x: x[0], reverse=True)
        _, keyword, doc_type, category = matches[0]
        return (doc_type, category, keyword)

    def _extract_year(self, content: str, metadata: FileMetadata | None = None) -> str:
        """Extract year from content or metadata.

        Priority: Content patterns > file date

        Args:
            content: Text content to search
            metadata: Optional file metadata

        Returns:
            Year string (YYYY) or current year as fallback
        """
        # Try common date patterns in content
        year_patterns = [
            r"\b(20[0-9]{2})\b",  # 2000-2099
            r"\b(19[0-9]{2})\b",  # 1900-1999
        ]

        for pattern in year_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)

        # Fall back to file date
        if metadata and metadata.best_date:
            return str(metadata.best_date.year)

        # Default to current year
        return str(datetime.now(UTC).year)

    def _resolve_pattern(
        self,
        pattern: str,
        issuer_name: str | None = None,
        year: str | None = None,
        metadata: FileMetadata | None = None,
        retention: str | None = None,
    ) -> str | None:
        """Resolve placeholders in para_pattern and inject retention suffix.

        Placeholders:
        - {year} - Year from content or file
        - {issuer} - Issuer name
        - {month} - Month (MM)
        - {day} - Day (DD)
        - {YYYY}, {MM}, {DD} - Alternative format

        Retention prefixes are added to the category folder:
        - permanent → (no prefix, stays in 3_Resources)
        - 10_years → 10y_
        - 5_years → 5y_
        - etc.

        Args:
            pattern: Path pattern with placeholders
            issuer_name: Matched issuer name
            year: Extracted year
            metadata: File metadata for dates
            retention: Retention policy key (e.g., "10_years", "permanent")

        Returns:
            Resolved path string with retention suffix
        """
        result = pattern

        # Inject retention prefix into the category folder
        if retention and retention in self.RETENTION_PREFIXES:
            prefix = self.RETENTION_PREFIXES[retention]
            # Pattern like "4_Archives/fiscalite/{year}" → "4_Archives/10y_fiscalite/{year}"
            # Find the first path component after PARA prefix and add prefix
            parts = result.split("/")
            if len(parts) >= self.MIN_PATH_PARTS_FOR_PREFIX and prefix:
                # parts[0] = "4_Archives" or "3_Resources", parts[1] = category
                # Add prefix to category (parts[1])
                category_part = parts[1]
                # Only add if not already has a prefix
                existing_prefixes = [p for p in self.RETENTION_PREFIXES.values() if p]
                if not any(category_part.startswith(p) for p in existing_prefixes):
                    parts[1] = prefix + category_part
                    result = "/".join(parts)

        # Year placeholder
        if year:
            result = result.replace("{year}", year)
            result = result.replace("{YYYY}", year)

        # Issuer placeholder
        if issuer_name:
            result = result.replace("{issuer}", issuer_name)

        # Date placeholders from metadata
        if metadata and metadata.best_date:
            date = metadata.best_date
            result = result.replace("{month}", f"{date.month:02d}")
            result = result.replace("{MM}", f"{date.month:02d}")
            result = result.replace("{day}", f"{date.day:02d}")
            result = result.replace("{DD}", f"{date.day:02d}")

        cleaned = clean_unreplaced_placeholders(result)
        if cleaned is None:
            logger.warning("Placeholder resolution failed for taxonomy match: {}", result)
            return None
        return cleaned

    def classify(  # noqa: PLR0911
        self,
        content: str,
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        """Classify content using taxonomy.

        Args:
            content: Text content to classify
            metadata: Optional file metadata (including PDF author/title/subject)

        Returns:
            ClassificationResult if matched, None otherwise
        """
        filename = metadata.filename if metadata else None

        # Priority 1: Exact issuer matching (90% confidence)
        # Checks pdf_author, filename, then content
        issuer_match = self._match_issuer(content, filename, metadata)
        if issuer_match:
            issuer, doc_type, category = issuer_match

            # Use document-level pattern if set, else category pattern
            pattern = doc_type.para_pattern or category.para_pattern

            year = self._extract_year(content, metadata)
            resolved_path = self._resolve_pattern(
                pattern,
                issuer_name=issuer.name,
                year=year,
                metadata=metadata,
                retention=doc_type.retention,
            )
            if resolved_path is None:
                return None

            return ClassificationResult(
                category=resolved_path,
                confidence=Confidence(
                    value=self.ISSUER_CONFIDENCE,
                    source=self.source,
                ),
                route_name=f"{category.id}/{doc_type.sub_id}/{issuer.name}",
                extracted_params={
                    "issuer": issuer.name,
                    "year": year,
                    "category_id": category.id,
                    "doc_type": doc_type.sub_id,
                    "retention": doc_type.retention,
                },
            )

        # Priority 2: Keyword matching (85% confidence)
        # Checks pdf_title/subject, then content
        keyword_match = self._match_keywords(content, metadata)
        if keyword_match:
            doc_type, category, matched_keyword = keyword_match

            # Use document-level pattern if set, else category pattern
            pattern = doc_type.para_pattern or category.para_pattern

            year = self._extract_year(content, metadata)
            resolved_path = self._resolve_pattern(
                pattern,
                year=year,
                metadata=metadata,
                retention=doc_type.retention,
            )
            if resolved_path is None:
                return None

            return ClassificationResult(
                category=resolved_path,
                confidence=Confidence(
                    value=self.KEYWORD_CONFIDENCE,
                    source=self.source,
                ),
                route_name=f"{category.id}/{doc_type.sub_id}",
                extracted_params={
                    "keyword": matched_keyword,
                    "year": year,
                    "category_id": category.id,
                    "doc_type": doc_type.sub_id,
                    "retention": doc_type.retention,
                },
            )

        # Priority 3: Fuzzy issuer matching (confidence * 0.95)
        # Fallback for misspellings and OCR errors
        fuzzy_match = self._fuzzy_match_issuer(content)
        if fuzzy_match:
            issuer, doc_type, category, similarity = fuzzy_match

            # Use document-level pattern if set, else category pattern
            pattern = doc_type.para_pattern or category.para_pattern

            year = self._extract_year(content, metadata)
            resolved_path = self._resolve_pattern(
                pattern,
                issuer_name=issuer.name,
                year=year,
                metadata=metadata,
                retention=doc_type.retention,
            )
            if resolved_path is None:
                return None

            # Confidence = base issuer confidence * fuzzy multiplier * similarity
            fuzzy_confidence = (
                self.ISSUER_CONFIDENCE * self.FUZZY_CONFIDENCE_MULTIPLIER * similarity
            )

            return ClassificationResult(
                category=resolved_path,
                confidence=Confidence(
                    value=fuzzy_confidence,
                    source=self.source,
                ),
                route_name=f"{category.id}/{doc_type.sub_id}/{issuer.name}",
                extracted_params={
                    "issuer": issuer.name,
                    "year": year,
                    "category_id": category.id,
                    "doc_type": doc_type.sub_id,
                    "retention": doc_type.retention,
                    "fuzzy_match": "true",
                    "fuzzy_similarity": f"{similarity:.2f}",
                },
            )

        return None


# Global cached instance
@lru_cache(maxsize=1)
def get_taxonomy_classifier() -> TaxonomyClassifier:
    """Get or create the global taxonomy classifier instance."""
    return TaxonomyClassifier()
