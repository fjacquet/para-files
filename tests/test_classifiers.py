"""Tests for the classifiers module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from para_files.classifiers.base import BaseClassifier
from para_files.classifiers.rules_engine import RulesEngineClassifier
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
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


class TestRulesEngineClassifier:
    """Tests for RulesEngineClassifier (Signal 1 in v2.0)."""

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
