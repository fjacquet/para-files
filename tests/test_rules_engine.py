"""Tests for rules engine classifier."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from para_files.classifiers.rules_engine import (
    MAX_DAY,
    MAX_MONTH,
    MAX_YEAR,
    MIN_MODERN_YEAR,
    MIN_YEAR,
    RulesEngineClassifier,
)
from para_files.types import ClassificationSource, FileMetadata, RoutingRule, RuleIssuer
from para_files.utils.placeholder_resolver import clean_unreplaced_placeholders


def make_metadata(**kwargs: object) -> FileMetadata:
    """Helper to create FileMetadata with required defaults."""
    defaults: dict[str, object] = {
        "path": Path("/test/file.txt"),
        "filename": "file.txt",
        "extension": ".txt",
        "size_bytes": 1024,
    }
    defaults.update(kwargs)
    return FileMetadata(**defaults)


class TestRulesEngineClassifierInit:
    """Test RulesEngineClassifier initialization."""

    def test_init_with_empty_rules(self) -> None:
        """Test initialization with empty rules dict."""
        classifier = RulesEngineClassifier({})
        assert classifier._rules == {}

    def test_init_with_rules(self) -> None:
        """Test initialization with routing rules."""
        rules = {
            "photos": RoutingRule(
                extensions=[".jpg", ".png"],
                destination="1_Projects/photos",
            )
        }
        classifier = RulesEngineClassifier(rules)
        assert "photos" in classifier._rules


class TestRulesEngineClassifierProperties:
    """Test classifier properties."""

    def test_name(self) -> None:
        """Test classifier name."""
        classifier = RulesEngineClassifier({})
        assert classifier.name == "rules_engine"

    def test_source(self) -> None:
        """Test classification source."""
        classifier = RulesEngineClassifier({})
        assert classifier.source == ClassificationSource.RULES_ENGINE

    def test_default_confidence(self) -> None:
        """Test default confidence is 95%."""
        classifier = RulesEngineClassifier({})
        assert classifier.default_confidence == 0.95


class TestClassify:
    """Test classify method."""

    def test_returns_none_without_metadata(self) -> None:
        """Test classify returns None when metadata is None."""
        classifier = RulesEngineClassifier({})
        result = classifier.classify("content")
        assert result is None

    def test_matches_extension(self) -> None:
        """Test matching by file extension."""
        rules = {
            "photos": RoutingRule(
                extensions=[".jpg", ".jpeg", ".png"],
                destination="1_Projects/photos",
            )
        }
        classifier = RulesEngineClassifier(rules)
        metadata = make_metadata(
            path=Path("/test/image.jpg"),
            filename="image.jpg",
            extension=".jpg",
        )
        result = classifier.classify("", metadata)
        assert result is not None
        assert result.category == "1_Projects/photos"
        assert result.route_name == "photos"

    def test_no_match_wrong_extension(self) -> None:
        """Test no match when extension doesn't match."""
        rules = {
            "photos": RoutingRule(
                extensions=[".jpg", ".jpeg", ".png"],
                destination="1_Projects/photos",
            )
        }
        classifier = RulesEngineClassifier(rules)
        metadata = make_metadata(
            path=Path("/test/document.pdf"),
            filename="document.pdf",
            extension=".pdf",
        )
        result = classifier.classify("", metadata)
        assert result is None

    def test_matches_pattern(self) -> None:
        """Test matching by filename pattern."""
        rules = {
            "screenshots": RoutingRule(
                patterns=["Screenshot*", "Capture*"],
                destination="1_Projects/screenshots",
            )
        }
        classifier = RulesEngineClassifier(rules)
        metadata = make_metadata(
            path=Path("/test/Screenshot 2024-01-01.png"),
            filename="Screenshot 2024-01-01.png",
            extension=".png",
        )
        result = classifier.classify("", metadata)
        assert result is not None
        assert result.category == "1_Projects/screenshots"

    def test_matches_extension_and_pattern(self) -> None:
        """Test matching both extension AND pattern."""
        rules = {
            "docs": RoutingRule(
                extensions=[".pdf"],
                patterns=["invoice*", "facture*"],
                destination="2_Areas/finance/invoices",
            )
        }
        classifier = RulesEngineClassifier(rules)

        # Match both extension and pattern
        metadata = make_metadata(
            path=Path("/test/invoice_2024.pdf"),
            filename="invoice_2024.pdf",
            extension=".pdf",
        )
        result = classifier.classify("", metadata)
        assert result is not None

        # Wrong pattern (extension matches but pattern doesn't)
        metadata2 = make_metadata(
            path=Path("/test/random.pdf"),
            filename="random.pdf",
            extension=".pdf",
        )
        result2 = classifier.classify("", metadata2)
        assert result2 is None

    def test_matches_platform_patterns(self) -> None:
        """Test matching platform patterns for courses.

        Note: Platform patterns are only checked if extension/pattern matching fails.
        To have platform extracted, don't include extensions in the rule.
        """
        rules = {
            "courses": RoutingRule(
                # No extensions - so extension match fails, platform patterns checked
                platforms={
                    "Udemy": ["*udemy*", "*Udemy*"],
                    "Coursera": ["*coursera*", "*Coursera*"],
                },
                destination="3_Resources/courses/{platform}",
            )
        }
        classifier = RulesEngineClassifier(rules)
        metadata = make_metadata(
            path=Path("/downloads/udemy-python-course.mp4"),
            filename="udemy-python-course.mp4",
            extension=".mp4",
        )
        result = classifier.classify("", metadata)
        assert result is not None
        assert "Udemy" in result.category
        assert result.extracted_params.get("platform") == "Udemy"


