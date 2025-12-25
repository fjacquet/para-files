"""Signal 3: Domain knowledge base classifier (90% confidence).

Matches known issuers (companies, organizations) in content to categories.
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


# Mapping from issuer category to archive path pattern
ISSUER_CATEGORY_PATHS: dict[str, str] = {
    "assurances": "4_Archives/factures/{year}/_Assurances/{issuer}",
    "banques": "4_Archives/factures/{year}/_Banques/{issuer}",
    "energie": "4_Archives/factures/{year}/_Energie/{issuer}",
    "telephonie": "4_Archives/factures/{year}/_Telephonie/{issuer}",
    "cloud": "4_Archives/factures/{year}/_Cloud/{issuer}",
}


class DomainKBClassifier(BaseClassifier):
    """Signal 3: Known domain/issuer knowledge base (90% confidence).

    Searches content for known issuer names and maps them to
    appropriate archive categories based on issuer type.
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
        """Build reverse mapping from issuer names to categories."""
        for issuer in self._known_issuers.assurances:
            self._issuer_map[issuer.lower()] = ("assurances", issuer)
        for issuer in self._known_issuers.banques:
            self._issuer_map[issuer.lower()] = ("banques", issuer)
        for issuer in self._known_issuers.energie:
            self._issuer_map[issuer.lower()] = ("energie", issuer)
        for issuer in self._known_issuers.telephonie:
            self._issuer_map[issuer.lower()] = ("telephonie", issuer)
        for issuer in self._known_issuers.cloud:
            self._issuer_map[issuer.lower()] = ("cloud", issuer)

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
        """Search content for known issuers.

        Args:
            content: Text content to search.
            metadata: Optional file metadata.

        Returns:
            ClassificationResult if an issuer is found, None otherwise.
        """
        content_lower = content.lower()

        # Search for each known issuer in content
        for issuer_lower, (category, original_name) in self._issuer_map.items():
            # Use word boundary matching to avoid partial matches
            pattern = rf"\b{re.escape(issuer_lower)}\b"
            if re.search(pattern, content_lower):
                return self._create_result(category, original_name, metadata)

        return None

    def _create_result(
        self,
        issuer_category: str,
        issuer_name: str,
        metadata: FileMetadata | None,
    ) -> ClassificationResult:
        """Create classification result for matched issuer.

        Args:
            issuer_category: Category of the issuer (assurances, banques, etc.).
            issuer_name: Original issuer name.
            metadata: File metadata for date extraction.

        Returns:
            ClassificationResult with resolved category path.
        """
        # Get current year for path
        year = str(datetime.now(tz=UTC).year)
        if metadata and metadata.modified_at:
            year = str(metadata.modified_at.year)

        # Get path pattern for this issuer category
        path_pattern = ISSUER_CATEGORY_PATHS.get(
            issuer_category,
            f"4_Archives/factures/{{year}}/_Other/{issuer_name}",
        )

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
