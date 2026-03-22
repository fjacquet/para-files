"""Signal 2: Rules engine classifier (95% confidence).

Applies glob patterns on filename, extension, and path for classification.
Handles special routing rules for photos, videos, courses, etc.
"""

from __future__ import annotations

import fnmatch
import re
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from para_files.classifiers.base import BaseClassifier
from para_files.config import DEFAULT_CONTENT_PREVIEW_CHARS
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
    RoutingRule,
    RuleIssuer,
)
from para_files.utils.geolocation import LocationInfo, reverse_geocode
from para_files.utils.placeholder_resolver import clean_unreplaced_placeholders
from para_files.utils.technology_extractor import TechnologyExtractor


# Date validation constants
MIN_YEAR = 1990
MAX_YEAR = 2040  # Realistic limit to avoid false positives (e.g., "2048" from crypto key)
MIN_MODERN_YEAR = 2000  # For content extraction (avoid historical dates)
MAX_MONTH = 12
MAX_DAY = 31


class RulesEngineClassifier(BaseClassifier):
    """Signal 2: Glob pattern matching (95% confidence).

    Matches files based on:
    - File extensions (for photos, videos)
    - Filename patterns (for screenshots, courses)
    - Path patterns (for specific folder structures)
    """

    def __init__(
        self, routing_rules: dict[str, RoutingRule], para_root: Path | None = None
    ) -> None:
        """Initialize with routing rules from reference tree.

        Args:
            routing_rules: Dictionary of rule_name → RoutingRule.
            para_root: PARA root directory for source constraint checks.
        """
        self._rules = routing_rules
        self._para_root = para_root

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
        content: str,
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        """Match content against routing rules.

        Args:
            content: Text content for date extraction (if date_source is content).
            metadata: File metadata with extension and path info.

        Returns:
            ClassificationResult if a rule matches, None otherwise.
        """
        if not metadata:
            return None

        for rule_name, rule in self._rules.items():
            # Try extension/pattern matching first
            if self._matches_extension_and_pattern(rule, metadata):
                return self._create_result(rule_name, rule, metadata, content=content)

            # Check platform patterns (for courses)
            platform = self._get_matching_platform(rule, metadata)
            if platform:
                return self._create_result(
                    rule_name, rule, metadata, platform=platform, content=content
                )

        return None

    def _matches_extension_and_pattern(self, rule: RoutingRule, metadata: FileMetadata) -> bool:
        """Check if file matches rule's extension and pattern requirements.

        Args:
            rule: Routing rule to check against.
            metadata: File metadata with extension and filename.

        Returns:
            True if rule matches, False otherwise.
        """
        # Check source constraint if defined (e.g., source: "0_Inbox")
        # Files not in the source directory should not match this rule
        if rule.source and self._para_root:
            source_path = self._para_root / rule.source
            try:
                # Check if file is within the source directory
                metadata.path.relative_to(source_path)
            except ValueError:
                # File is not under the source directory
                return False

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
        content: str | None = None,
    ) -> ClassificationResult | None:
        """Create classification result from matched rule.

        Args:
            rule_name: Name of the matched rule.
            rule: The RoutingRule that matched.
            metadata: File metadata for parameter extraction.
            platform: Platform name for course rules.
            content: Optional text content for date extraction.

        Returns:
            ClassificationResult with resolved category path.
        """
        # Extract date for path resolution
        date = self._get_date(rule, metadata, content)

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

        # Try to extract technology from filename, then content if {technology} in destination
        if "{technology}" in rule.destination:
            tech_extractor = TechnologyExtractor(technologies=rule.known_technologies or None)
            tech = tech_extractor.extract_from_filename(metadata.filename)
            if tech:
                params["technology"] = tech
                logger.debug("Technology from filename: {}", tech)
            elif content:
                # Fallback: try to extract from content (first 1000 chars)
                tech, score = tech_extractor.extract_from_content(content[:1000])
                if tech:
                    params["technology"] = tech
                    logger.debug("Technology from content: {} (score={:.2f})", tech, score)
                else:
                    params["technology"] = "misc"
                    logger.debug("No technology detected, using 'misc'")
            else:
                # Default to misc if no technology detected
                params["technology"] = "misc"
                logger.debug("No technology detected, using 'misc'")

        # Try to extract issuer from content if {issuer} in destination
        if "{issuer}" in rule.destination and rule.issuers:
            issuer = self._extract_issuer(content or "", rule.issuers)
            if issuer:
                # Sanitize issuer name for folder (replace spaces with underscores)
                params["issuer"] = issuer.name.replace(" ", "_")
                logger.debug("Issuer from content: {}", issuer.name)
            else:
                # Default to 'unknown' if no issuer detected
                params["issuer"] = "unknown"
                logger.debug("No issuer detected, using 'unknown'")

        # Check for date mismatch and set suggested_name if needed
        self._apply_date_correction(rule, metadata, content, params)

        # Resolve destination pattern
        category = rule.destination
        for key, value in params.items():
            category = category.replace(f"{{{key}}}", value)

        # Clean up unreplaced placeholders (None means required placeholder missing)
        cleaned_category = clean_unreplaced_placeholders(category)
        if cleaned_category is None:
            return None

        return ClassificationResult(
            category=cleaned_category,
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

    def _get_date(
        self,
        rule: RoutingRule,
        metadata: FileMetadata,
        content: str | None = None,
    ) -> datetime | None:
        """Extract date from file based on rule configuration.

        Supports date_source values:
        - "exif": Use EXIF date from exiftool
        - "filename": Extract year from filename (YYYY pattern), no fallback
        - "content": Extract year from file content, fallback to filename
        - "file_modified": Use file modification date
        - None/default: Use best_date (EXIF > modified > created)

        Args:
            rule: Routing rule with date_source configuration.
            metadata: File metadata (may contain EXIF date from exiftool).
            content: Optional file content for content-based extraction.

        Returns:
            datetime if available, None if date_source is filename/content and not found.
        """
        result: datetime | None = None

        # If rule specifically requests EXIF date
        if rule.date_source == "exif" and metadata.exif_date:
            result = metadata.exif_date
        # If rule requests filename-based date extraction (no fallback)
        elif rule.date_source == "filename":
            result = self._extract_date_from_filename(metadata.filename)
        # If rule requests content-based date extraction
        elif rule.date_source == "content":
            # Try content first, then filename
            if content:
                result = self._extract_date_from_content(content)
            if not result:
                result = self._extract_date_from_filename(metadata.filename)
            # No fallback to file_modified - keep None
        else:
            # Use best_date property which prioritizes: EXIF > modified > created
            result = metadata.best_date or datetime.now(tz=UTC)

        return result

    def _is_valid_date(self, year: int, month: int, day: int) -> bool:
        """Check if date components are valid.

        Args:
            year: Year value.
            month: Month value.
            day: Day value.

        Returns:
            True if valid date within expected range.
        """
        return MIN_YEAR <= year <= MAX_YEAR and 1 <= month <= MAX_MONTH and 1 <= day <= MAX_DAY

    def _extract_date_from_filename(self, filename: str) -> datetime | None:
        """Extract date from filename patterns.

        Supports patterns:
        - YYYY-MM-DD or YYYYMMDD at start/in filename
        - YYYY at start of filename (e.g., "2013-certificat.pdf")
        - Year in filename (e.g., "certificat-2013.pdf")

        Args:
            filename: Filename to extract date from.

        Returns:
            datetime if a date pattern found, None otherwise.
        """
        # Try full date patterns first (YMD format)
        ymd_patterns = [
            r"(\d{4})-(\d{2})-(\d{2})",  # YYYY-MM-DD
            r"(\d{4})(\d{2})(\d{2})",  # YYYYMMDD
        ]
        for pattern in ymd_patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    if self._is_valid_date(year, month, day):
                        return datetime(year, month, day, tzinfo=UTC)
                except ValueError:
                    continue

        # Try YYYYMM format (6 digits, year + month, common in expense reports)
        ym_patterns = [
            r"(\d{4})-(\d{2})(?=[^0-9]|$)",  # YYYY-MM (not followed by digit)
            r"^(\d{4})(\d{2})(?=[^0-9]|$)",  # YYYYMM at start (not followed by digit)
        ]
        for pattern in ym_patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    if MIN_YEAR <= year <= MAX_YEAR and 1 <= month <= MAX_MONTH:
                        return datetime(year, month, 1, tzinfo=UTC)
                except ValueError:
                    continue

        # Try European date formats (DMY format)
        dmy_patterns = [
            r"(\d{2})_(\d{2})_(\d{4})",  # DD_MM_YYYY
            r"(\d{2})-(\d{2})-(\d{4})",  # DD-MM-YYYY
            r"(\d{2})\.(\d{2})\.(\d{4})",  # DD.MM.YYYY
        ]
        for pattern in dmy_patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    day = int(match.group(1))
                    month = int(match.group(2))
                    year = int(match.group(3))
                    if self._is_valid_date(year, month, day):
                        return datetime(year, month, day, tzinfo=UTC)
                except ValueError:
                    continue

        # Try year-only pattern (at start or after separator)
        # Accept any non-digit as separator (space, dash, underscore, parenthesis, etc.)
        year_match = re.search(r"(?:^|[_\-\s\(\)])(\d{4})(?:[_\-\s\(\)\.]|$)", filename)
        if year_match:
            year = int(year_match.group(1))
            if MIN_YEAR <= year <= MAX_YEAR:
                return datetime(year, 1, 1, tzinfo=UTC)

        return None

    def _extract_date_from_content(self, content: str) -> datetime | None:
        """Extract date/year from document content.

        Prioritizes fiscal year patterns (e.g., "Année fiscale 2023") over
        general year mentions to avoid extracting birth years.

        Args:
            content: Text content to search.

        Returns:
            datetime if a year found, None otherwise.
        """
        # Priority 1: Fiscal year patterns (most reliable for documents)
        fiscal_patterns = [
            # French fiscal patterns (specific first)
            r"[Aa]nnée\s+fiscale\s+(\d{4})",
            r"[Ee]xercice\s+(\d{4})",
            r"[Rr]evenus?\s+de\s+l[''']année\s+(\d{4})",
            r"[Rr]evenus?\s+de\s+(\d{4})",
            r"[Rr]evenus?\s+(\d{4})",
            r"réalisée?s?\s+en\s+(\d{4})",  # "réalisées en 2023"
            r"perçue?s?\s+en\s+(\d{4})",  # "perçus en 2023"
            r"versée?s?\s+en\s+(\d{4})",  # "versés en 2023"
            r"payée?s?\s+en\s+(\d{4})",  # "payés en 2023"
            r"[Aa]u\s+titre\s+de\s+(\d{4})",
            r"[Pp]our\s+l[''']année\s+(\d{4})",
            r"[Aa]nnée\s+(\d{4})",
            r"[Pp]ériode\s+(\d{4})",
            r"[Dd]éclaration\s+(\d{4})",
            r"IFU\s+(\d{4})",
            r"[Ii]mprimé\s+[Ff]iscal\s+[Uu]nique\s+(\d{4})",
            r"[Aa]ttestation\s+(\d{4})",
            r"[Cc]ertificat\s+(\d{4})",
            # English fiscal patterns
            r"[Ff]iscal\s+[Yy]ear\s+(\d{4})",
            r"[Yy]ear\s+(\d{4})",
            r"(\d{4})\s+[Tt]ax\s+[Rr]eturn",
            r"[Tt]ax\s+[Yy]ear\s+(\d{4})",
        ]
        for pattern in fiscal_patterns:
            match = re.search(pattern, content)
            if match:
                year = int(match.group(1))
                if MIN_YEAR <= year <= MAX_YEAR:
                    logger.debug("Fiscal year from content: {}", year)
                    return datetime(year, 1, 1, tzinfo=UTC)

        # Priority 2: Full date patterns (YYYY-MM-DD or DD/MM/YYYY)
        date_patterns = [
            (r"(\d{4})-(\d{2})-(\d{2})", "ymd"),  # YYYY-MM-DD
            (r"(\d{2})/(\d{2})/(\d{4})", "dmy"),  # DD/MM/YYYY
            (r"(\d{2})\.(\d{2})\.(\d{4})", "dmy"),  # DD.MM.YYYY
        ]
        for pattern, fmt in date_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    if fmt == "ymd":
                        year = int(match.group(1))
                        month = int(match.group(2))
                        day = int(match.group(3))
                    else:  # dmy
                        day = int(match.group(1))
                        month = int(match.group(2))
                        year = int(match.group(3))
                    if self._is_valid_date(year, month, day):
                        logger.debug("Full date from content: {:d}-{:02d}-{:02d}", year, month, day)
                        return datetime(year, month, day, tzinfo=UTC)
                except ValueError:
                    continue

        # Priority 3: Standalone year in first DEFAULT_CONTENT_PREVIEW_CHARS (document header)
        header = content[:DEFAULT_CONTENT_PREVIEW_CHARS]
        year_match = re.search(r"\b(20[0-9]{2})\b", header)
        if year_match:
            year = int(year_match.group(1))
            if MIN_MODERN_YEAR <= year <= MAX_YEAR:
                logger.debug("Year from content header: {}", year)
                return datetime(year, 1, 1, tzinfo=UTC)

        return None

    def _detect_date_mismatch(
        self,
        filename: str,
        content: str | None,
    ) -> tuple[datetime | None, datetime | None, bool]:
        """Detect if filename date differs from content date.

        Only compares years because content extraction often yields year-only
        dates (month defaults to 01). A year mismatch indicates the file needs
        correction.

        Args:
            filename: Filename to extract date from.
            content: File content for date extraction.

        Returns:
            Tuple of (filename_date, content_date, has_mismatch).
        """
        filename_date = self._extract_date_from_filename(filename)
        content_date = self._extract_date_from_content(content) if content else None

        # No mismatch if either date is missing
        if not filename_date or not content_date:
            return filename_date, content_date, False

        # Compare years only (content often has year-only extraction)
        has_mismatch = filename_date.year != content_date.year

        return filename_date, content_date, has_mismatch

    def _build_corrected_filename(
        self,
        original_filename: str,
        content_date: datetime,
        filename_date: datetime | None = None,
    ) -> str:
        """Build corrected filename with date from content in ISO format.

        Strategy:
        1. Use content year with filename month (if available) to preserve month info
        2. Remove existing date patterns from filename
        3. Prepend YYYY-MM- (ISO format) to the rest

        Args:
            original_filename: Original filename.
            content_date: Authoritative date from content.
            filename_date: Original date from filename (for preserving month).

        Returns:
            Corrected filename with content date in ISO format.
        """
        stem = Path(original_filename).stem
        suffix = Path(original_filename).suffix

        # Use content year with filename month to preserve month info
        # If content has month != 1, it has specific month info, use it
        # Otherwise, use filename's month if available
        if content_date.month != 1:
            month = content_date.month
        elif filename_date and filename_date.month != 1:
            month = filename_date.month
        else:
            month = 1

        iso_date = f"{content_date.year}-{month:02d}"

        # Patterns to remove from filename (date prefixes)
        date_patterns = [
            r"^\d{4}-\d{2}-\d{2}[-_]?",  # YYYY-MM-DD- or YYYY-MM-DD_
            r"^\d{4}-\d{2}[-_]?",  # YYYY-MM- or YYYY-MM_
            r"^\d{8}[-_]?",  # YYYYMMDD- or YYYYMMDD_
            r"^\d{6}[-_]?",  # YYYYMM- or YYYYMM_
        ]

        # Remove existing date prefix
        new_stem = stem
        for pattern in date_patterns:
            new_stem = re.sub(pattern, "", stem)
            if new_stem != stem:
                break

        # Build new filename with ISO date prefix
        if new_stem:
            return f"{iso_date}-{new_stem}{suffix}"
        # Edge case: filename was just a date
        return f"{iso_date}{suffix}"

    def _apply_date_correction(
        self,
        rule: RoutingRule,
        metadata: FileMetadata,
        content: str | None,
        params: dict[str, str],
    ) -> None:
        """Check for date mismatch and add suggested_name to params if needed.

        Args:
            rule: Routing rule with auto_correct_date setting.
            metadata: File metadata with filename.
            content: File content for date extraction.
            params: Parameters dict to update with suggested_name.
        """
        if not (rule.auto_correct_date and rule.date_source == "content" and content):
            return

        filename_date, content_date, has_mismatch = self._detect_date_mismatch(
            metadata.filename, content
        )

        if has_mismatch and content_date:
            corrected_name = self._build_corrected_filename(
                metadata.filename, content_date, filename_date
            )
            # Store stem only (without extension) for FileMover
            params["suggested_name"] = Path(corrected_name).stem
            logger.info(
                "Date mismatch: filename={}, content={}. Suggesting: {}",
                filename_date.strftime("%Y-%m") if filename_date else "none",
                content_date.strftime("%Y-%m"),
                corrected_name,
            )

    def _extract_issuer(
        self,
        content: str,
        issuers: list[RuleIssuer],
    ) -> RuleIssuer | None:
        """Extract issuer from content by pattern matching.

        Searches content for each issuer's patterns. Uses word boundary at start
        to avoid false positives, but allows prefix matching at end (e.g., BIC codes
        like 'BCVLCH2L' matching 'BCVLCH2LXXX').

        Args:
            content: Text content to search.
            issuers: List of RuleIssuer with name and patterns.

        Returns:
            RuleIssuer if found, None otherwise.
        """
        if not content:
            return None

        content_lower = content.lower()
        for issuer in issuers:
            for pattern in issuer.patterns:
                pattern_lower = pattern.lower()
                # Use word boundary at start, allow prefix matching at end
                # This matches "BCVLCH2L" in "BCVLCH2LXXX" while avoiding
                # false positives like "UBS" matching inside "CLUBS"
                escaped_pattern = re.escape(pattern_lower)
                regex = rf"(?:^|[^a-z0-9]){escaped_pattern}"
                if re.search(regex, content_lower):
                    logger.debug(
                        "Issuer '%s' matched pattern '%s'",
                        issuer.name,
                        pattern,
                    )
                    return issuer

        return None
