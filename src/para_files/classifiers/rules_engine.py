"""Signal 2: Rules engine classifier (95% confidence).

Applies glob patterns on filename, extension, and path for classification.
Handles special routing rules for photos, videos, courses, etc.
"""

from __future__ import annotations

import fnmatch
from datetime import UTC, datetime

from para_files.classifiers.base import BaseClassifier
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
    RoutingRule,
)


class RulesEngineClassifier(BaseClassifier):
    """Signal 2: Glob pattern matching (95% confidence).

    Matches files based on:
    - File extensions (for photos, videos)
    - Filename patterns (for screenshots, courses)
    - Path patterns (for specific folder structures)
    """

    def __init__(self, routing_rules: dict[str, RoutingRule]) -> None:
        """Initialize with routing rules from reference tree.

        Args:
            routing_rules: Dictionary of rule_name → RoutingRule.
        """
        self._rules = routing_rules

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "rules_engine"

    @property
    def source(self) -> ClassificationSource:
        """Return classification source."""
        return ClassificationSource.RULES_ENGINE

    @property
    def default_confidence(self) -> float:
        """Return default confidence (95%)."""
        return 0.95

    def classify(
        self,
        _content: str,
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        """Match content against routing rules.

        Args:
            _content: Text content (unused - rules use metadata).
            metadata: File metadata with extension and path info.

        Returns:
            ClassificationResult if a rule matches, None otherwise.
        """
        if not metadata:
            return None

        filename = metadata.filename
        extension = metadata.extension.lower()

        for rule_name, rule in self._rules.items():
            # Check extension match
            if rule.extensions:
                matching_extensions = [e.lower() for e in rule.extensions]
                if extension in matching_extensions:
                    return self._create_result(rule_name, rule, metadata)

            # Check pattern match
            if rule.patterns:
                for pattern in rule.patterns:
                    if fnmatch.fnmatch(filename, pattern):
                        return self._create_result(rule_name, rule, metadata)

            # Check platform patterns (for courses)
            if rule.platforms:
                for platform, patterns in rule.platforms.items():
                    for pattern in patterns:
                        if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(
                            str(metadata.path), pattern
                        ):
                            return self._create_result(
                                rule_name,
                                rule,
                                metadata,
                                platform=platform,
                            )

        return None

    def _create_result(
        self,
        rule_name: str,
        rule: RoutingRule,
        metadata: FileMetadata,
        platform: str | None = None,
    ) -> ClassificationResult:
        """Create classification result from matched rule.

        Args:
            rule_name: Name of the matched rule.
            rule: The RoutingRule that matched.
            metadata: File metadata for parameter extraction.
            platform: Platform name for course rules.

        Returns:
            ClassificationResult with resolved category path.
        """
        # Extract date for path resolution
        date = self._get_date(rule, metadata)

        # Build parameters
        params: dict[str, str] = {}
        if date:
            params["YYYY"] = str(date.year)
            params["MM"] = f"{date.month:02d}"
            params["DD"] = f"{date.day:02d}"
            params["year"] = str(date.year)
        if platform:
            params["platform"] = platform

        # Resolve destination pattern
        category = rule.destination
        for key, value in params.items():
            category = category.replace(f"{{{key}}}", value)

        return ClassificationResult(
            category=category,
            confidence=Confidence(
                value=self.default_confidence,
                source=self.source,
            ),
            route_name=rule_name,
            extracted_params=params,
        )

    def _get_date(
        self,
        rule: RoutingRule,
        metadata: FileMetadata,
    ) -> datetime | None:
        """Extract date from file based on rule configuration.

        Uses EXIF date when available, falling back to file modified date.

        Args:
            rule: Routing rule with date_source configuration.
            metadata: File metadata (may contain EXIF date from exiftool).

        Returns:
            datetime if available, None otherwise.
        """
        # If rule specifically requests EXIF date
        if rule.date_source == "exif" and metadata.exif_date:
            return metadata.exif_date

        # Use best_date property which prioritizes: EXIF > modified > created
        best = metadata.best_date
        if best:
            return best

        return datetime.now(tz=UTC)
