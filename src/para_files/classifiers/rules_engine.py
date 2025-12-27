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
from para_files.utils.geolocation import LocationInfo, reverse_geocode


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

        for rule_name, rule in self._rules.items():
            # Try extension/pattern matching first
            if self._matches_extension_and_pattern(rule, metadata):
                return self._create_result(rule_name, rule, metadata)

            # Check platform patterns (for courses)
            platform = self._get_matching_platform(rule, metadata)
            if platform:
                return self._create_result(rule_name, rule, metadata, platform=platform)

        return None

    def _matches_extension_and_pattern(self, rule: RoutingRule, metadata: FileMetadata) -> bool:
        """Check if file matches rule's extension and pattern requirements.

        Args:
            rule: Routing rule to check against.
            metadata: File metadata with extension and filename.

        Returns:
            True if rule matches, False otherwise.
        """
        # Must have at least extensions or patterns defined
        if not rule.extensions and not rule.patterns:
            return False

        extension = metadata.extension.lower()
        filename = metadata.filename

        # Check extension match (True if no extensions specified)
        extension_match = True
        if rule.extensions:
            matching_extensions = [e.lower() for e in rule.extensions]
            extension_match = extension in matching_extensions

        # Check pattern match (True if no patterns specified)
        pattern_match = not rule.patterns or any(
            fnmatch.fnmatch(filename, pattern) for pattern in rule.patterns
        )

        return extension_match and pattern_match

    def _get_matching_platform(self, rule: RoutingRule, metadata: FileMetadata) -> str | None:
        """Find matching platform from rule's platform patterns.

        Args:
            rule: Routing rule with optional platform patterns.
            metadata: File metadata with filename and path.

        Returns:
            Platform name if matched, None otherwise.
        """
        if not rule.platforms:
            return None

        filename = metadata.filename
        path_str = str(metadata.path)

        for platform, patterns in rule.platforms.items():
            for pattern in patterns:
                if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(path_str, pattern):
                    return platform
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
        location_info = self._get_location_info(metadata)
        if location_info:
            # Set location as city or region (most specific non-country)
            if location_info.city:
                params["location"] = location_info.city.replace(" ", "_")
            elif location_info.region:
                params["location"] = location_info.region.replace(" ", "_")
            # Set country separately
            if location_info.country:
                params["country"] = location_info.country.replace(" ", "_")

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

    def _get_location_info(self, metadata: FileMetadata) -> LocationInfo | None:
        """Get location info from GPS coordinates if available.

        Args:
            metadata: File metadata with potential GPS data.

        Returns:
            LocationInfo with city/region/country, or None if no GPS or lookup fails.
        """
        if metadata.exif_gps_lat is None or metadata.exif_gps_lon is None:
            return None

        location_info = reverse_geocode(metadata.exif_gps_lat, metadata.exif_gps_lon)
        if location_info:
            logger.debug(
                "GPS location resolved: %.4f, %.4f → %s/%s",
                metadata.exif_gps_lat,
                metadata.exif_gps_lon,
                location_info.country,
                location_info.city or location_info.region,
            )
        return location_info

    def _clean_unreplaced_location(self, category: str) -> str:
        """Remove unreplaced {location} and {country} placeholders and clean up path.

        Handles patterns like:
        - "path/{country}/{location}/more" → "path/more"
        - "path/{location}" → "path"

        Args:
            category: Category path possibly containing {location} or {country}.

        Returns:
            Cleaned category path without empty segments.
        """
        # Remove {location} and {country} placeholders if still present
        category = category.replace("{location}", "")
        category = category.replace("{country}", "")
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