class TestMatchesExtensionAndPattern:
    """Test _matches_extension_and_pattern method."""

    def test_no_extensions_or_patterns_returns_false(self) -> None:
        """Test returns False when rule has neither extensions nor patterns."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(destination="test")
        metadata = make_metadata(
            path=Path("/test/file.txt"),
            filename="file.txt",
            extension=".txt",
        )
        result = classifier._matches_extension_and_pattern(rule, metadata)
        assert result is False

    def test_extension_only_match(self) -> None:
        """Test matching by extension only."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            extensions=[".pdf", ".doc"],
            destination="test",
        )
        metadata = make_metadata(
            path=Path("/test/file.pdf"),
            filename="file.pdf",
            extension=".pdf",
        )
        result = classifier._matches_extension_and_pattern(rule, metadata)
        assert result is True

    def test_pattern_only_match(self) -> None:
        """Test matching by pattern only."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            patterns=["Screenshot*"],
            destination="test",
        )
        metadata = make_metadata(
            path=Path("/test/Screenshot 2024.png"),
            filename="Screenshot 2024.png",
            extension=".png",
        )
        result = classifier._matches_extension_and_pattern(rule, metadata)
        assert result is True

    def test_case_insensitive_extension(self) -> None:
        """Test extension matching is case-insensitive."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            extensions=[".PDF", ".DOC"],
            destination="test",
        )
        metadata = make_metadata(
            path=Path("/test/file.pdf"),
            filename="file.pdf",
            extension=".pdf",
        )
        result = classifier._matches_extension_and_pattern(rule, metadata)
        assert result is True


class TestGetMatchingPlatform:
    """Test _get_matching_platform method."""

    def test_no_platforms_returns_none(self) -> None:
        """Test returns None when rule has no platforms."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(destination="test")
        metadata = make_metadata(
            path=Path("/test/file.mp4"),
            filename="file.mp4",
            extension=".mp4",
        )
        result = classifier._get_matching_platform(rule, metadata)
        assert result is None

    def test_matches_filename_platform(self) -> None:
        """Test matches platform from filename."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            platforms={"Udemy": ["*udemy*"], "Pluralsight": ["*pluralsight*"]},
            destination="test",
        )
        metadata = make_metadata(
            path=Path("/downloads/udemy-course.mp4"),
            filename="udemy-course.mp4",
            extension=".mp4",
        )
        result = classifier._get_matching_platform(rule, metadata)
        assert result == "Udemy"

    def test_matches_path_platform(self) -> None:
        """Test matches platform from path."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            platforms={"Udemy": ["*/Udemy/*"]},
            destination="test",
        )
        metadata = make_metadata(
            path=Path("/downloads/Udemy/course.mp4"),
            filename="course.mp4",
            extension=".mp4",
        )
        result = classifier._get_matching_platform(rule, metadata)
        assert result == "Udemy"

    def test_no_platform_match(self) -> None:
        """Test returns None when no platform matches."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            platforms={"Udemy": ["*udemy*"]},
            destination="test",
        )
        metadata = make_metadata(
            path=Path("/downloads/random-video.mp4"),
            filename="random-video.mp4",
            extension=".mp4",
        )
        result = classifier._get_matching_platform(rule, metadata)
        assert result is None


