"""Signal 2: Rules engine classifier (95% confidence).

Applies glob patterns on filename, extension, and path for classification.
Handles special routing rules for photos, videos, courses, etc.
"""

from __future__ import annotations

import fnmatch
import logging
import re
from datetime import UTC, datetime

from para_files.classifiers.base import BaseClassifier
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
    RoutingRule,
)
from para_files.utils.geolocation import get_location_folder


logger = logging.getLogger(__name__)


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
            # Check if extension matches (if extensions are specified)
            extension_match = True
            if rule.extensions:
                matching_extensions = [e.lower() for e in rule.extensions]
                extension_match = extension in matching_extensions

            # Check if pattern matches (if patterns are specified)
            pattern_match = False
            if rule.patterns:
                for pattern in rule.patterns:
                    if fnmatch.fnmatch(filename, pattern):
                        pattern_match = True
                        break
            else:
                # No patterns specified - extension-only rules (photos, videos, etc.)
                pattern_match = True

            # Rule matches if BOTH extension and pattern conditions are met
            # - If rule has extensions: extension must match
            # - If rule has patterns: filename must match at least one pattern
            # - If rule only has extensions (no patterns): extension match is sufficient
            if extension_match and pattern_match:
                if rule.extensions or rule.patterns:
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

        # Try to get location from GPS coordinates
        location = self._get_location(metadata)
        if location:
            params["location"] = location

        # Resolve destination pattern
        category = rule.destination
        for key, value in params.items():
            category = category.replace(f"{{{key}}}", value)

        # Clean up unreplaced {location} placeholder if no GPS data
        category = self._clean_unreplaced_location(category)

        return ClassificationResult(
            category=category,
            confidence=Confidence(
                value=self.default_confidence,
                source=self.source,
            ),
            route_name=rule_name,
            extracted_params=params,
        )

    def _get_location(self, metadata: FileMetadata) -> str | None:
        """Get location from GPS coordinates if available.

        Args:
            metadata: File metadata with potential GPS data.

        Returns:
            Location folder name, or None if no GPS or lookup fails.
        """
        if metadata.exif_gps_lat is None or metadata.exif_gps_lon is None:
            return None

        location = get_location_folder(metadata.exif_gps_lat, metadata.exif_gps_lon)
        if location:
            logger.debug(
                "GPS location resolved: %.4f, %.4f → %s",
                metadata.exif_gps_lat,
                metadata.exif_gps_lon,
                location,
            )
        return location

    def _clean_unreplaced_location(self, category: str) -> str:
        """Remove unreplaced {location} placeholder and clean up path.

        Handles patterns like:
        - "path/{location}/more" → "path/more"
        - "path/{location}" → "path"

        Args:
            category: Category path possibly containing {location}.

        Returns:
            Cleaned category path without empty segments.
        """
        # Remove {location} placeholder if still present
        category = category.replace("{location}", "")
        # Clean up double slashes
        category = re.sub(r"/+", "/", category)
        # Remove trailing slash
        return category.rstrip("/")

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
