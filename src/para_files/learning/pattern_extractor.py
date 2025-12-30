"""Pattern extractor for learning new classification rules.

This module analyzes correction history to extract patterns that can
improve classification accuracy, including new issuer patterns,
keywords, and filename patterns.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from para_files.learning.feedback_tracker import CorrectionRecord, FeedbackTracker


logger = logging.getLogger(__name__)

# Minimum occurrences to suggest a pattern
MIN_PATTERN_OCCURRENCES = 2

# Minimum length for valid issuer/prefix names
MIN_NAME_LENGTH = 3

# Common words to exclude from keyword extraction
STOPWORDS = frozenset({
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "en", "pour",
    "par", "sur", "avec", "dans", "ce", "cette", "ces", "au", "aux",
    "the", "a", "an", "of", "to", "in", "for", "on", "with", "at", "by",
    "from", "or", "and", "is", "it", "as", "be", "are", "was", "were",
    "pdf", "doc", "docx", "txt", "jpg", "png",
})


@dataclass
class PatternSuggestion:
    """A suggested pattern to add to the taxonomy.

    Attributes:
        pattern_type: Type of pattern ('issuer', 'keyword', 'filename').
        pattern: The suggested pattern string.
        category: Target category for this pattern.
        confidence: How confident we are in this suggestion (0-1).
        occurrences: Number of corrections supporting this pattern.
        examples: Example filenames that match this pattern.
    """

    pattern_type: str
    pattern: str
    category: str
    confidence: float
    occurrences: int
    examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_type": self.pattern_type,
            "pattern": self.pattern,
            "category": self.category,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "examples": self.examples,
        }


class PatternExtractor:
    """Extract patterns from correction history.

    Analyzes corrections to find:
    - New issuer patterns (company names in content/filenames)
    - New keywords (terms that correlate with categories)
    - Filename patterns (common prefixes/suffixes)
    """

    def __init__(self, tracker: FeedbackTracker) -> None:
        """Initialize the pattern extractor.

        Args:
            tracker: FeedbackTracker to get corrections from.
        """
        self._tracker = tracker

    def _collect_issuer_candidates(
        self,
        record: CorrectionRecord,
        candidates: Counter[str],
    ) -> None:
        """Collect issuer candidates from a single record."""
        # Check metadata author
        author = record.metadata.get("author", "")
        if author and self._is_valid_issuer(author):
            candidates[author.strip()] += 1

        # Check metadata creator
        creator = record.metadata.get("creator", "")
        if creator and self._is_valid_issuer(creator):
            candidates[creator.strip()] += 1

        # Extract from filename
        filename_issuer = self._extract_issuer_from_filename(record.filename)
        if filename_issuer:
            candidates[filename_issuer] += 1

    def _create_issuer_suggestion(
        self,
        issuer: str,
        count: int,
        category: str,
        records: list[CorrectionRecord],
    ) -> PatternSuggestion:
        """Create a pattern suggestion for an issuer."""
        examples = [
            r.filename for r in records
            if issuer.lower() in r.filename.lower()
            or issuer.lower() in r.metadata.get("author", "").lower()
        ][:5]

        return PatternSuggestion(
            pattern_type="issuer",
            pattern=issuer,
            category=category,
            confidence=min(0.9, 0.5 + count * 0.1),
            occurrences=count,
            examples=examples,
        )

    def extract_issuer_patterns(
        self,
        min_occurrences: int = MIN_PATTERN_OCCURRENCES,
    ) -> list[PatternSuggestion]:
        """Extract potential issuer patterns from corrections.

        Looks for company/organization names in metadata and content
        that appear consistently for a category.

        Args:
            min_occurrences: Minimum corrections to suggest a pattern.

        Returns:
            List of issuer pattern suggestions.
        """
        corrections = self._tracker.get_corrections()
        if not corrections:
            return []

        by_category = self._group_by_category(corrections)
        suggestions: list[PatternSuggestion] = []

        for category, records in by_category.items():
            issuer_candidates: Counter[str] = Counter()
            for record in records:
                self._collect_issuer_candidates(record, issuer_candidates)

            for issuer, count in issuer_candidates.items():
                if count >= min_occurrences:
                    suggestions.append(
                        self._create_issuer_suggestion(issuer, count, category, records)
                    )

        return suggestions

    def _group_by_category(
        self,
        corrections: list[CorrectionRecord],
    ) -> dict[str, list[CorrectionRecord]]:
        """Group corrections by corrected category."""
        by_category: dict[str, list[CorrectionRecord]] = {}
        for c in corrections:
            cat = c.corrected_category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(c)
        return by_category

    def extract_keyword_patterns(
        self,
        min_occurrences: int = MIN_PATTERN_OCCURRENCES,
    ) -> list[PatternSuggestion]:
        """Extract keyword patterns from correction content.

        Finds words that appear frequently in content for specific categories.

        Args:
            min_occurrences: Minimum corrections to suggest a pattern.

        Returns:
            List of keyword pattern suggestions.
        """
        corrections = self._tracker.get_corrections()
        if not corrections:
            return []

        by_category = self._group_by_category(corrections)

        suggestions: list[PatternSuggestion] = []

        for category, records in by_category.items():
            word_counts: Counter[str] = Counter()

            for record in records:
                # Extract words from content preview
                words = self._extract_keywords(record.content_preview)
                word_counts.update(words)

                # Extract from filename
                filename_words = self._extract_keywords(
                    record.filename.replace("_", " ").replace("-", " ")
                )
                word_counts.update(filename_words)

            # Create suggestions for frequent keywords
            for keyword, count in word_counts.most_common(20):
                if count >= min_occurrences:
                    examples = [
                        r.filename for r in records
                        if keyword.lower() in r.content_preview.lower()
                        or keyword.lower() in r.filename.lower()
                    ][:5]

                    suggestions.append(PatternSuggestion(
                        pattern_type="keyword",
                        pattern=keyword,
                        category=category,
                        confidence=min(0.8, 0.4 + count * 0.05),
                        occurrences=count,
                        examples=examples,
                    ))

        return suggestions

    def extract_filename_patterns(
        self,
        min_occurrences: int = MIN_PATTERN_OCCURRENCES,
    ) -> list[PatternSuggestion]:
        """Extract filename patterns from corrections.

        Finds common filename patterns (prefixes, suffixes, formats)
        that correlate with categories.

        Args:
            min_occurrences: Minimum corrections to suggest a pattern.

        Returns:
            List of filename pattern suggestions.
        """
        corrections = self._tracker.get_corrections()
        if not corrections:
            return []

        by_category = self._group_by_category(corrections)

        suggestions: list[PatternSuggestion] = []

        for category, records in by_category.items():
            if len(records) < min_occurrences:
                continue

            # Find common prefixes
            filenames = [r.filename for r in records]
            common_prefix = self._find_common_prefix(filenames)
            if common_prefix and len(common_prefix) >= MIN_NAME_LENGTH:
                suggestions.append(PatternSuggestion(
                    pattern_type="filename_prefix",
                    pattern=f"{common_prefix}*",
                    category=category,
                    confidence=0.7,
                    occurrences=len(records),
                    examples=filenames[:5],
                ))

            # Find common patterns (date formats, etc.)
            date_pattern = self._find_date_pattern(filenames)
            if date_pattern:
                suggestions.append(PatternSuggestion(
                    pattern_type="filename_pattern",
                    pattern=date_pattern,
                    category=category,
                    confidence=0.6,
                    occurrences=len(records),
                    examples=filenames[:5],
                ))

        return suggestions

    def get_all_suggestions(
        self,
        min_occurrences: int = MIN_PATTERN_OCCURRENCES,
    ) -> dict[str, list[PatternSuggestion]]:
        """Get all pattern suggestions grouped by type.

        Args:
            min_occurrences: Minimum corrections to suggest a pattern.

        Returns:
            Dictionary with 'issuers', 'keywords', and 'filenames' keys.
        """
        return {
            "issuers": self.extract_issuer_patterns(min_occurrences),
            "keywords": self.extract_keyword_patterns(min_occurrences),
            "filenames": self.extract_filename_patterns(min_occurrences),
        }

    def _is_valid_issuer(self, name: str) -> bool:
        """Check if a string could be a valid issuer name."""
        if not name or len(name) < MIN_NAME_LENGTH:
            return False
        # Filter out obvious non-issuers
        invalid_patterns = [
            r"^[0-9]+$",  # Pure numbers
            r"^[a-f0-9-]{36}$",  # UUIDs
            r"microsoft|adobe|pdf|word",  # Software names
        ]
        name_lower = name.lower()
        return not any(re.search(p, name_lower) for p in invalid_patterns)

    def _extract_issuer_from_filename(self, filename: str) -> str | None:
        """Try to extract an issuer name from a filename."""
        # Common patterns: "IssuerName-document.pdf", "IssuerName_2024.pdf"
        patterns = [
            r"^([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",  # CamelCase words
            r"^([A-Za-z]+(?:-[A-Za-z]+)*)[_-]",  # Name before underscore/dash
        ]
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                issuer = match.group(1)
                if self._is_valid_issuer(issuer):
                    return issuer
        return None

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text."""
        if not text:
            return []

        # Tokenize and filter
        words = re.findall(r"\b[a-zA-ZÀ-ÿ]{4,}\b", text.lower())
        return [w for w in words if w not in STOPWORDS]

    def _find_common_prefix(self, strings: list[str]) -> str:
        """Find the longest common prefix among strings."""
        if not strings:
            return ""

        prefix = strings[0]
        for s in strings[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ""
        return prefix

    def _find_date_pattern(self, filenames: list[str]) -> str | None:
        """Find if filenames follow a common date pattern."""
        date_patterns = [
            (r"^\d{4}-\d{2}-\d{2}", "YYYY-MM-DD_*"),
            (r"^\d{8}", "YYYYMMDD*"),
            (r"^\d{4}_", "YYYY_*"),
        ]

        for regex, pattern in date_patterns:
            matches = sum(1 for f in filenames if re.match(regex, f))
            if matches >= len(filenames) * 0.5:  # 50% match threshold
                return pattern

        return None

    def similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
