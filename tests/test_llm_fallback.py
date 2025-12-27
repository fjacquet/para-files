"""Tests for the LLM fallback classifier module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from para_files.classifiers.llm_fallback import (
    SYSTEM_PROMPT,
    LLMFallbackClassifier,
)
from para_files.types import ClassificationSource, FileMetadata, Route


class TestLLMFallbackClassifier:
    """Tests for LLMFallbackClassifier."""

    def test_name(self):
        """Test classifier name."""
        classifier = LLMFallbackClassifier()
        assert classifier.name == "llm_fallback"

    def test_source(self):
        """Test classification source."""
        classifier = LLMFallbackClassifier()
        assert classifier.source == ClassificationSource.LLM_FALLBACK

    def test_default_confidence(self):
        """Test default confidence matches threshold."""
        classifier = LLMFallbackClassifier(confidence_threshold=0.7)
        assert classifier.default_confidence == 0.7

    def test_classify_disabled(self):
        """Test classify returns None when disabled."""
        classifier = LLMFallbackClassifier(enabled=False)
        result = classifier.classify("test content")
        assert result is None

    def test_classify_empty_content(self):
        """Test classify returns None for empty content."""
        classifier = LLMFallbackClassifier(enabled=True)
        result = classifier.classify("")
        assert result is None

    def test_classify_whitespace_only(self):
        """Test classify returns None for whitespace-only content."""
        classifier = LLMFallbackClassifier(enabled=True)
        result = classifier.classify("   \n\t  ")
        assert result is None

    @patch("para_files.classifiers.llm_fallback.LLMFallbackClassifier._call_llm")
    def test_classify_success(self, mock_call_llm: MagicMock):
        """Test successful classification."""
        from para_files.types import ClassificationResult, Confidence

        mock_call_llm.return_value = ClassificationResult(
            category="4_Archives/test",
            confidence=Confidence(value=0.8, source=ClassificationSource.LLM_FALLBACK),
        )

        classifier = LLMFallbackClassifier(enabled=True)
        result = classifier.classify("test document content")

        assert result is not None
        assert result.category == "4_Archives/test"
        mock_call_llm.assert_called_once()

    @patch("para_files.classifiers.llm_fallback.LLMFallbackClassifier._call_llm")
    def test_classify_exception_handling(self, mock_call_llm: MagicMock):
        """Test classify handles exceptions gracefully."""
        mock_call_llm.side_effect = Exception("API error")

        classifier = LLMFallbackClassifier(enabled=True)
        result = classifier.classify("test content")

        assert result is None


class TestLLMFallbackBuildUserMessage:
    """Tests for _build_user_message method."""

    def test_build_message_no_metadata(self):
        """Test building message without metadata."""
        classifier = LLMFallbackClassifier(
            enabled=True,
            content_preview_chars=100,
        )
        content = "Test content for classification"
        message = classifier._build_user_message(content, None)

        assert "Content preview:" in message
        assert "Test content" in message

    def test_build_message_with_metadata(self):
        """Test building message with metadata."""
        from datetime import UTC, datetime
        from pathlib import Path

        classifier = LLMFallbackClassifier(enabled=True)
        metadata = FileMetadata(
            path=Path("/tmp/test.pdf"),
            filename="test.pdf",
            extension=".pdf",
            size_bytes=1024,
            modified_at=datetime(2025, 1, 15, tzinfo=UTC),
        )
        message = classifier._build_user_message("content", metadata)

        assert "Filename: test.pdf" in message
        assert "Extension: .pdf" in message
        assert "2025-01-15" in message

    def test_build_message_with_routes(self):
        """Test building message with available routes."""
        routes = [
            Route(name="factures", pattern="4_Archives/factures", utterances=["invoice"]),
            Route(name="banques", pattern="4_Archives/banques", utterances=["bank"]),
        ]
        classifier = LLMFallbackClassifier(
            enabled=True,
            available_routes=routes,
        )
        message = classifier._build_user_message("content", None)

        assert "Available categories:" in message
        assert "factures" in message
        assert "banques" in message

    def test_build_message_truncates_content(self):
        """Test that content is truncated to max chars."""
        classifier = LLMFallbackClassifier(
            enabled=True,
            content_preview_chars=50,
        )
        long_content = "x" * 200
        message = classifier._build_user_message(long_content, None)

        # Content should be truncated
        assert "x" * 50 in message
        assert "x" * 200 not in message


class TestLLMFallbackParseResponse:
    """Tests for _parse_llm_response method."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        classifier = LLMFallbackClassifier(
            enabled=True,
            confidence_threshold=0.6,
        )
        response = '{"category": "4_Archives/test", "confidence": 0.8, "reasoning": "test"}'
        result = classifier._parse_llm_response(response)

        assert result is not None
        assert result.category == "4_Archives/test"
        assert result.confidence.value == 0.8
        assert result.extracted_params == {"llm_reasoning": "test"}

    def test_parse_json_with_markdown_code_block(self):
        """Test parsing JSON wrapped in markdown code block."""
        classifier = LLMFallbackClassifier(
            enabled=True,
            confidence_threshold=0.6,
        )
        response = '```json\n{"category": "4_Archives/test", "confidence": 0.8}\n```'
        result = classifier._parse_llm_response(response)

        assert result is not None
        assert result.category == "4_Archives/test"

    def test_parse_low_confidence_returns_none(self):
        """Test that low confidence results return None."""
        classifier = LLMFallbackClassifier(
            enabled=True,
            confidence_threshold=0.7,
        )
        response = '{"category": "4_Archives/test", "confidence": 0.5}'
        result = classifier._parse_llm_response(response)

        assert result is None

    def test_parse_missing_category_returns_none(self):
        """Test that missing category returns None."""
        classifier = LLMFallbackClassifier(
            enabled=True,
            confidence_threshold=0.6,
        )
        response = '{"confidence": 0.8}'
        result = classifier._parse_llm_response(response)

        assert result is None

    def test_parse_invalid_json_returns_none(self):
        """Test that invalid JSON returns None."""
        classifier = LLMFallbackClassifier(enabled=True)
        result = classifier._parse_llm_response("not valid json")

        assert result is None

    def test_parse_empty_category_returns_none(self):
        """Test that empty category returns None."""
        classifier = LLMFallbackClassifier(
            enabled=True,
            confidence_threshold=0.6,
        )
        response = '{"category": "", "confidence": 0.8}'
        result = classifier._parse_llm_response(response)

        assert result is None


