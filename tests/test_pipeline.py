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
        """Test classifiers are added in correct priority order."""
        pipeline = ClassificationPipeline(mock_config)
        classifiers = pipeline.classifiers

        # Should have at least validated_db, rules_engine, domain_kb
        classifier_names = [c.name for c in classifiers]
        assert "validated_db" in classifier_names

        # validated_db should come first
        assert classifier_names[0] == "validated_db"

    def test_classify_returns_default_when_no_match(self, mock_config: Config):
        """Test that classify returns 0_Inbox when nothing matches."""
        pipeline = ClassificationPipeline(mock_config)
        result = pipeline.classify("random content that matches nothing specific")

        assert result.category == "0_Inbox"
        assert result.confidence.source == ClassificationSource.DEFAULT
        assert result.confidence.value == 0.0

    def test_classify_with_validated_db_match(self, mock_config: Config):
        """Test classification with validated DB match."""
        pipeline = ClassificationPipeline(mock_config)
        pipeline._ensure_initialized()

        # Add a mapping to the validated DB classifier
        validated_db = pipeline._classifiers[0]
        validated_db.add_mapping("test@known.com", "4_Archives/known")

        result = pipeline.classify("Email from test@known.com with invoice")

        assert result.category == "4_Archives/known"
        assert result.confidence.value == 1.0
        assert result.confidence.source == ClassificationSource.VALIDATED_DB

    def test_classify_with_domain_kb_match(self, mock_config: Config):
        """Test classification with domain KB match."""
        pipeline = ClassificationPipeline(mock_config)
        result = pipeline.classify("Facture Swica assurance maladie")

        # Should match Swica from known_issuers in test fixture
        assert "Swica" in result.category
        assert result.confidence.source == ClassificationSource.DOMAIN_KB

    def test_classify_with_metadata(self, mock_config: Config):
        """Test classification with file metadata."""
        pipeline = ClassificationPipeline(mock_config)
        metadata = FileMetadata(
            path=Path("/tmp/photo.jpg"),
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
    def test_pipeline_skips_empty_routes(
        self,
        mock_tree_class: MagicMock,
        tmp_path: Path,
    ):
        """Test that pipeline skips semantic router when no routes have utterances."""
        mock_tree = MagicMock()
        mock_tree.load.return_value = None
        mock_tree.get_routing_rules.return_value = {}
        mock_tree.get_known_issuers.return_value = MagicMock(
            assurances=[],
            banques=[],
            energie=[],
            telephonie=[],
            cloud=[],
        )
        mock_tree.get_all_routes.return_value = []
        mock_tree_class.return_value = mock_tree

        config = Config(
            para_root=tmp_path,
            reference_tree_path=tmp_path / "tree.yaml",  # Won't be read
        )

        pipeline = ClassificationPipeline(config)
        pipeline._ensure_initialized()

        # Should have validated_db and domain_kb (even empty issuers is truthy as a mock)
        # No rules_engine (empty rules) and no semantic_router (no routes)
        classifier_names = [c.name for c in pipeline._classifiers]
        assert "validated_db" in classifier_names
        assert "semantic_router" not in classifier_names
        assert "rules_engine" not in classifier_names


class TestClassificationPipelineIntegration:
    """Integration tests requiring reference tree."""

    def test_full_pipeline_priority(self, mock_config: Config):
        """Test that higher priority classifiers take precedence."""
        pipeline = ClassificationPipeline(mock_config)
        pipeline._ensure_initialized()

        # Add validated mapping that would also match domain_kb
        validated_db = pipeline._classifiers[0]
        validated_db.add_mapping("swica", "OVERRIDE/path")

        # Should use validated_db (100%) over domain_kb (90%)
        result = pipeline.classify("Facture Swica assurance")
        assert result.category == "OVERRIDE/path"
        assert result.confidence.source == ClassificationSource.VALIDATED_DB

    def test_pipeline_cascade_to_second_classifier(self, mock_config: Config):
        """Test that pipeline cascades when first classifier doesn't match."""
        pipeline = ClassificationPipeline(mock_config)
        pipeline._ensure_initialized()

        # validated_db won't match this, but domain_kb should
        result = pipeline.classify("Facture UBS banque")

        # Should be classified by domain_kb (banks)
        assert result.confidence.source == ClassificationSource.DOMAIN_KB
        assert "UBS" in result.category
