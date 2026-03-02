"""Tests for the classifiers module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from para_files.classifiers.base import BaseClassifier
from para_files.classifiers.llm_classifier import LLMClassifier
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


class TestLLMClassifier:
    """Tests for LLMClassifier 0_Inbox rejection and sanitization."""

    @pytest.fixture
    def classifier(self) -> LLMClassifier:
        """Create a test LLM classifier."""
        return LLMClassifier(
            enabled=True,
            confidence_threshold=0.6,
            valid_categories=["3_Resources/documentation/Dell", "4_Archives/5y_divers/2024"],
        )

    def test_rejects_0_inbox_response(self, classifier: LLMClassifier):
        """LLM returning 0_Inbox should be treated as 'uncertain' and return None."""
        response = '{"category": "0_Inbox", "confidence": 1.0, "reasoning": "unsure"}'
        result = classifier._parse_response(response)
        assert result is None

    def test_accepts_valid_category(self, classifier: LLMClassifier):
        """LLM returning a valid PARA category should be accepted."""
        response = (
            '{"category": "3_Resources/documentation/Dell",'
            ' "confidence": 0.85, "reasoning": "Dell tech doc"}'
        )
        result = classifier._parse_response(response)
        assert result is not None
        assert result.category == "3_Resources/documentation/Dell"
        assert result.confidence.value == 0.85

    def test_rejects_low_confidence(self, classifier: LLMClassifier):
        """LLM response below threshold should return None."""
        response = (
            '{"category": "3_Resources/documentation/Dell",'
            ' "confidence": 0.3, "reasoning": "maybe Dell"}'
        )
        result = classifier._parse_response(response)
        assert result is None

    def test_rejects_absolute_path(self, classifier: LLMClassifier):
        """LLM returning an absolute path should be rejected."""
        response = (
            '{"category": "/home/user/3_Resources/docs", "confidence": 0.9, "reasoning": "x"}'
        )
        result = classifier._parse_response(response)
        assert result is None

    def test_rejects_non_para_category(self, classifier: LLMClassifier):
        """LLM returning a non-PARA category should be rejected."""
        response = '{"category": "random/folder", "confidence": 0.9, "reasoning": "x"}'
        result = classifier._parse_response(response)
        assert result is None

    def test_returns_none_when_disabled(self):
        """Disabled classifier should always return None."""
        classifier = LLMClassifier(enabled=False)
        result = classifier.classify("some content")
        assert result is None

    def test_returns_none_for_empty_content(self):
        """Empty content should return None."""
        classifier = LLMClassifier(enabled=True)
        result = classifier.classify("")
        assert result is None

    def test_system_prompt_excludes_0_inbox_instruction(self):
        """System prompt should not encourage returning 0_Inbox."""
        classifier = LLMClassifier(enabled=True, valid_categories=[])
        prompt = classifier._system_prompt
        assert "If unsure: use 0_Inbox" not in prompt
        assert "Use 0_Inbox ONLY" not in prompt