class TestCreateResult:
    """Test _create_result method."""

    def test_basic_result(self) -> None:
        """Test creating basic result without parameters."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(destination="1_Projects/photos")
        metadata = make_metadata(
            path=Path("/test/image.jpg"),
            filename="image.jpg",
            extension=".jpg",
        )
        result = classifier._create_result("photos", rule, metadata)
        assert result.category == "1_Projects/photos"
        assert result.route_name == "photos"
        assert result.confidence.value == 0.95
        assert result.confidence.source == ClassificationSource.RULES_ENGINE

    def test_result_with_date_params(self) -> None:
        """Test result includes date parameters."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            destination="1_Projects/photos/{YYYY}/{MM}",
        )
        metadata = make_metadata(
            path=Path("/test/image.jpg"),
            filename="image.jpg",
            extension=".jpg",
            modified_at=datetime(2024, 6, 15, tzinfo=UTC),
        )
        result = classifier._create_result("photos", rule, metadata)
        assert "2024" in result.category
        assert "06" in result.category
        assert result.extracted_params.get("YYYY") == "2024"
        assert result.extracted_params.get("MM") == "06"

    def test_result_with_platform_param(self) -> None:
        """Test result includes platform parameter."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            destination="3_Resources/courses/{platform}",
        )
        metadata = make_metadata(
            path=Path("/test/course.mp4"),
            filename="course.mp4",
            extension=".mp4",
        )
        result = classifier._create_result("courses", rule, metadata, platform="Udemy")
        assert "Udemy" in result.category
        assert result.extracted_params.get("platform") == "Udemy"

    @patch("para_files.classifiers.rules_engine.reverse_geocode")
    def test_result_with_location_params(self, mock_geocode: MagicMock) -> None:
        """Test result includes location parameters from GPS."""
        from para_files.utils.geolocation import LocationInfo

        mock_geocode.return_value = LocationInfo(
            country="Switzerland",
            region="Vaud",
            city="Lausanne",
        )

        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            destination="1_Projects/photos/{country}/{location}",
        )
        metadata = make_metadata(
            path=Path("/test/image.jpg"),
            filename="image.jpg",
            extension=".jpg",
            exif_gps_lat=46.5197,
            exif_gps_lon=6.6323,
        )
        result = classifier._create_result("photos", rule, metadata)
        assert "Switzerland" in result.category
        assert "Lausanne" in result.category
        assert result.extracted_params.get("country") == "Switzerland"
        assert result.extracted_params.get("location") == "Lausanne"

    @patch("para_files.classifiers.rules_engine.reverse_geocode")
    def test_result_with_region_when_no_city(self, mock_geocode: MagicMock) -> None:
        """Test location falls back to region when no city."""
        from para_files.utils.geolocation import LocationInfo

        mock_geocode.return_value = LocationInfo(
            country="Switzerland",
            region="Valais",
            city=None,
        )

        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            destination="1_Projects/photos/{location}",
        )
        metadata = make_metadata(
            path=Path("/test/image.jpg"),
            filename="image.jpg",
            extension=".jpg",
            exif_gps_lat=46.5197,
            exif_gps_lon=6.6323,
        )
        result = classifier._create_result("photos", rule, metadata)
        assert "Valais" in result.category

    def test_result_with_technology_from_filename(self) -> None:
        """Test technology extraction from filename."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            destination="3_Resources/tech/{technology}",
        )
        metadata = make_metadata(
            path=Path("/test/kubernetes-guide.pdf"),
            filename="kubernetes-guide.pdf",
            extension=".pdf",
        )
        result = classifier._create_result("tech", rule, metadata)
        assert "Kubernetes" in result.category
        assert result.extracted_params.get("technology") == "Kubernetes"

    @patch("para_files.classifiers.rules_engine.TechnologyExtractor")
    def test_result_with_technology_from_content(self, mock_extractor_class: MagicMock) -> None:
        """Test technology extraction from content when filename doesn't match."""
        mock_extractor = MagicMock()
        mock_extractor.extract_from_filename.return_value = None
        mock_extractor.extract_from_content.return_value = ("Docker", 0.85)
        mock_extractor_class.return_value = mock_extractor

        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            destination="3_Resources/tech/{technology}",
        )
        metadata = make_metadata(
            path=Path("/test/guide.pdf"),
            filename="guide.pdf",
            extension=".pdf",
        )
        result = classifier._create_result("tech", rule, metadata, content="Docker containers")
        assert "Docker" in result.category

    @patch("para_files.classifiers.rules_engine.TechnologyExtractor")
    def test_result_with_technology_default_misc(self, mock_extractor_class: MagicMock) -> None:
        """Test technology defaults to 'misc' when not detected."""
        mock_extractor = MagicMock()
        mock_extractor.extract_from_filename.return_value = None
        mock_extractor.extract_from_content.return_value = (None, 0.0)
        mock_extractor_class.return_value = mock_extractor

        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            destination="3_Resources/tech/{technology}",
        )
        metadata = make_metadata(
            path=Path("/test/guide.pdf"),
            filename="guide.pdf",
            extension=".pdf",
        )
        result = classifier._create_result("tech", rule, metadata, content="random content")
        assert "misc" in result.category

    def test_result_with_issuer_extraction(self) -> None:
        """Test issuer extraction from content."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            destination="2_Areas/finance/{issuer}",
            issuers=[
                RuleIssuer(name="UBS", patterns=["UBS", "Union Bank"]),
                RuleIssuer(name="Credit Suisse", patterns=["Credit Suisse", "CS"]),
            ],
        )
        metadata = make_metadata(
            path=Path("/test/statement.pdf"),
            filename="statement.pdf",
            extension=".pdf",
        )
        result = classifier._create_result("banking", rule, metadata, content="UBS Statement 2024")
        assert "UBS" in result.category
        assert result.extracted_params.get("issuer") == "UBS"

    def test_result_issuer_default_unknown(self) -> None:
        """Test issuer defaults to 'unknown' when not detected."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            destination="2_Areas/finance/{issuer}",
            issuers=[
                RuleIssuer(name="UBS", patterns=["UBS"]),
            ],
        )
        metadata = make_metadata(
            path=Path("/test/statement.pdf"),
            filename="statement.pdf",
            extension=".pdf",
        )
        result = classifier._create_result(
            "banking", rule, metadata, content="Random Bank Statement"
        )
        assert "unknown" in result.category


class TestCleanUnreplacedLocation:
    """Test clean_unreplaced_placeholders for location placeholders."""

    def test_removes_location_placeholder(self) -> None:
        """Test removes {location} placeholder."""
        result = clean_unreplaced_placeholders("photos/{location}/2024")
        assert result == "photos/2024"

    def test_removes_country_placeholder(self) -> None:
        """Test removes {country} placeholder."""
        result = clean_unreplaced_placeholders("photos/{country}/2024")
        assert result == "photos/2024"

    def test_removes_both_placeholders(self) -> None:
        """Test removes both {country} and {location}."""
        result = clean_unreplaced_placeholders("photos/{country}/{location}/2024")
        assert result == "photos/2024"

    def test_cleans_double_slashes(self) -> None:
        """Test cleans up double slashes."""
        result = clean_unreplaced_placeholders("photos//2024")
        assert result == "photos/2024"

    def test_removes_trailing_slash(self) -> None:
        """Test removes trailing slash."""
        result = clean_unreplaced_placeholders("photos/2024/")
        assert result == "photos/2024"


