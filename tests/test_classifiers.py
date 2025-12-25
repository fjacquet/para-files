"""Tests for the classifiers module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from para_files.classifiers.base import BaseClassifier
from para_files.classifiers.domain_kb import DomainKBClassifier
from para_files.classifiers.rules_engine import RulesEngineClassifier
from para_files.classifiers.validated_db import ValidatedDBClassifier
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
    KnownIssuers,
    RoutingRule,
)


class ConcreteClassifier(BaseClassifier):
    """Concrete implementation for testing abstract base."""

    @property
    def name(self) -> str:
        return "test_classifier"

    @property
    def source(self) -> ClassificationSource:
        return ClassificationSource.DEFAULT

    @property
    def default_confidence(self) -> float:
        return 0.5

    def classify(
        self,
        content: str,
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        if "match" in content:
            return ClassificationResult(
                category="test/category",
                confidence=Confidence(value=self.default_confidence, source=self.source),
            )
        return None


class TestBaseClassifier:
    """Tests for abstract BaseClassifier."""

    def test_cannot_instantiate_abstract(self):
        """Test that BaseClassifier cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseClassifier()  # type: ignore[abstract]

    def test_concrete_implementation(self):
        """Test concrete classifier works."""
        classifier = ConcreteClassifier()
        assert classifier.name == "test_classifier"
        assert classifier.source == ClassificationSource.DEFAULT
        assert classifier.default_confidence == 0.5

    def test_classify_match(self):
        """Test classification when content matches."""
        classifier = ConcreteClassifier()
        result = classifier.classify("this should match")
        assert result is not None
        assert result.category == "test/category"

    def test_classify_no_match(self):
        """Test classification when content doesn't match."""
        classifier = ConcreteClassifier()
        result = classifier.classify("no keyword here")
        assert result is None


class TestValidatedDBClassifier:
    """Tests for ValidatedDBClassifier (Signal 1)."""

    def test_init_empty(self):
        """Test initialization without database."""
        classifier = ValidatedDBClassifier()
        assert classifier.name == "validated_db"
        assert classifier.source == ClassificationSource.VALIDATED_DB
        assert classifier.default_confidence == 1.0

    def test_add_mapping(self):
        """Test adding a mapping programmatically."""
        classifier = ValidatedDBClassifier()
        classifier.add_mapping("test@example.com", "4_Archives/test")

        result = classifier.classify("Email from test@example.com")
        assert result is not None
        assert result.category == "4_Archives/test"
        assert result.confidence.value == 1.0

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        classifier = ValidatedDBClassifier()
        classifier.add_mapping("SWICA", "4_Archives/assurances/Swica")

        result = classifier.classify("Invoice from swica insurance")
        assert result is not None
        assert "swica" in result.extracted_params.get("validated_sender", "")

    def test_no_match(self):
        """Test when no mapping matches."""
        classifier = ValidatedDBClassifier()
        classifier.add_mapping("known@example.com", "4_Archives/known")

        result = classifier.classify("Email from unknown@other.com")
        assert result is None

    def test_load_from_file(self, tmp_path: Path):
        """Test loading mappings from JSON file."""
        db_file = tmp_path / "validated.json"
        db_file.write_text('{"mappings": {"test@mail.com": "4_Archives/test"}}')

        classifier = ValidatedDBClassifier(db_path=db_file)
        result = classifier.classify("From test@mail.com")
        assert result is not None
        assert result.category == "4_Archives/test"

    def test_save_db(self, tmp_path: Path):
        """Test saving mappings to JSON file."""
        db_file = tmp_path / "validated.json"
        classifier = ValidatedDBClassifier(db_path=db_file)
        classifier.add_mapping("new@example.com", "4_Archives/new")
        classifier.save_db()

        # Verify file was written
        assert db_file.exists()
        import json

        data = json.loads(db_file.read_text())
        assert "new@example.com" in data["mappings"]


