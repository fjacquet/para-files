"""Signal 3: Domain knowledge base classifier (90% confidence).

Matches known issuers (companies, organizations) in content to categories.
All configuration comes from YAML - no hardcoded values.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from para_files.classifiers.base import BaseClassifier
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
    KnownIssuers,
)


class DomainKBClassifier(BaseClassifier):
    """Signal 3: Known domain/issuer knowledge base (90% confidence).

    Searches content for known issuer names and maps them to
    appropriate archive categories based on issuer type.

    All categories and path patterns are loaded from YAML - no hardcoded values.
    """

    def __init__(self, known_issuers: KnownIssuers) -> None:
        """Initialize with known issuers database.

        Args:
            known_issuers: KnownIssuers instance from reference tree.
        """
        self._known_issuers = known_issuers
        # Build reverse mapping: issuer_name (lowercase) → (category, original_name)
        self._issuer_map: dict[str, tuple[str, str]] = {}
        self._build_issuer_map()

    def _build_issuer_map(self) -> None:
        """Build reverse mapping from issuer names to categories.

        Dynamically iterates all categories - no hardcoded category names.
        First occurrence wins - if an issuer is in multiple categories,
        the first one (in YAML order) takes precedence.
        """
        for category_name in self._known_issuers.list_categories():
            for issuer in self._known_issuers.get_issuers(category_name):
                issuer_lower = issuer.lower()
                # First occurrence wins - don't overwrite if already exists
                if issuer_lower not in self._issuer_map:
                    self._issuer_map[issuer_lower] = (category_name, issuer)

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "domain_kb"

    @property
    def source(self) -> ClassificationSource:
        """Return classification source."""
        return ClassificationSource.DOMAIN_KB

    @property
    def default_confidence(self) -> float:
        """Return default confidence (90%)."""
        return 0.90

    def classify(
        self,
        content: str,
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        """Search for known issuers, prioritizing filename and header over body.

        Priority order:
        1. Issuer in filename (highest priority - most reliable)
        2. Issuer in header section (first ~1000 chars - letterhead area)
        3. Issuer in full content (lowest priority - may have false positives)

        Args:
            content: Text content to search.
            metadata: Optional file metadata.

        Returns:
            ClassificationResult if an issuer is found, None otherwise.
        """
        # Priority 1: Check filename first (most reliable signal)
        if metadata:
            filename_match = self._find_issuer_in_text(metadata.filename.lower())
            if filename_match:
                return self._create_result(*filename_match, metadata)

        # Priority 2: Check header section (letterhead area - first ~1000 chars)
        # This is where the document issuer's name/logo typically appears
        header_section = content[:1000].lower()
        header_match = self._find_issuer_in_text(header_section)
        if header_match:
            return self._create_result(*header_match, metadata)

        # Priority 3: Check full content (may have false positives)
        # Only if nothing found in header - catches edge cases but less reliable
        content_match = self._find_issuer_in_text(content.lower())
        if content_match:
            return self._create_result(*content_match, metadata)

        return None

    def _find_issuer_in_text(self, text: str) -> tuple[str, str] | None:
        """Find the issuer that appears earliest in the text.

        This prioritizes issuers by their position in the document,
        so letterhead/header issuers are found before those mentioned
        in the body (e.g., as transaction counterparties).

        Args:
            text: Lowercase text to search.

        Returns:
            Tuple of (category, original_name) if found, None otherwise.
        """
        earliest_match: tuple[int, str, str] | None = None  # (position, category, name)

        for issuer_lower, (category, original_name) in self._issuer_map.items():
            # Use word boundary matching to avoid partial matches
            pattern = rf"\b{re.escape(issuer_lower)}\b"
            match = re.search(pattern, text)
            if match:
                position = match.start()
                if earliest_match is None or position < earliest_match[0]:
                    earliest_match = (position, category, original_name)

        if earliest_match:
            return (earliest_match[1], earliest_match[2])
        return None

    def _create_result(
        self,
        issuer_category: str,
        issuer_name: str,
        metadata: FileMetadata | None,
    ) -> ClassificationResult:
        """Create classification result for matched issuer.

        Args:
            issuer_category: Category of the issuer.
            issuer_name: Original issuer name.
            metadata: File metadata for date extraction.

        Returns:
            ClassificationResult with resolved category path.
        """
        # Get current year for path
        year = str(datetime.now(tz=UTC).year)
        if metadata and metadata.modified_at:
            year = str(metadata.modified_at.year)

        # Get path pattern from KnownIssuers (loaded from YAML)
        path_pattern = self._known_issuers.get_pattern(issuer_category)

        # Resolve pattern
        category = path_pattern.replace("{year}", year).replace("{issuer}", issuer_name)

        return ClassificationResult(
            category=category,
            confidence=Confidence(
                value=self.default_confidence,
                source=self.source,
            ),
            route_name=f"issuer_{issuer_category}",
            extracted_params={
                "issuer": issuer_name,
                "issuer_category": issuer_category,
                "year": year,
            },
        )
