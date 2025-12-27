"""Tests for the semantic router classifier module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from para_files.classifiers.semantic_router import SemanticRouterClassifier
from para_files.types import ClassificationSource, Route


class MockEncoder:
    """Mock encoder for testing."""

    max_chars = 20000

    def __call__(self, texts: list[str]) -> list[list[float]]:
        """Return mock embeddings."""
        return [[0.1] * 768 for _ in texts]


class TestSemanticRouterClassifier:
    """Tests for SemanticRouterClassifier."""

    def test_name(self):
        """Test classifier name."""
        encoder = MockEncoder()
        classifier = SemanticRouterClassifier(encoder=encoder, routes=[])
        assert classifier.name == "semantic_router"

    def test_source(self):
        """Test classification source."""
        encoder = MockEncoder()
        classifier = SemanticRouterClassifier(encoder=encoder, routes=[])
        assert classifier.source == ClassificationSource.SEMANTIC_ROUTER

    def test_default_confidence(self):
        """Test default confidence is 85%."""
        encoder = MockEncoder()
        classifier = SemanticRouterClassifier(encoder=encoder, routes=[])
        assert classifier.default_confidence == 0.85

    def test_classify_empty_content(self):
        """Test classify returns None for empty content."""
        encoder = MockEncoder()
        classifier = SemanticRouterClassifier(encoder=encoder, routes=[])
        result = classifier.classify("")
        assert result is None

    def test_classify_whitespace_only(self):
        """Test classify returns None for whitespace-only content."""
        encoder = MockEncoder()
        classifier = SemanticRouterClassifier(encoder=encoder, routes=[])
        result = classifier.classify("   \n\t  ")
        assert result is None

    def test_get_routes_with_utterances(self):
        """Test getting routes that have utterances."""
        encoder = MockEncoder()
        routes = [
            Route(name="test1", pattern="test/1", utterances=["utterance1"]),
            Route(name="test2", pattern="test/2", utterances=[]),  # No utterances
            Route(name="test3", pattern="test/3", utterances=["utterance3"]),
        ]
        classifier = SemanticRouterClassifier(encoder=encoder, routes=routes)

        routes_with_utterances = classifier.get_routes_with_utterances()
        assert len(routes_with_utterances) == 2
        assert routes_with_utterances[0].name == "test1"
        assert routes_with_utterances[1].name == "test3"

    @patch("para_files.classifiers.semantic_router.SemanticRouter")
    def test_ensure_router_builds_once(self, mock_sr_class: MagicMock):
        """Test that router is built lazily and only once."""
        mock_router = MagicMock()
        mock_sr_class.return_value = mock_router

        encoder = MockEncoder()
        routes = [
            Route(name="test", pattern="test/pattern", utterances=["utterance"]),
        ]
        classifier = SemanticRouterClassifier(encoder=encoder, routes=routes)

        # Call _ensure_router multiple times
        router1 = classifier._ensure_router()
        router2 = classifier._ensure_router()

        # Should be the same instance
        assert router1 is router2
        # SemanticRouter should only be constructed once
        assert mock_sr_class.call_count == 1

    @patch("para_files.classifiers.semantic_router.SemanticRouter")
    def test_classify_no_match(self, mock_sr_class: MagicMock):
        """Test classify when no route matches."""
        mock_router = MagicMock()
        mock_router.return_value = MagicMock(name=None, similarity_score=None)
        mock_sr_class.return_value = mock_router

        encoder = MockEncoder()
        routes = [
            Route(name="test", pattern="test/pattern", utterances=["utterance"]),
        ]
        classifier = SemanticRouterClassifier(encoder=encoder, routes=routes)

        result = classifier.classify("some content that doesn't match")
        assert result is None

    @patch("para_files.classifiers.semantic_router.SemanticRouter")
    def test_classify_match_not_in_route_map(self, mock_sr_class: MagicMock):
        """Test classify when matched route is not in route map."""
        mock_router = MagicMock()
        mock_choice = MagicMock()
        mock_choice.name = "unknown_route"
        mock_choice.similarity_score = 0.9
        mock_router.return_value = mock_choice
        mock_sr_class.return_value = mock_router

        encoder = MockEncoder()
        routes = [
            Route(name="test", pattern="test/pattern", utterances=["utterance"]),
        ]
        classifier = SemanticRouterClassifier(encoder=encoder, routes=routes)

        result = classifier.classify("some content")
        assert result is None

    @patch("para_files.classifiers.semantic_router.SemanticRouter")
    def test_classify_success(self, mock_sr_class: MagicMock):
        """Test successful classification."""
        mock_router = MagicMock()
        mock_choice = MagicMock()
        mock_choice.name = "factures"
        mock_choice.similarity_score = 0.9
        mock_router.return_value = mock_choice
        mock_sr_class.return_value = mock_router

        encoder = MockEncoder()
        routes = [
            Route(name="factures", pattern="4_Archives/factures", utterances=["invoice"]),
        ]
        classifier = SemanticRouterClassifier(encoder=encoder, routes=routes)

        result = classifier.classify("invoice from company")

        assert result is not None
        assert result.category == "4_Archives/factures"
        assert result.confidence.value == 0.85
        assert result.route_name == "factures"

    @patch("para_files.classifiers.semantic_router.SemanticRouter")
    def test_classify_list_result(self, mock_sr_class: MagicMock):
        """Test classify when router returns a list."""
        mock_router = MagicMock()
        mock_choice = MagicMock()
        mock_choice.name = "factures"
        mock_choice.similarity_score = 0.9
        mock_router.return_value = [mock_choice]  # Return as list
        mock_sr_class.return_value = mock_router

        encoder = MockEncoder()
        routes = [
            Route(name="factures", pattern="4_Archives/factures", utterances=["invoice"]),
        ]
        classifier = SemanticRouterClassifier(encoder=encoder, routes=routes)

        result = classifier.classify("invoice content")

        assert result is not None
        assert result.category == "4_Archives/factures"

    @patch("para_files.classifiers.semantic_router.SemanticRouter")
    def test_classify_empty_list_result(self, mock_sr_class: MagicMock):
        """Test classify when router returns empty list."""
        mock_router = MagicMock()
        mock_router.return_value = []  # Empty list
        mock_sr_class.return_value = mock_router

        encoder = MockEncoder()
        routes = [
            Route(name="test", pattern="test/pattern", utterances=["utterance"]),
        ]
        classifier = SemanticRouterClassifier(encoder=encoder, routes=routes)

        result = classifier.classify("content")
        assert result is None

    @patch("para_files.classifiers.semantic_router.SemanticRouter")
    def test_classify_truncates_long_content(self, mock_sr_class: MagicMock):
        """Test that long content is truncated."""
        mock_router = MagicMock()
        mock_router.return_value = MagicMock(name=None, similarity_score=None)
        mock_sr_class.return_value = mock_router

        encoder = MockEncoder()
        encoder.max_chars = 100  # Set low limit

        routes = [
            Route(name="test", pattern="test/pattern", utterances=["utterance"]),
        ]
        classifier = SemanticRouterClassifier(encoder=encoder, routes=routes)

        long_content = "x" * 500
        classifier.classify(long_content)

        # Router should be called with truncated content
        mock_router.assert_called_once()
        call_arg = mock_router.call_args[0][0]
        assert len(call_arg) == 100

    @patch("para_files.classifiers.semantic_router.SemanticRouter")
    def test_classify_stores_raw_score(self, mock_sr_class: MagicMock):
        """Test that raw similarity score is stored in result."""
        mock_router = MagicMock()
        mock_choice = MagicMock()
        mock_choice.name = "test"
        mock_choice.similarity_score = 0.923
        mock_router.return_value = mock_choice
        mock_sr_class.return_value = mock_router

        encoder = MockEncoder()
        routes = [
            Route(name="test", pattern="test/pattern", utterances=["utterance"]),
        ]
        classifier = SemanticRouterClassifier(encoder=encoder, routes=routes)

        result = classifier.classify("content")

        assert result is not None
        assert result.raw_score == 0.923


class TestSemanticRouterDebugLogging:
    """Tests for debug logging functionality."""

    @patch("para_files.classifiers.semantic_router.SemanticRouter")
    def test_log_debug_similarities_no_index(self, mock_sr_class: MagicMock):
        """Test debug logging when router has no index."""
        mock_router = MagicMock()
        mock_router.index = None
        mock_router.return_value = MagicMock(name=None, similarity_score=None)
        mock_sr_class.return_value = mock_router

        encoder = MockEncoder()
        routes = [
            Route(name="test", pattern="test/pattern", utterances=["utterance"]),
        ]
        classifier = SemanticRouterClassifier(encoder=encoder, routes=routes)

        # Should not raise
        classifier._log_debug_similarities("content", mock_router)

    @patch("para_files.classifiers.semantic_router.SemanticRouter")
    def test_log_debug_similarities_no_get_routes(self, mock_sr_class: MagicMock):
        """Test debug logging when index has no get_routes method."""
        mock_router = MagicMock()
        mock_router.index = MagicMock(spec=[])  # No get_routes method
        mock_router.return_value = MagicMock(name=None, similarity_score=None)
        mock_sr_class.return_value = mock_router

        encoder = MockEncoder()
        routes = [
            Route(name="test", pattern="test/pattern", utterances=["utterance"]),
        ]
        classifier = SemanticRouterClassifier(encoder=encoder, routes=routes)

        # Should not raise
        classifier._log_debug_similarities("content", mock_router)
