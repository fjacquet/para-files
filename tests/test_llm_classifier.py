"""Tests for LLM classifier response parsing and validation.

Covers TEST-04 edge cases:
- JSON-first parsing strategy
- String/percentage/integer confidence coercion
- URL-decoded category paths
- Category allowlist validation
- Pipeline short-circuit after first match (LLM-03)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from para_files.classifiers.llm_classifier import LLMClassifier
from para_files.types import ClassificationResult, ClassificationSource, Confidence


VALID_CATEGORIES = [
    "3_Resources/documentation/Python",
    "3_Resources/documentation/C++",
    "4_Archives/5y_divers/2024",
]


@pytest.fixture
def classifier() -> LLMClassifier:
    """LLMClassifier instance with known valid categories for testing."""
    return LLMClassifier(
        enabled=True,
        model="test",
        confidence_threshold=0.6,
        valid_categories=VALID_CATEGORIES,
    )


# ---------------------------------------------------------------------------
# _parse_response: basic valid JSON
# ---------------------------------------------------------------------------


def test_parse_response_valid_json(classifier: LLMClassifier) -> None:
    """Valid JSON with float confidence returns ClassificationResult."""
    response = '{"category":"3_Resources/documentation/Python","confidence":0.8,"reasoning":"Python docs"}'
    result = classifier._parse_response(response)
    assert result is not None
    assert result.category == "3_Resources/documentation/Python"
    assert result.confidence.value == pytest.approx(0.8)


def test_parse_response_string_confidence(classifier: LLMClassifier) -> None:
    """String confidence '0.85' is coerced to float 0.85."""
    response = '{"category":"3_Resources/documentation/Python","confidence":"0.85"}'
    result = classifier._parse_response(response)
    assert result is not None
    assert result.confidence.value == pytest.approx(0.85)


def test_parse_response_percentage_confidence(classifier: LLMClassifier) -> None:
    """Percentage confidence '80%' is coerced to float 0.80."""
    response = '{"category":"3_Resources/documentation/Python","confidence":"80%"}'
    result = classifier._parse_response(response)
    assert result is not None
    assert result.confidence.value == pytest.approx(0.80)


def test_parse_response_integer_confidence(classifier: LLMClassifier) -> None:
    """Integer-as-string confidence '80' is coerced to float 0.80."""
    response = '{"category":"3_Resources/documentation/Python","confidence":"80"}'
    result = classifier._parse_response(response)
    assert result is not None
    assert result.confidence.value == pytest.approx(0.80)


def test_parse_response_trailing_spaces(classifier: LLMClassifier) -> None:
    """Category with leading/trailing spaces is stripped and accepted."""
    response = '{"category":"  3_Resources/documentation/Python  ","confidence": 0.9 }'
    result = classifier._parse_response(response)
    assert result is not None
    assert result.category == "3_Resources/documentation/Python"
    assert result.confidence.value == pytest.approx(0.9)


def test_parse_response_nested_json(classifier: LLMClassifier) -> None:
    """JSON embedded in extra text before/after is extracted correctly."""
    response = 'Here is my analysis. {"category":"3_Resources/documentation/Python","confidence":0.75,"reasoning":"matches"} End.'
    result = classifier._parse_response(response)
    assert result is not None
    assert result.category == "3_Resources/documentation/Python"


def test_parse_response_markdown_wrapped(classifier: LLMClassifier) -> None:
    """JSON wrapped in triple backtick markdown code block is extracted."""
    response = '```json\n{"category":"3_Resources/documentation/Python","confidence":0.8,"reasoning":"good match"}\n```'
    result = classifier._parse_response(response)
    assert result is not None
    assert result.category == "3_Resources/documentation/Python"


def test_parse_response_incomplete_json(classifier: LLMClassifier) -> None:
    """Incomplete JSON returns None without raising an exception."""
    response = '{"category":"3_Resources'
    result = classifier._parse_response(response)
    assert result is None


def test_parse_response_empty_string(classifier: LLMClassifier) -> None:
    """Empty string returns None."""
    result = classifier._parse_response("")
    assert result is None


def test_parse_response_chatty_response(classifier: LLMClassifier) -> None:
    """LLM chatty preamble before JSON is handled correctly."""
    response = 'Sure! Here is the classification:\n{"category":"3_Resources/documentation/Python","confidence":0.82,"reasoning":"Python"}'
    result = classifier._parse_response(response)
    assert result is not None
    assert result.category == "3_Resources/documentation/Python"


# ---------------------------------------------------------------------------
# _sanitize_category: URL-encoding and allowlist
# ---------------------------------------------------------------------------


def test_sanitize_category_url_encoded(classifier: LLMClassifier) -> None:
    """URL-encoded path '3_Resources/documentation/C%2B%2B' decodes to 'C++'."""
    result = classifier._sanitize_category("3_Resources/documentation/C%2B%2B")
    assert result == "3_Resources/documentation/C++"


def test_sanitize_category_allowlist_match(classifier: LLMClassifier) -> None:
    """Category present in allowlist is accepted."""
    result = classifier._sanitize_category("3_Resources/documentation/Python")
    assert result == "3_Resources/documentation/Python"


def test_sanitize_category_allowlist(classifier: LLMClassifier) -> None:
    """Category NOT in allowlist is rejected when allowlist is provided."""
    # "3_Resources/documentation/Java" is not in our VALID_CATEGORIES fixture
    result = classifier._sanitize_category("3_Resources/documentation/Java")
    assert result is None


def test_sanitize_category_no_allowlist_accepts_valid_para(classifier: LLMClassifier) -> None:
    """Without allowlist, any valid PARA prefix is accepted."""
    no_allowlist = LLMClassifier(
        enabled=True,
        model="test",
        confidence_threshold=0.6,
        valid_categories=None,
    )
    result = no_allowlist._sanitize_category("3_Resources/documentation/Java")
    assert result == "3_Resources/documentation/Java"


def test_sanitize_category_rejects_absolute_path(classifier: LLMClassifier) -> None:
    """Absolute paths are rejected."""
    result = classifier._sanitize_category("/etc/passwd")
    assert result is None


def test_sanitize_category_rejects_windows_path(classifier: LLMClassifier) -> None:
    """Windows-style paths are rejected."""
    result = classifier._sanitize_category("C:\\Users\\foo")
    assert result is None


# ---------------------------------------------------------------------------
# Pipeline short-circuit (LLM-03): first match wins
# ---------------------------------------------------------------------------


def test_pipeline_short_circuit() -> None:
    """Pipeline stops after first classifier match; later classifiers are never called."""
    import threading

    from para_files.pipeline import ClassificationPipeline

    # Create mock classifiers
    first_classifier = MagicMock()
    second_classifier = MagicMock()
    third_classifier = MagicMock()

    # First classifier returns a match
    mock_result = ClassificationResult(
        category="3_Resources/documentation/Python",
        confidence=Confidence(value=0.9, source=ClassificationSource.RULES_ENGINE),
    )
    first_classifier.classify.return_value = mock_result
    first_classifier.name = "first"
    first_classifier.default_confidence = 0.6
    first_classifier.source = ClassificationSource.RULES_ENGINE

    # Others should NOT be called
    second_classifier.name = "second"
    second_classifier.default_confidence = 0.6
    second_classifier.source = ClassificationSource.DEFAULT
    second_classifier.classify.return_value = None
    third_classifier.name = "third"
    third_classifier.default_confidence = 0.6
    third_classifier.source = ClassificationSource.DEFAULT
    third_classifier.classify.return_value = None

    # Build a pipeline with our mocks injected directly, bypassing __init__
    pipeline = ClassificationPipeline.__new__(ClassificationPipeline)
    pipeline._classifiers = [first_classifier, second_classifier, third_classifier]
    pipeline._lock = threading.Lock()
    pipeline._initialized = True  # skip lazy init

    # Patch _ensure_initialized to be a no-op
    with patch.object(ClassificationPipeline, "_ensure_initialized"):
        pipeline.classify("some content")

    # Only the first classifier should have been called
    first_classifier.classify.assert_called_once()
    second_classifier.classify.assert_not_called()
    third_classifier.classify.assert_not_called()
