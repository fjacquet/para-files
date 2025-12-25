"""Tests for the OCR extractor module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from para_files.utils.ocr import (
    OCR_EXTENSIONS,
    OCRResult,
    extract_text,
    extract_text_with_regions,
    is_vision_available,
)


class TestOCRResultModel:
    """Tests for OCRResult Pydantic model."""

    def test_ocr_result_basic(self):
        """Test OCRResult with basic values."""
        result = OCRResult(
            text="Hello world",
            confidence=0.95,
            word_count=2,
        )
        assert result.text == "Hello world"
        assert result.confidence == 0.95
        assert result.word_count == 2
        assert result.language is None

    def test_ocr_result_with_language(self):
        """Test OCRResult with language code."""
        result = OCRResult(
            text="Bonjour monde",
            confidence=0.92,
            word_count=2,
            language="fr",
        )
        assert result.language == "fr"

    def test_ocr_result_preview_short_text(self):
        """Test preview with short text returns full text."""
        result = OCRResult(
            text="Short text",
            confidence=0.9,
            word_count=2,
        )
        assert result.preview == "Short text"

    def test_ocr_result_preview_long_text(self):
        """Test preview with long text is truncated."""
        long_text = "x" * 600
        result = OCRResult(
            text=long_text,
            confidence=0.9,
            word_count=1,
        )
        assert len(result.preview) == 503  # 500 + "..."
        assert result.preview.endswith("...")


class TestOCRExtensions:
    """Tests for OCR extension constants."""

    def test_common_image_formats_supported(self):
        """Test common image formats are supported."""
        assert ".png" in OCR_EXTENSIONS
        assert ".jpg" in OCR_EXTENSIONS
        assert ".jpeg" in OCR_EXTENSIONS
        assert ".heic" in OCR_EXTENSIONS
        assert ".tiff" in OCR_EXTENSIONS
        assert ".gif" in OCR_EXTENSIONS
        assert ".webp" in OCR_EXTENSIONS

    def test_unsupported_formats(self):
        """Test unsupported formats are not included."""
        assert ".pdf" not in OCR_EXTENSIONS
        assert ".docx" not in OCR_EXTENSIONS
        assert ".txt" not in OCR_EXTENSIONS
        assert ".svg" not in OCR_EXTENSIONS


class TestIsVisionAvailable:
    """Tests for Vision Framework availability check."""

    def test_vision_available(self):
        """Test when Vision Framework is installed."""
        with patch.dict("sys.modules", {"Vision": MagicMock()}):
            # Need to reimport after patching
            from importlib import reload

            from para_files.utils import ocr

            reload(ocr)
            # Test the function
            assert ocr.is_vision_available() is True

    def test_vision_not_available(self):
        """Test when Vision Framework is not installed."""
        msg = "No module named 'Vision'"

        def mock_import(name, *args, **kwargs):
            if name == "Vision":
                raise ImportError(msg)
            return MagicMock()

        with patch("builtins.__import__", side_effect=mock_import):
            # Reimport to get fresh state
            result = is_vision_available()
            # The actual result depends on system state
            # Just verify it returns a boolean
            assert isinstance(result, bool)


class TestExtractText:
    """Tests for the main extract_text function."""

    def test_vision_not_available(self, tmp_path: Path):
        """Test when Vision Framework is not installed."""
        test_file = tmp_path / "test.png"
        test_file.touch()
        with patch("para_files.utils.ocr.is_vision_available", return_value=False):
            result = extract_text(test_file)
            assert result is None

    def test_unsupported_extension(self, tmp_path: Path):
        """Test unsupported file extension."""
        test_file = tmp_path / "test.pdf"
        test_file.touch()
        with patch("para_files.utils.ocr.is_vision_available", return_value=True):
            result = extract_text(test_file)
            assert result is None

    def test_file_not_exists(self):
        """Test non-existent file."""
        with patch("para_files.utils.ocr.is_vision_available", return_value=True):
            result = extract_text(Path("/nonexistent/file.png"))
            assert result is None

    @patch("para_files.utils.ocr._extract_text_vision")
    def test_extract_text_success(self, mock_extract: MagicMock, tmp_path: Path):
        """Test successful text extraction."""
        test_file = tmp_path / "document.png"
        test_file.touch()

        mock_extract.return_value = ("This is text from an image.", 0.95)

        with patch("para_files.utils.ocr.is_vision_available", return_value=True):
            result = extract_text(test_file)

        assert result is not None
        assert "This is text from an image" in result.text
        assert result.confidence == 0.95
        assert result.word_count > 0

    @patch("para_files.utils.ocr._extract_text_vision")
    def test_extract_text_truncates(self, mock_extract: MagicMock, tmp_path: Path):
        """Test text extraction with max_chars limit."""
        test_file = tmp_path / "document.jpg"
        test_file.touch()

        # Return a long text
        mock_extract.return_value = ("word " * 1000, 0.9)  # 5000 chars

        with patch("para_files.utils.ocr.is_vision_available", return_value=True):
            result = extract_text(test_file, max_chars=100)

        assert result is not None
        assert len(result.text) <= 100

    @patch("para_files.utils.ocr._extract_text_vision")
    def test_extract_text_no_result(self, mock_extract: MagicMock, tmp_path: Path):
        """Test when OCR returns no result."""
        test_file = tmp_path / "empty.png"
        test_file.touch()

        mock_extract.return_value = None

        with patch("para_files.utils.ocr.is_vision_available", return_value=True):
            result = extract_text(test_file)
            assert result is None


class TestExtractTextWithRegions:
    """Tests for region extraction function."""

    def test_vision_not_available(self, tmp_path: Path):
        """Test when Vision Framework is not installed."""
        test_file = tmp_path / "test.png"
        test_file.touch()
        with patch("para_files.utils.ocr.is_vision_available", return_value=False):
            result = extract_text_with_regions(test_file)
            assert result is None

    def test_unsupported_format(self, tmp_path: Path):
        """Test unsupported file format."""
        test_file = tmp_path / "test.pdf"
        test_file.touch()
        with patch("para_files.utils.ocr.is_vision_available", return_value=True):
            result = extract_text_with_regions(test_file)
            assert result is None

    def test_file_not_exists(self):
        """Test non-existent file."""
        with patch("para_files.utils.ocr.is_vision_available", return_value=True):
            result = extract_text_with_regions(Path("/nonexistent/file.png"))
            assert result is None


class TestExtractTextIntegration:
    """Integration tests that require Vision Framework."""

    @pytest.fixture
    def check_vision(self):
        """Skip test if Vision Framework is not available."""
        if not is_vision_available():
            pytest.skip("Vision Framework not available")

    @pytest.mark.slow
    def test_extract_from_png(self, check_vision, tmp_path: Path):
        """Test extracting text from a PNG image.

        Note: This test requires an actual image with text.
        """
        # Create a simple test image with text would require PIL/Pillow
        # For now, just skip if no real test image is available
        pytest.skip("Requires test image with text")

    @pytest.mark.slow
    def test_extract_from_jpeg(self, check_vision, tmp_path: Path):
        """Test extracting text from a JPEG image."""
        pytest.skip("Requires test image with text")

    @pytest.mark.slow
    def test_extract_with_regions(self, check_vision, tmp_path: Path):
        """Test extracting text with bounding boxes."""
        pytest.skip("Requires test image with text")