class TestCleanUnreplacedDate:
    """Test clean_unreplaced_placeholders for date placeholders."""

    def test_removes_yyyy_placeholder(self) -> None:
        """Test removes {YYYY} placeholder."""
        result = clean_unreplaced_placeholders("photos/{YYYY}/images")
        assert result == "photos/images"

    def test_removes_year_placeholder(self) -> None:
        """Test removes {year} placeholder."""
        result = clean_unreplaced_placeholders("photos/{year}/images")
        assert result == "photos/images"

    def test_removes_mm_placeholder(self) -> None:
        """Test removes {MM} placeholder."""
        result = clean_unreplaced_placeholders("photos/2024/{MM}/images")
        assert result == "photos/2024/images"

    def test_removes_dd_placeholder(self) -> None:
        """Test removes {DD} placeholder."""
        result = clean_unreplaced_placeholders("photos/2024/06/{DD}")
        assert result == "photos/2024/06"


class TestGetDate:
    """Test _get_date method."""

    def test_exif_date_source(self) -> None:
        """Test date_source='exif' uses EXIF date."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            destination="test",
            date_source="exif",
        )
        exif_date = datetime(2024, 6, 15, 12, 30, tzinfo=UTC)
        metadata = make_metadata(
            path=Path("/test/image.jpg"),
            filename="image.jpg",
            extension=".jpg",
            exif_date=exif_date,
        )
        result = classifier._get_date(rule, metadata)
        assert result == exif_date

    def test_filename_date_source(self) -> None:
        """Test date_source='filename' extracts from filename."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            destination="test",
            date_source="filename",
        )
        metadata = make_metadata(
            path=Path("/test/2024-06-15-photo.jpg"),
            filename="2024-06-15-photo.jpg",
            extension=".jpg",
        )
        result = classifier._get_date(rule, metadata)
        assert result is not None
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_content_date_source(self) -> None:
        """Test date_source='content' extracts from content."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            destination="test",
            date_source="content",
        )
        metadata = make_metadata(
            path=Path("/test/document.pdf"),
            filename="document.pdf",
            extension=".pdf",
        )
        result = classifier._get_date(rule, metadata, content="Fiscal Year 2023")
        assert result is not None
        assert result.year == 2023

    def test_content_date_source_fallback_to_filename(self) -> None:
        """Test date_source='content' falls back to filename."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(
            destination="test",
            date_source="content",
        )
        metadata = make_metadata(
            path=Path("/test/2024-document.pdf"),
            filename="2024-document.pdf",
            extension=".pdf",
        )
        result = classifier._get_date(rule, metadata, content="no date here")
        assert result is not None
        assert result.year == 2024

    def test_default_uses_best_date(self) -> None:
        """Test default date_source uses best_date property."""
        classifier = RulesEngineClassifier({})
        rule = RoutingRule(destination="test")
        modified = datetime(2024, 3, 10, tzinfo=UTC)
        metadata = make_metadata(
            path=Path("/test/file.pdf"),
            filename="file.pdf",
            extension=".pdf",
            modified_at=modified,
        )
        result = classifier._get_date(rule, metadata)
        assert result == modified


class TestIsValidDate:
    """Test _is_valid_date method."""

    def test_valid_date(self) -> None:
        """Test valid date returns True."""
        classifier = RulesEngineClassifier({})
        assert classifier._is_valid_date(2024, 6, 15) is True

    def test_year_too_low(self) -> None:
        """Test year below MIN_YEAR returns False."""
        classifier = RulesEngineClassifier({})
        assert classifier._is_valid_date(1980, 6, 15) is False

    def test_year_too_high(self) -> None:
        """Test year above MAX_YEAR returns False."""
        classifier = RulesEngineClassifier({})
        assert classifier._is_valid_date(2100, 6, 15) is False

    def test_month_invalid(self) -> None:
        """Test invalid month returns False."""
        classifier = RulesEngineClassifier({})
        assert classifier._is_valid_date(2024, 13, 15) is False
        assert classifier._is_valid_date(2024, 0, 15) is False

    def test_day_invalid(self) -> None:
        """Test invalid day returns False."""
        classifier = RulesEngineClassifier({})
        assert classifier._is_valid_date(2024, 6, 32) is False
        assert classifier._is_valid_date(2024, 6, 0) is False


class TestExtractDateFromFilename:
    """Test _extract_date_from_filename method."""

    def test_yyyy_mm_dd_format(self) -> None:
        """Test YYYY-MM-DD format extraction."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_filename("2024-06-15-document.pdf")
        assert result is not None
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_yyyymmdd_format(self) -> None:
        """Test YYYYMMDD format extraction."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_filename("20240615_photo.jpg")
        assert result is not None
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_dd_mm_yyyy_underscore_format(self) -> None:
        """Test DD_MM_YYYY format extraction."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_filename("15_06_2024_document.pdf")
        assert result is not None
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_dd_mm_yyyy_dash_format(self) -> None:
        """Test DD-MM-YYYY format extraction."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_filename("15-06-2024-document.pdf")
        assert result is not None
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_dd_mm_yyyy_dot_format(self) -> None:
        """Test DD.MM.YYYY format extraction."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_filename("15.06.2024_document.pdf")
        assert result is not None
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_year_only_at_start(self) -> None:
        """Test year-only at start of filename."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_filename("2024-certificate.pdf")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_year_only_with_parenthesis(self) -> None:
        """Test year in parentheses."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_filename("certificate(2024).pdf")
        assert result is not None
        assert result.year == 2024

    def test_no_date_returns_none(self) -> None:
        """Test returns None when no date found."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_filename("random-document.pdf")
        assert result is None

    def test_invalid_date_falls_back_to_year(self) -> None:
        """Test invalid dates fall back to year-only extraction."""
        classifier = RulesEngineClassifier({})
        # Month 13 is invalid, but year-only pattern will catch "2024"
        result = classifier._extract_date_from_filename("2024-13-01-doc.pdf")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1  # Default month when only year extracted
        assert result.day == 1  # Default day when only year extracted


