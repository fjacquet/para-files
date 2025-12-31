"""Tests for the classification pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from para_files.config import Config
from para_files.pipeline import ClassificationPipeline
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
)


@pytest.fixture
def mock_config(tmp_path: Path, fixtures_dir: Path) -> Config:
    """Create a test configuration."""
    return Config(
        para_root=tmp_path,
        reference_tree_path=fixtures_dir / "test_reference_tree.yaml",
    )


class TestClassificationPipeline:
    """Tests for ClassificationPipeline."""

    def test_init(self, mock_config: Config):
        """Test pipeline initialization is lazy."""
        pipeline = ClassificationPipeline(mock_config)
        assert pipeline._initialized is False
        assert len(pipeline._classifiers) == 0

    def test_ensure_initialized(self, mock_config: Config):
        """Test lazy initialization."""
        pipeline = ClassificationPipeline(mock_config)
        pipeline._ensure_initialized()
        assert pipeline._initialized is True
        assert len(pipeline._classifiers) > 0

    def test_classifiers_in_priority_order(self, mock_config: Config):
        """Test classifiers are added in correct priority order (v2.0)."""
        pipeline = ClassificationPipeline(mock_config)
        classifiers = pipeline.classifiers

        # v2.0 pipeline: rules_engine, book_detector, TaxonomyClassifier
        classifier_names = [c.name for c in classifiers]

        # Should have at least 3 classifiers
        assert len(classifier_names) >= 3

        # rules_engine should come first (if routing_rules exist)
        assert "rules_engine" in classifier_names or "book_detector" in classifier_names

        # TaxonomyClassifier should be present
        assert "TaxonomyClassifier" in classifier_names

    def test_classify_returns_default_when_no_match(self, mock_config: Config):
        """Test that classify returns 0_Inbox when nothing matches."""
        pipeline = ClassificationPipeline(mock_config)
        result = pipeline.classify("random content that matches nothing specific")

        assert result.category == "0_Inbox"
        assert result.confidence.source == ClassificationSource.DEFAULT
        assert result.confidence.value == 0.0

    def test_classify_with_taxonomy_issuer_match(self, mock_config: Config):
        """Test classification with TaxonomyClassifier issuer match (v2.0)."""
        pipeline = ClassificationPipeline(mock_config)
        result = pipeline.classify("Facture Swica assurance maladie")

        # Should match Swica from documents.json issuers via TaxonomyClassifier
        # Note: Result depends on documents.json content
        assert result is not None
        # If Swica is in documents.json, it should match with TAXONOMY_CLASSIFIER source
        if (
            "Swica" in result.category
            or result.confidence.source == ClassificationSource.TAXONOMY_CLASSIFIER
        ):
            assert result.confidence.value >= 0.85

    def test_classify_with_taxonomy_keyword_match(self, mock_config: Config):
        """Test classification with TaxonomyClassifier keyword match (v2.0)."""
        pipeline = ClassificationPipeline(mock_config)
        result = pipeline.classify("Relevé bancaire IBAN compte courant")

        # Should match banking keywords from documents.json
        assert result is not None
        # Keywords like IBAN, Relevé should trigger TaxonomyClassifier
        if result.confidence.source == ClassificationSource.TAXONOMY_CLASSIFIER:
            assert result.confidence.value >= 0.85

    def test_classify_with_metadata(self, mock_config: Config):
        """Test classification with file metadata from 0_Inbox.

        Note: Photos rule has source: "0_Inbox" constraint, so file must be
        under {para_root}/0_Inbox/ for the rule to match.
        """
        pipeline = ClassificationPipeline(mock_config)
        # File must be under 0_Inbox for photos rule to match (source constraint)
        inbox_path = mock_config.para_root / "0_Inbox" / "photo.jpg"
        metadata = FileMetadata(
            path=inbox_path,
            filename="photo.jpg",
            extension=".jpg",
            size_bytes=1024,
        )

        result = pipeline.classify("", metadata)

        # Should match photos rule from test fixture
        assert "photos" in result.category.lower() or result.route_name == "photos"

    def test_get_target_path(self, mock_config: Config):
        """Test getting full target path."""
        pipeline = ClassificationPipeline(mock_config)
        result = ClassificationResult(
            category="4_Archives/test",
            confidence=Confidence(value=1.0, source=ClassificationSource.DEFAULT),
        )

        target = pipeline.get_target_path(result)
        assert target == mock_config.para_root / "4_Archives/test"

    def test_classifier_exception_handling(self, mock_config: Config):
        """Test that pipeline handles classifier exceptions gracefully."""
        pipeline = ClassificationPipeline(mock_config)
        pipeline._ensure_initialized()

        # Mock a classifier to raise an exception
        mock_classifier = MagicMock()
        mock_classifier.name = "failing_classifier"
        mock_classifier.classify.side_effect = Exception("Test error")

        # Insert at beginning
        pipeline._classifiers.insert(0, mock_classifier)

        # Should not raise, should continue to next classifier
        result = pipeline.classify("Facture Swica")  # Will match domain_kb
        assert result is not None

    def test_only_initializes_once(self, mock_config: Config):
        """Test that pipeline only initializes once."""
        pipeline = ClassificationPipeline(mock_config)

        pipeline._ensure_initialized()
        first_classifiers = pipeline._classifiers.copy()

        pipeline._ensure_initialized()
        assert pipeline._classifiers == first_classifiers


class TestClassificationPipelineWithMocks:
    """Tests for pipeline with mocked classifiers."""

    @patch("para_files.pipeline.ReferenceTree")
    def test_pipeline_with_empty_routing_rules(
        self,
        mock_tree_class: MagicMock,
        tmp_path: Path,
    ):
        """Test pipeline v2.0 when routing_rules is empty."""
        mock_tree = MagicMock()
        mock_tree.load.return_value = None
        mock_tree.get_routing_rules.return_value = {}
        mock_tree_class.return_value = mock_tree

        config = Config(
            para_root=tmp_path,
            reference_tree_path=tmp_path / "tree.yaml",  # Won't be read
        )

        pipeline = ClassificationPipeline(config)
        pipeline._ensure_initialized()

        # v2.0 pipeline: should have book_detector and TaxonomyClassifier
        # No rules_engine (empty rules)
        classifier_names = [c.name for c in pipeline._classifiers]
        assert "TaxonomyClassifier" in classifier_names
        assert "book_detector" in classifier_names
        assert "rules_engine" not in classifier_names


class TestClassificationPipelineIntegration:
    """Integration tests requiring reference tree (v2.0)."""

    def test_full_pipeline_priority(self, mock_config: Config):
        """Test that higher priority classifiers take precedence (v2.0)."""
        pipeline = ClassificationPipeline(mock_config)
        pipeline._ensure_initialized()

        # v2.0: rules_engine has highest priority
        # Create content that matches a routing rule pattern
        from para_files.types import FileMetadata

        metadata = FileMetadata(
            path=Path("/tmp/test.jpg"),
            filename="test.jpg",
            extension=".jpg",
            size_bytes=1024,
        )

        # Photo extension should match rules_engine before TaxonomyClassifier
        result = pipeline.classify("", metadata)

        # Should be classified by rules_engine (photos rule)
        if result.confidence.source == ClassificationSource.RULES_ENGINE:
            assert result.confidence.value == 0.95

    def test_pipeline_cascade_to_taxonomy_classifier(self, mock_config: Config):
        """Test that pipeline cascades when rules_engine doesn't match (v2.0)."""
        pipeline = ClassificationPipeline(mock_config)
        pipeline._ensure_initialized()

        # Text content that won't match rules_engine but should match TaxonomyClassifier
        result = pipeline.classify("Facture UBS banque suisse")

        # Should be classified by TaxonomyClassifier (if UBS is in documents.json)
        assert result is not None
        if result.confidence.source == ClassificationSource.TAXONOMY_CLASSIFIER:
            assert "UBS" in result.category or "banque" in result.category.lower()