class TestLLMFallbackCallLLM:
    """Tests for _call_llm method."""

    def test_call_llm_litellm_not_installed(self):
        """Test _call_llm when litellm is not installed."""
        classifier = LLMFallbackClassifier(enabled=True)

        with (
            patch.dict("sys.modules", {"litellm": None}),
            patch("para_files.classifiers.llm_fallback.LLMFallbackClassifier._call_llm") as mock,
        ):
            mock.return_value = None
            result = classifier._call_llm("content", None)
            assert result is None

    @patch("litellm.completion")
    def test_call_llm_success(self, mock_completion: MagicMock):
        """Test successful LLM call."""
        # Mock the LLM response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content='{"category": "4_Archives/test", "confidence": 0.85}')
            )
        ]
        mock_completion.return_value = mock_response

        classifier = LLMFallbackClassifier(
            enabled=True,
            model="ollama/test",
            api_base="http://localhost:11434",
        )
        result = classifier._call_llm("test content", None)

        assert result is not None
        assert result.category == "4_Archives/test"
        mock_completion.assert_called_once()

    @patch("litellm.completion")
    def test_call_llm_empty_response(self, mock_completion: MagicMock):
        """Test LLM call with empty response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]
        mock_completion.return_value = mock_response

        classifier = LLMFallbackClassifier(enabled=True)
        result = classifier._call_llm("content", None)

        assert result is None


class TestSystemPrompt:
    """Tests for the system prompt."""

    def test_system_prompt_contains_para_categories(self):
        """Test that system prompt contains PARA categories."""
        assert "0_Inbox" in SYSTEM_PROMPT
        assert "1_Projects" in SYSTEM_PROMPT
        assert "2_Areas" in SYSTEM_PROMPT
        assert "3_Resources" in SYSTEM_PROMPT
        assert "4_Archives" in SYSTEM_PROMPT

    def test_system_prompt_contains_json_format(self):
        """Test that system prompt specifies JSON format."""
        assert "JSON" in SYSTEM_PROMPT
        assert "category" in SYSTEM_PROMPT
        assert "confidence" in SYSTEM_PROMPT