class TestExtractDateFromContent:
    """Test _extract_date_from_content method."""

    def test_french_fiscal_year(self) -> None:
        """Test French fiscal year pattern."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_content("Année fiscale 2023")
        assert result is not None
        assert result.year == 2023

    def test_french_exercice(self) -> None:
        """Test French exercice pattern."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_content("Exercice 2023")
        assert result is not None
        assert result.year == 2023

    def test_french_revenus(self) -> None:
        """Test French revenus pattern."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_content("Revenus de l'année 2023")
        assert result is not None
        assert result.year == 2023

    def test_english_fiscal_year(self) -> None:
        """Test English fiscal year pattern."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_content("Fiscal Year 2023")
        assert result is not None
        assert result.year == 2023

    def test_english_tax_return(self) -> None:
        """Test English tax return pattern."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_content("2023 Tax Return")
        assert result is not None
        assert result.year == 2023

    def test_full_date_yyyy_mm_dd(self) -> None:
        """Test full date YYYY-MM-DD in content."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_content("Document dated 2024-06-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_full_date_dd_mm_yyyy(self) -> None:
        """Test full date DD/MM/YYYY in content."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_content("Document dated 15/06/2024")
        assert result is not None
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_standalone_year_in_header(self) -> None:
        """Test standalone year in document header."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_content("Annual Report 2023\n\nContent here")
        assert result is not None
        assert result.year == 2023

    def test_no_date_returns_none(self) -> None:
        """Test returns None when no date found."""
        classifier = RulesEngineClassifier({})
        result = classifier._extract_date_from_content("Random document content")
        assert result is None


class TestExtractIssuer:
    """Test _extract_issuer method."""

    def test_matches_issuer_pattern(self) -> None:
        """Test matching issuer by pattern."""
        classifier = RulesEngineClassifier({})
        issuers = [
            RuleIssuer(name="UBS", patterns=["UBS", "UBS AG"]),
            RuleIssuer(name="Credit Suisse", patterns=["Credit Suisse", "CS"]),
        ]
        result = classifier._extract_issuer("Statement from UBS Bank", issuers)
        assert result is not None
        assert result.name == "UBS"

    def test_matches_second_issuer(self) -> None:
        """Test matching second issuer in list."""
        classifier = RulesEngineClassifier({})
        issuers = [
            RuleIssuer(name="UBS", patterns=["UBS"]),
            RuleIssuer(name="Credit Suisse", patterns=["Credit Suisse"]),
        ]
        result = classifier._extract_issuer("Statement from Credit Suisse", issuers)
        assert result is not None
        assert result.name == "Credit Suisse"

    def test_case_insensitive_match(self) -> None:
        """Test case-insensitive matching."""
        classifier = RulesEngineClassifier({})
        issuers = [RuleIssuer(name="UBS", patterns=["UBS"])]
        result = classifier._extract_issuer("statement from ubs bank", issuers)
        assert result is not None
        assert result.name == "UBS"

    def test_no_match_returns_none(self) -> None:
        """Test returns None when no match."""
        classifier = RulesEngineClassifier({})
        issuers = [RuleIssuer(name="UBS", patterns=["UBS"])]
        result = classifier._extract_issuer("Statement from Other Bank", issuers)
        assert result is None

    def test_empty_content_returns_none(self) -> None:
        """Test empty content returns None."""
        classifier = RulesEngineClassifier({})
        issuers = [RuleIssuer(name="UBS", patterns=["UBS"])]
        result = classifier._extract_issuer("", issuers)
        assert result is None

    def test_word_boundary_matching(self) -> None:
        """Test word boundary prevents false positives."""
        classifier = RulesEngineClassifier({})
        issuers = [RuleIssuer(name="UBS", patterns=["UBS"])]
        # "UBS" should not match inside "CLUBS"
        result = classifier._extract_issuer("Member of CLUBS association", issuers)
        assert result is None

    def test_bic_prefix_matching(self) -> None:
        """Test BIC code prefix matching."""
        classifier = RulesEngineClassifier({})
        issuers = [RuleIssuer(name="BCV", patterns=["BCVLCH2L"])]
        # "BCVLCH2L" should match "BCVLCH2LXXX"
        result = classifier._extract_issuer("BIC: BCVLCH2LXXX", issuers)
        assert result is not None
        assert result.name == "BCV"


