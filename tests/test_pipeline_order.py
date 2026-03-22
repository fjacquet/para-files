"""Tests for pipeline classifier ordering and failure isolation (TEST-01)."""
from __future__ import annotations

import threading
from unittest.mock import MagicMock

from para_files.pipeline import ClassificationPipeline
from para_files.types import ClassificationResult, ClassificationSource, Confidence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(category: str) -> ClassificationResult:
    """Create a minimal ClassificationResult for testing."""
    return ClassificationResult(
        category=category,
        confidence=Confidence(value=0.9, source=ClassificationSource.RULES_ENGINE),
    )


def _make_classifier(name: str, result: ClassificationResult | None) -> MagicMock:
    """Create a mock classifier that returns *result* from .classify()."""
    m = MagicMock()
    m.name = name
    m.default_confidence = 0.6
    m.source = ClassificationSource.DEFAULT
    m.classify.return_value = result
    return m


def _build_pipeline(classifiers: list) -> ClassificationPipeline:
    """Inject classifiers into a pipeline, bypassing __init__."""
    pipeline = ClassificationPipeline.__new__(ClassificationPipeline)
    pipeline._classifiers = classifiers
    pipeline._init_lock = threading.Lock()
    pipeline._initialized = True
    pipeline._circuit_breaker = None
    return pipeline


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_classifier_order_respected() -> None:
    """Classifiers run in registration order (A then B then C)."""
    call_order: list[str] = []

    def side_effect_a(_content: str, _metadata: object = None) -> ClassificationResult | None:
        call_order.append("A")
        return None

    def side_effect_b(_content: str, _metadata: object = None) -> ClassificationResult | None:
        call_order.append("B")
        return None

    def side_effect_c(_content: str, _metadata: object = None) -> ClassificationResult | None:
        call_order.append("C")
        return _make_result("3_Resources/test")

    classifier_a = _make_classifier("A", None)
    classifier_a.classify.side_effect = side_effect_a
    classifier_b = _make_classifier("B", None)
    classifier_b.classify.side_effect = side_effect_b
    classifier_c = _make_classifier("C", None)
    classifier_c.classify.side_effect = side_effect_c

    pipeline = _build_pipeline([classifier_a, classifier_b, classifier_c])
    result = pipeline.classify("some content")

    # All three called in order
    assert call_order == ["A", "B", "C"]
    assert result.category == "3_Resources/test"


def test_first_match_wins_stops_pipeline() -> None:
    """When the first classifier matches, later classifiers are never called."""
    classifier_a = _make_classifier("A", _make_result("1_Projects/match"))
    classifier_b = _make_classifier("B", _make_result("2_Areas/would-never"))
    classifier_c = _make_classifier("C", _make_result("3_Resources/would-never"))

    pipeline = _build_pipeline([classifier_a, classifier_b, classifier_c])
    result = pipeline.classify("some content")

    classifier_a.classify.assert_called_once()
    assert classifier_b.classify.call_count == 0
    assert classifier_c.classify.call_count == 0
    assert result.category == "1_Projects/match"


def test_disabled_classifier_skipped() -> None:
    """A classifier that returns None (simulating disabled) is skipped; pipeline continues."""
    # Mock disabled behavior: classify() returns None (pipeline doesn't check enabled flag)
    disabled = _make_classifier("disabled", None)  # returns None → pipeline continues
    enabled = _make_classifier("enabled", _make_result("3_Resources/found"))

    pipeline = _build_pipeline([disabled, enabled])
    result = pipeline.classify("some content")

    # Pipeline calls the disabled classifier (it just returns None)
    disabled.classify.assert_called_once()
    # Pipeline continues and calls the enabled classifier
    enabled.classify.assert_called_once()
    assert result.category == "3_Resources/found"


def test_single_exception_does_not_abort_pipeline() -> None:
    """A ValueError from one classifier does not prevent the next classifier from running."""
    crashing = _make_classifier("crashing", None)
    crashing.classify.side_effect = ValueError("boom")

    good = _make_classifier("good", _make_result("3_Resources/recovered"))

    pipeline = _build_pipeline([crashing, good])

    # Must NOT raise — exception is caught internally
    result = pipeline.classify("some content")

    crashing.classify.assert_called_once()
    good.classify.assert_called_once()
    assert result.category == "3_Resources/recovered"