class TestRulesEngineClassifier:
    """Tests for RulesEngineClassifier (Signal 2)."""

    @pytest.fixture
    def photo_rules(self) -> dict[str, RoutingRule]:
        """Create sample photo routing rules."""
        return {
            "photos": RoutingRule(
                extensions=[".jpg", ".jpeg", ".png", ".heic"],
                destination="4_Archives/photos/{YYYY}/{MM}",
            ),
            "screenshots": RoutingRule(
                patterns=["Screenshot*", "Capture*"],
                destination="4_Archives/screenshots/{YYYY}/{MM}",
            ),
        }

    def test_init(self, photo_rules: dict[str, RoutingRule]):
        """Test initialization."""
        classifier = RulesEngineClassifier(photo_rules)
        assert classifier.name == "rules_engine"
        assert classifier.source == ClassificationSource.RULES_ENGINE
        assert classifier.default_confidence == 0.95

    def test_match_by_extension(self, photo_rules: dict[str, RoutingRule]):
        """Test matching by file extension."""
        classifier = RulesEngineClassifier(photo_rules)
        metadata = FileMetadata(
            path=Path("/tmp/photo.jpg"),
            filename="photo.jpg",
            extension=".jpg",
            size_bytes=1024,
            modified_at=datetime(2025, 6, 15),
        )

        result = classifier.classify("", metadata)
        assert result is not None
        assert result.route_name == "photos"
        assert "2025" in result.category
        assert "06" in result.category

    def test_match_by_pattern(self, photo_rules: dict[str, RoutingRule]):
        """Test matching by filename pattern."""
        classifier = RulesEngineClassifier(photo_rules)
        metadata = FileMetadata(
            path=Path("/tmp/Screenshot 2025-01-01.bmp"),
            filename="Screenshot 2025-01-01.bmp",
            extension=".bmp",
            size_bytes=2048,
            modified_at=datetime(2025, 1, 1),
        )

        result = classifier.classify("", metadata)
        assert result is not None
        assert result.route_name == "screenshots"

    def test_no_match_without_metadata(self, photo_rules: dict[str, RoutingRule]):
        """Test that classifier returns None without metadata."""
        classifier = RulesEngineClassifier(photo_rules)
        result = classifier.classify("some content")
        assert result is None

    def test_no_match_unknown_extension(self, photo_rules: dict[str, RoutingRule]):
        """Test no match for unknown extension."""
        classifier = RulesEngineClassifier(photo_rules)
        metadata = FileMetadata(
            path=Path("/tmp/document.pdf"),
            filename="document.pdf",
            extension=".pdf",
            size_bytes=5000,
        )

        result = classifier.classify("", metadata)
        assert result is None


class TestDomainKBClassifier:
    """Tests for DomainKBClassifier (Signal 3)."""

    @pytest.fixture
    def known_issuers(self) -> KnownIssuers:
        """Create sample known issuers."""
        return KnownIssuers(
            assurances=["Swica", "CSS", "Helsana"],
            banques=["UBS", "Credit Suisse"],
            energie=["SIG"],
            telephonie=["Swisscom"],
            cloud=["AWS", "Azure"],
        )

    def test_init(self, known_issuers: KnownIssuers):
        """Test initialization."""
        classifier = DomainKBClassifier(known_issuers)
        assert classifier.name == "domain_kb"
        assert classifier.source == ClassificationSource.DOMAIN_KB
        assert classifier.default_confidence == 0.90

    def test_match_assurance(self, known_issuers: KnownIssuers):
        """Test matching insurance issuer."""
        classifier = DomainKBClassifier(known_issuers)
        result = classifier.classify("FACTURE - Swica Assurance Maladie SA")
        assert result is not None
        assert "Assurances" in result.category
        assert "Swica" in result.category
        assert result.extracted_params["issuer"] == "Swica"

    def test_match_banque(self, known_issuers: KnownIssuers):
        """Test matching bank issuer."""
        classifier = DomainKBClassifier(known_issuers)
        result = classifier.classify("Relevé de compte UBS Switzerland")
        assert result is not None
        assert "Banques" in result.category
        assert "UBS" in result.category

    def test_match_energie(self, known_issuers: KnownIssuers):
        """Test matching energy issuer."""
        classifier = DomainKBClassifier(known_issuers)
        result = classifier.classify("Facture électricité SIG Genève")
        assert result is not None
        assert "Energie" in result.category
        assert "SIG" in result.category

    def test_case_insensitive(self, known_issuers: KnownIssuers):
        """Test case-insensitive matching."""
        classifier = DomainKBClassifier(known_issuers)
        result = classifier.classify("Invoice from AWS cloud services")
        assert result is not None
        assert "Cloud" in result.category
        assert result.extracted_params["issuer"] == "AWS"

    def test_word_boundary_matching(self, known_issuers: KnownIssuers):
        """Test that partial matches don't trigger."""
        classifier = DomainKBClassifier(known_issuers)
        # "AWSOME" should not match "AWS"
        result = classifier.classify("AWSOME product invoice")
        assert result is None

    def test_no_match(self, known_issuers: KnownIssuers):
        """Test when no issuer matches."""
        classifier = DomainKBClassifier(known_issuers)
        result = classifier.classify("Invoice from Unknown Company SA")
        assert result is None

    def test_uses_file_date(self, known_issuers: KnownIssuers):
        """Test that file date is used for year in path."""
        classifier = DomainKBClassifier(known_issuers)
        metadata = FileMetadata(
            path=Path("/tmp/invoice.pdf"),
            filename="invoice.pdf",
            extension=".pdf",
            size_bytes=1000,
            modified_at=datetime(2024, 3, 15),
        )

        result = classifier.classify("Facture Swisscom mobile", metadata)
        assert result is not None
        assert "2024" in result.category