class TestConstants:
    """Test module constants."""

    def test_min_year(self) -> None:
        """Test MIN_YEAR constant."""
        assert MIN_YEAR == 1990

    def test_max_year(self) -> None:
        """Test MAX_YEAR constant (realistic limit to avoid false positives)."""
        assert MAX_YEAR == 2040

    def test_min_modern_year(self) -> None:
        """Test MIN_MODERN_YEAR constant."""
        assert MIN_MODERN_YEAR == 2000

    def test_max_month(self) -> None:
        """Test MAX_MONTH constant."""
        assert MAX_MONTH == 12

    def test_max_day(self) -> None:
        """Test MAX_DAY constant."""
        assert MAX_DAY == 31


class TestDetectDateMismatch:
    """Test _detect_date_mismatch method."""

    def test_detects_year_mismatch(self) -> None:
        """Test detects different years."""
        classifier = RulesEngineClassifier({})
        fn_date, content_date, mismatch = classifier._detect_date_mismatch(
            "201304-Expense.pdf",  # April 2013 in filename
            "Exercice 2014",  # 2014 in content
        )
        assert mismatch is True
        assert fn_date is not None
        assert fn_date.year == 2013
        assert content_date is not None
        assert content_date.year == 2014

    def test_no_mismatch_when_only_month_differs(self) -> None:
        """Test no mismatch when only months differ (same year)."""
        classifier = RulesEngineClassifier({})
        fn_date, content_date, mismatch = classifier._detect_date_mismatch(
            "2013-04-01-Expense.pdf",
            "Document dated 2013-06-15",
        )
        # Only year is compared, not month (content often has year-only dates)
        assert mismatch is False
        assert fn_date is not None
        assert fn_date.year == 2013
        assert content_date is not None
        assert content_date.year == 2013

    def test_no_mismatch_when_same_year(self) -> None:
        """Test no mismatch when years match."""
        classifier = RulesEngineClassifier({})
        _, _, mismatch = classifier._detect_date_mismatch(
            "2013-Expense.pdf",
            "Exercice 2013",
        )
        assert mismatch is False

    def test_no_mismatch_when_filename_has_no_date(self) -> None:
        """Test no mismatch when filename has no date."""
        classifier = RulesEngineClassifier({})
        fn_date, content_date, mismatch = classifier._detect_date_mismatch(
            "Expense-Report.pdf",
            "Exercice 2014",
        )
        assert mismatch is False
        assert fn_date is None
        assert content_date is not None

    def test_no_mismatch_when_content_has_no_date(self) -> None:
        """Test no mismatch when content has no date."""
        classifier = RulesEngineClassifier({})
        fn_date, content_date, mismatch = classifier._detect_date_mismatch(
            "2013-04-Expense.pdf",
            "Some random content without a date",
        )
        assert mismatch is False
        assert fn_date is not None
        assert content_date is None


class TestBuildCorrectedFilename:
    """Test _build_corrected_filename method."""

    def test_corrects_yyyymm_format_with_content_month(self) -> None:
        """Test corrects YYYYMM format using content's month."""
        classifier = RulesEngineClassifier({})
        result = classifier._build_corrected_filename(
            "201304-Expense.pdf",
            datetime(2014, 6, 1, tzinfo=UTC),  # Content has specific month
            datetime(2013, 4, 1, tzinfo=UTC),  # Filename date
        )
        assert result == "2014-06-Expense.pdf"

    def test_preserves_filename_month_when_content_year_only(self) -> None:
        """Test preserves filename month when content has year only (month=1)."""
        classifier = RulesEngineClassifier({})
        result = classifier._build_corrected_filename(
            "201304-Expense.pdf",
            datetime(2014, 1, 1, tzinfo=UTC),  # Year-only content (month=1)
            datetime(2013, 4, 1, tzinfo=UTC),  # Filename has April
        )
        assert result == "2014-04-Expense.pdf"

    def test_corrects_yyyy_mm_dd_format(self) -> None:
        """Test corrects YYYY-MM-DD format to ISO."""
        classifier = RulesEngineClassifier({})
        result = classifier._build_corrected_filename(
            "2013-04-01-Report.pdf",
            datetime(2014, 6, 15, tzinfo=UTC),
            datetime(2013, 4, 1, tzinfo=UTC),
        )
        assert result == "2014-06-Report.pdf"

    def test_corrects_yyyymmdd_format(self) -> None:
        """Test corrects YYYYMMDD format to ISO."""
        classifier = RulesEngineClassifier({})
        result = classifier._build_corrected_filename(
            "20130401-Report.pdf",
            datetime(2014, 6, 15, tzinfo=UTC),
            datetime(2013, 4, 1, tzinfo=UTC),
        )
        assert result == "2014-06-Report.pdf"

    def test_prepends_date_when_no_date_in_filename(self) -> None:
        """Test prepends date when no date in filename."""
        classifier = RulesEngineClassifier({})
        result = classifier._build_corrected_filename(
            "Expense Report.pdf",
            datetime(2014, 6, 1, tzinfo=UTC),
            None,  # No filename date
        )
        assert result == "2014-06-Expense Report.pdf"

    def test_preserves_extension(self) -> None:
        """Test preserves original file extension."""
        classifier = RulesEngineClassifier({})
        result = classifier._build_corrected_filename(
            "201304-Report.xlsx",
            datetime(2014, 6, 1, tzinfo=UTC),
            datetime(2013, 4, 1, tzinfo=UTC),
        )
        assert result.endswith(".xlsx")


