"""Tests for the types module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
    IssuerCategory,
    KnownIssuers,
    Route,
    RoutingRule,
)


class TestClassificationSource:
    """Tests for ClassificationSource enum."""

    def test_all_sources_defined(self):
        """Verify all expected sources exist (v2.0 pipeline)."""
        # Active sources in v2.0
        assert ClassificationSource.RULES_ENGINE == "rules_engine"
        assert ClassificationSource.BOOK_DETECTOR == "book_detector"
        assert ClassificationSource.TAXONOMY_CLASSIFIER == "taxonomy_classifier"
        assert ClassificationSource.LLM_FALLBACK == "llm_fallback"
        assert ClassificationSource.DEFAULT == "default"
        # Deprecated sources (kept for backward compatibility)
        assert ClassificationSource.VALIDATED_DB == "validated_db"
        assert ClassificationSource.DOMAIN_KB == "domain_kb"
        assert ClassificationSource.SEMANTIC_ROUTER == "semantic_router"

    def test_source_count(self):
        """Verify we have exactly 8 sources (v2.0 pipeline with TAXONOMY_CLASSIFIER)."""
        assert len(ClassificationSource) == 8


class TestConfidence:
    """Tests for Confidence model."""

    def test_valid_confidence(self):
        """Test creating confidence with valid values."""
        conf = Confidence(value=0.85, source=ClassificationSource.SEMANTIC_ROUTER)
        assert conf.value == 0.85
        assert conf.source == ClassificationSource.SEMANTIC_ROUTER

    def test_confidence_boundary_values(self):
        """Test confidence at boundaries."""
        low = Confidence(value=0.0, source=ClassificationSource.DEFAULT)
        high = Confidence(value=1.0, source=ClassificationSource.VALIDATED_DB)
        assert low.value == 0.0
        assert high.value == 1.0

    def test_confidence_below_zero_fails(self):
        """Test that negative confidence fails validation."""
        with pytest.raises(ValidationError):
            Confidence(value=-0.1, source=ClassificationSource.DEFAULT)

    def test_confidence_above_one_fails(self):
        """Test that confidence above 1.0 fails validation."""
        with pytest.raises(ValidationError):
            Confidence(value=1.1, source=ClassificationSource.DEFAULT)


class TestRoute:
    """Tests for Route model."""

    def test_minimal_route(self):
        """Test creating route with minimal fields."""
        route = Route(name="test", pattern="4_Archives/test")
        assert route.name == "test"
        assert route.pattern == "4_Archives/test"
        assert route.utterances == []
        assert route.preserve_structure is False
        assert route.date_format is None

    def test_full_route(self):
        """Test creating route with all fields."""
        route = Route(
            name="factures_assurance",
            pattern="4_Archives/factures/{year}/_Assurances/{issuer}",
            utterances=["facture assurance", "police d'assurance", "prime annuelle"],
            preserve_structure=True,
            date_format="YYYY/MM",
        )
        assert route.name == "factures_assurance"
        assert len(route.utterances) == 3
        assert route.preserve_structure is True
        assert route.date_format == "YYYY/MM"


class TestRoutingRule:
    """Tests for RoutingRule model."""

    def test_photo_routing_rule(self):
        """Test creating a photo routing rule."""
        rule = RoutingRule(
            source="0_Inbox",
            extensions=[".jpg", ".jpeg", ".png", ".heic"],
            destination="4_Archives/photos/{YYYY}/{MM}/{DD}",
            date_source="exif",
            fallback_date="file_modified",
        )
        assert rule.source == "0_Inbox"
        assert ".jpg" in rule.extensions
        assert rule.date_source == "exif"

    def test_screenshot_routing_rule(self):
        """Test creating a screenshot routing rule with patterns."""
        rule = RoutingRule(
            patterns=["Screenshot*", "Capture*", "Screen Shot*"],
            destination="4_Archives/screenshots/{YYYY}/{MM}",
        )
        assert len(rule.patterns) == 3
        assert "Screenshot*" in rule.patterns


class TestFileMetadata:
    """Tests for FileMetadata model."""

    def test_minimal_metadata(self):
        """Test creating metadata with minimal fields."""
        meta = FileMetadata(
            path=Path("/tmp/test.pdf"),
            filename="test.pdf",
            extension=".pdf",
            size_bytes=1024,
        )
        assert meta.filename == "test.pdf"
        assert meta.extension == ".pdf"
        assert meta.size_bytes == 1024
        assert meta.created_at is None
        assert meta.content_preview is None

    def test_full_metadata(self):
        """Test creating metadata with all fields."""
        now = datetime.now()
        meta = FileMetadata(
            path=Path("/home/user/Documents/invoice.pdf"),
            filename="invoice.pdf",
            extension=".pdf",
            size_bytes=50000,
            created_at=now,
            modified_at=now,
            content_preview="FACTURE No. 2025-001 - Swica Assurance...",
        )
        assert meta.created_at == now
        assert "Swica" in (meta.content_preview or "")

    def test_negative_size_fails(self):
        """Test that negative file size fails validation."""
        with pytest.raises(ValidationError):
            FileMetadata(
                path=Path("/tmp/test.pdf"),
                filename="test.pdf",
                extension=".pdf",
                size_bytes=-1,
            )


class TestKnownIssuers:
    """Tests for KnownIssuers model."""

    def test_empty_issuers(self):
        """Test creating empty known issuers."""
        issuers = KnownIssuers()
        assert issuers.categories == {}
        assert len(issuers.all_issuers()) == 0
        assert issuers.list_categories() == []

    def test_populated_issuers(self):
        """Test creating populated known issuers with dynamic categories."""
        issuers = KnownIssuers(
            categories={
                "assurances": IssuerCategory(
                    pattern="4_Archives/factures/{year}/Assurances/{issuer}",
                    issuers=["Swica", "CSS", "Helsana"],
                ),
                "banques": IssuerCategory(
                    pattern="4_Archives/factures/{year}/Banques/{issuer}",
                    issuers=["UBS", "Credit Suisse", "PostFinance"],
                ),
                "energie": IssuerCategory(
                    pattern="4_Archives/factures/{year}/Energie/{issuer}",
                    issuers=["SIG", "Romande Energie"],
                ),
            }
        )
        assert len(issuers.get_issuers("assurances")) == 3
        assert len(issuers.get_issuers("banques")) == 3
        assert len(issuers.list_categories()) == 3

    def test_all_issuers_mapping(self):
        """Test the all_issuers() method returns correct mapping."""
        issuers = KnownIssuers(
            categories={
                "assurances": IssuerCategory(
                    pattern="4_Archives/factures/{year}/Assurances/{issuer}",
                    issuers=["Swica"],
                ),
                "banques": IssuerCategory(
                    pattern="4_Archives/factures/{year}/Banques/{issuer}",
                    issuers=["UBS"],
                ),
            }
        )
        mapping = issuers.all_issuers()
        assert mapping["swica"] == "assurances"
        assert mapping["ubs"] == "banques"

    def test_all_issuers_case_insensitive(self):
        """Test that issuer lookup is case-insensitive."""
        issuers = KnownIssuers(
            categories={
                "assurances": IssuerCategory(
                    pattern="4_Archives/factures/{year}/Assurances/{issuer}",
                    issuers=["SWICA", "Helsana"],
                ),
            }
        )
        mapping = issuers.all_issuers()
        assert "swica" in mapping
        assert "helsana" in mapping

    def test_get_pattern(self):
        """Test get_pattern returns correct pattern for category."""
        issuers = KnownIssuers(
            categories={
                "transport": IssuerCategory(
                    pattern="4_Archives/factures/{year}/Mobilité/{issuer}",
                    issuers=["MOB", "CFF"],
                ),
            }
        )
        assert issuers.get_pattern("transport") == "4_Archives/factures/{year}/Mobilité/{issuer}"
        # Unknown category returns default pattern
        assert "/_Other/" in issuers.get_pattern("unknown")

    def test_get_issuers(self):
        """Test get_issuers returns correct list for category."""
        issuers = KnownIssuers(
            categories={
                "cloud": IssuerCategory(
                    pattern="4_Archives/factures/{year}/Cloud/{issuer}",
                    issuers=["Netflix", "Spotify"],
                ),
            }
        )
        assert issuers.get_issuers("cloud") == ["Netflix", "Spotify"]
        assert issuers.get_issuers("unknown") == []


class TestClassificationResult:
    """Tests for ClassificationResult model."""

    def test_minimal_result(self):
        """Test creating result with minimal fields."""
        result = ClassificationResult(
            category="0_Inbox",
            confidence=Confidence(value=0.5, source=ClassificationSource.DEFAULT),
        )
        assert result.category == "0_Inbox"
        assert result.route_name is None
        assert result.extracted_params == {}

    def test_full_result(self):
        """Test creating result with all fields."""
        result = ClassificationResult(
            category="4_Archives/factures/2025/_Assurances/Swica",
            confidence=Confidence(value=0.90, source=ClassificationSource.DOMAIN_KB),
            route_name="factures_assurance",
            extracted_params={"year": "2025", "issuer": "Swica"},
            raw_score=0.923,
        )
        assert result.route_name == "factures_assurance"
        assert result.extracted_params["issuer"] == "Swica"
        assert result.raw_score == 0.923