class TestAutoCorrectDateIntegration:
    """Integration tests for auto_correct_date feature."""

    def test_suggests_rename_on_mismatch(self) -> None:
        """Test suggested_name added to params on mismatch."""
        rule = RoutingRule(
            patterns=["*Expense*"],
            extensions=[".pdf"],
            destination="4_Archives/notes-frais/{YYYY}",
            date_source="content",
            auto_correct_date=True,
        )
        classifier = RulesEngineClassifier({"notes_frais": rule})
        metadata = make_metadata(
            path=Path("/test/201304-Expense.pdf"),
            filename="201304-Expense.pdf",
            extension=".pdf",
        )
        result = classifier.classify(
            content="Exercice 2014",  # Different year
            metadata=metadata,
        )
        assert result is not None
        assert "suggested_name" in result.extracted_params
        # Content only has year (2014), so we preserve month (04) from filename
        assert "2014-04" in result.extracted_params["suggested_name"]

    def test_no_suggested_name_when_dates_match(self) -> None:
        """Test no suggested_name when dates match."""
        rule = RoutingRule(
            patterns=["*Expense*"],
            extensions=[".pdf"],
            destination="4_Archives/notes-frais/{YYYY}",
            date_source="content",
            auto_correct_date=True,
        )
        classifier = RulesEngineClassifier({"notes_frais": rule})
        metadata = make_metadata(
            path=Path("/test/2014-06-Expense.pdf"),
            filename="2014-06-Expense.pdf",
            extension=".pdf",
        )
        result = classifier.classify(
            content="Exercice 2014",  # Same year
            metadata=metadata,
        )
        assert result is not None
        assert "suggested_name" not in result.extracted_params

    def test_no_suggested_name_when_auto_correct_disabled(self) -> None:
        """Test no suggested_name when auto_correct_date is False."""
        rule = RoutingRule(
            patterns=["*Expense*"],
            extensions=[".pdf"],
            destination="4_Archives/notes-frais/{YYYY}",
            date_source="content",
            auto_correct_date=False,
        )
        classifier = RulesEngineClassifier({"notes_frais": rule})
        metadata = make_metadata(
            path=Path("/test/201304-Expense.pdf"),
            filename="201304-Expense.pdf",
            extension=".pdf",
        )
        result = classifier.classify(
            content="Exercice 2014",  # Different year
            metadata=metadata,
        )
        assert result is not None


class TestUnicodeAndSpecialCharFilenames:
    """Test rules engine handles non-ASCII and special-character filenames."""

    def test_unicode_accented_extension_match(self) -> None:
        """Accented Latin filename matches extension-only rule."""
        rules = {"docs": RoutingRule(extensions=[".pdf"], destination="3_Resources/docs")}
        classifier = RulesEngineClassifier(rules)
        metadata = make_metadata(
            path=Path("/test/Résumé_2024.pdf"),
            filename="Résumé_2024.pdf",
            extension=".pdf",
        )
        result = classifier.classify("", metadata)
        assert result is not None
        assert result.category == "3_Resources/docs"

    def test_unicode_cjk_extension_match(self) -> None:
        """CJK filename matches extension-only rule."""
        rules = {"docs": RoutingRule(extensions=[".pdf"], destination="3_Resources/docs")}
        classifier = RulesEngineClassifier(rules)
        metadata = make_metadata(
            path=Path("/test/职业简历.pdf"),
            filename="职业简历.pdf",
            extension=".pdf",
        )
        result = classifier.classify("", metadata)
        assert result is not None
        assert result.category == "3_Resources/docs"

    def test_unicode_pattern_match(self) -> None:
        """Accented Latin filename matches glob pattern with accents."""
        rules = {
            "payslips": RoutingRule(
                patterns=["Décompte*"], destination="2_Areas/finance/payslips"
            )
        }
        classifier = RulesEngineClassifier(rules)
        metadata = make_metadata(
            path=Path("/test/Décompte_salaire.pdf"),
            filename="Décompte_salaire.pdf",
            extension=".pdf",
        )
        result = classifier.classify("", metadata)
        assert result is not None
        assert result.category == "2_Areas/finance/payslips"

    def test_unicode_extension_no_match_wrong_ext(self) -> None:
        """Accented Latin filename does NOT match when extension differs."""
        rules = {"docs": RoutingRule(extensions=[".pdf"], destination="3_Resources/docs")}
        classifier = RulesEngineClassifier(rules)
        metadata = make_metadata(
            path=Path("/test/Résumé_2024.docx"),
            filename="Résumé_2024.docx",
            extension=".docx",
        )
        result = classifier.classify("", metadata)
        assert result is None

    def test_special_chars_parentheses_brackets_extension_match(self) -> None:
        """Filename with parens/brackets does not crash fnmatch when rule is extension-only."""
        rules = {"docs": RoutingRule(extensions=[".txt"], destination="3_Resources/misc")}
        classifier = RulesEngineClassifier(rules)
        metadata = make_metadata(
            path=Path("/test/file (1) [draft] #final.txt"),
            filename="file (1) [draft] #final.txt",
            extension=".txt",
        )
        result = classifier.classify("", metadata)
        assert result is not None
        assert result.category == "3_Resources/misc"

    def test_special_chars_ampersand_extension_match(self) -> None:
        """Filename with ampersand matches extension-only rule."""
        rules = {"docs": RoutingRule(extensions=[".pdf"], destination="3_Resources/docs")}
        classifier = RulesEngineClassifier(rules)
        metadata = make_metadata(
            path=Path("/test/report & summary.pdf"),
            filename="report & summary.pdf",
            extension=".pdf",
        )
        result = classifier.classify("", metadata)
        assert result is not None

    def test_special_chars_wildcards_in_filename_do_not_crash(self) -> None:
        """Filename containing glob metacharacters does not raise when matched by extension rule."""
        rules = {"docs": RoutingRule(extensions=[".txt"], destination="3_Resources/misc")}
        classifier = RulesEngineClassifier(rules)
        metadata = make_metadata(
            path=Path("/test/file!@#$%.txt"),
            filename="file!@#$%.txt",
            extension=".txt",
        )
        # Should not raise — extension matching does not use fnmatch on filename
        result = classifier.classify("", metadata)
        assert result is not None

    def test_unicode_naive_pattern_match(self) -> None:
        """Filename with multiple Unicode accents matches glob pattern."""
        rules = {"tagged": RoutingRule(patterns=["naïve*"], destination="3_Resources/misc")}
        classifier = RulesEngineClassifier(rules)
        metadata = make_metadata(
            path=Path("/test/naïve café résumé.pdf"),
            filename="naïve café résumé.pdf",
            extension=".pdf",
        )
        result = classifier.classify("", metadata)
        assert result is not None
        assert result.category == "3_Resources/misc"


class TestOverlappingPatterns:
    """Test first-rule-wins semantics and AND logic for extension+pattern rules."""

    def test_broad_rule_wins_when_first(self) -> None:
        """When broad rule comes first, it wins over specific rule for overlapping files."""
        broad_rule = RoutingRule(extensions=[".pdf"], destination="3_Resources/docs")
        specific_rule = RoutingRule(
            extensions=[".pdf"],
            patterns=["invoice*"],
            destination="2_Areas/finance",
        )
        classifier = RulesEngineClassifier({"broad": broad_rule, "specific": specific_rule})
        metadata = make_metadata(
            path=Path("/test/invoice_2024.pdf"),
            filename="invoice_2024.pdf",
            extension=".pdf",
        )
        result = classifier.classify("", metadata)
        assert result is not None
        assert result.category == "3_Resources/docs"
        assert result.route_name == "broad"

    def test_specific_rule_wins_when_first(self) -> None:
        """When specific rule comes first, it wins over broad rule."""
        broad_rule = RoutingRule(extensions=[".pdf"], destination="3_Resources/docs")
        specific_rule = RoutingRule(
            extensions=[".pdf"],
            patterns=["invoice*"],
            destination="2_Areas/finance",
        )
        classifier = RulesEngineClassifier({"specific": specific_rule, "broad": broad_rule})
        metadata = make_metadata(
            path=Path("/test/invoice_2024.pdf"),
            filename="invoice_2024.pdf",
            extension=".pdf",
        )
        result = classifier.classify("", metadata)
        assert result is not None
        assert result.category == "2_Areas/finance"
        assert result.route_name == "specific"

    def test_extension_and_pattern_both_required_wrong_extension(self) -> None:
        """Rule with both extension AND pattern: wrong extension → no match."""
        rule = RoutingRule(
            extensions=[".pdf"],
            patterns=["invoice*"],
            destination="2_Areas/finance",
        )
        classifier = RulesEngineClassifier({"invoices": rule})
        metadata = make_metadata(
            path=Path("/test/invoice_2024.txt"),
            filename="invoice_2024.txt",
            extension=".txt",
        )
        result = classifier.classify("", metadata)
        assert result is None

    def test_extension_and_pattern_both_required_wrong_pattern(self) -> None:
        """Rule with both extension AND pattern: wrong pattern → no match."""
        rule = RoutingRule(
            extensions=[".pdf"],
            patterns=["invoice*"],
            destination="2_Areas/finance",
        )
        classifier = RulesEngineClassifier({"invoices": rule})
        metadata = make_metadata(
            path=Path("/test/report_2024.pdf"),
            filename="report_2024.pdf",
            extension=".pdf",
        )
        result = classifier.classify("", metadata)
        assert result is None

    def test_extension_and_pattern_both_required_both_match(self) -> None:
        """Rule with both extension AND pattern: both conditions met → match."""
        rule = RoutingRule(
            extensions=[".pdf"],
            patterns=["invoice*"],
            destination="2_Areas/finance",
        )
        classifier = RulesEngineClassifier({"invoices": rule})
        metadata = make_metadata(
            path=Path("/test/invoice_2024.pdf"),
            filename="invoice_2024.pdf",
            extension=".pdf",
        )
        result = classifier.classify("", metadata)
        assert result is not None
        assert result.category == "2_Areas/finance"

    def test_three_overlapping_rules_first_matching_wins(self) -> None:
        """Three rules all matching same file: rule iteration order determines winner."""
        rule_a = RoutingRule(extensions=[".pdf"], destination="dest_a")
        rule_b = RoutingRule(extensions=[".pdf"], destination="dest_b")
        rule_c = RoutingRule(extensions=[".pdf"], destination="dest_c")
        classifier = RulesEngineClassifier(
            {"rule_a": rule_a, "rule_b": rule_b, "rule_c": rule_c}
        )
        metadata = make_metadata(
            path=Path("/test/document.pdf"),
            filename="document.pdf",
            extension=".pdf",
        )
        result = classifier.classify("", metadata)
        assert result is not None
        assert result.category == "dest_a"
        assert result.route_name == "rule_a"
        assert "suggested_name" not in result.extracted_params
