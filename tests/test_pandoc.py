"""Tests for the pandoc extractor module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from para_files.utils.pandoc import (
    PANDOC_EXTENSIONS,
    PANDOC_FORMATS,
    PandocResult,
    extract_metadata,
    extract_text,
    get_pandoc_format,
    is_pandoc_available,
)


class TestPandocResultModel:
    """Tests for PandocResult Pydantic model."""

    def test_pandoc_result_basic(self):
        """Test PandocResult with basic values."""
        result = PandocResult(
            text="Hello world",
            format="markdown",
            char_count=11,
            word_count=2,
        )
        assert result.text == "Hello world"
        assert result.format == "markdown"
        assert result.char_count == 11
        assert result.word_count == 2

    def test_pandoc_result_preview_short_text(self):
        """Test preview with short text returns full text."""
        result = PandocResult(
            text="Short text",
            format="markdown",
            char_count=10,
            word_count=2,
        )
        assert result.preview == "Short text"

    def test_pandoc_result_preview_long_text(self):
        """Test preview with long text is truncated."""
        long_text = "x" * 600
        result = PandocResult(
            text=long_text,
            format="markdown",
            char_count=600,
            word_count=1,
        )
        assert len(result.preview) == 503  # 500 + "..."
        assert result.preview.endswith("...")


class TestPandocFormats:
    """Tests for pandoc format constants."""

    def test_common_formats_supported(self):
        """Test common document formats are supported."""
        assert ".docx" in PANDOC_EXTENSIONS
        assert ".odt" in PANDOC_EXTENSIONS
        assert ".epub" in PANDOC_EXTENSIONS
        assert ".md" in PANDOC_EXTENSIONS
        assert ".html" in PANDOC_EXTENSIONS
        assert ".rst" in PANDOC_EXTENSIONS

    def test_format_mapping_correct(self):
        """Test format mapping returns correct pandoc format names."""
        assert PANDOC_FORMATS[".docx"] == "docx"
        assert PANDOC_FORMATS[".md"] == "markdown"
        assert PANDOC_FORMATS[".html"] == "html"
        assert PANDOC_FORMATS[".rst"] == "rst"
        assert PANDOC_FORMATS[".tex"] == "latex"


class TestGetPandocFormat:
    """Tests for get_pandoc_format function."""

    def test_supported_format(self):
        """Test getting format for supported file."""
        assert get_pandoc_format(Path("doc.docx")) == "docx"
        assert get_pandoc_format(Path("readme.md")) == "markdown"
        assert get_pandoc_format(Path("page.html")) == "html"

    def test_unsupported_format(self):
        """Test unsupported format returns None."""
        assert get_pandoc_format(Path("image.jpg")) is None
        assert get_pandoc_format(Path("data.csv")) is None
        assert get_pandoc_format(Path("archive.zip")) is None

    def test_case_insensitive(self):
        """Test format lookup is case insensitive."""
        assert get_pandoc_format(Path("DOC.DOCX")) == "docx"
        assert get_pandoc_format(Path("README.MD")) == "markdown"


class TestIsPandocAvailable:
    """Tests for pandoc availability check."""

    def test_pandoc_available(self):
        """Test when pandoc is installed."""
        with patch("shutil.which", return_value="/usr/local/bin/pandoc"):
            assert is_pandoc_available() is True

    def test_pandoc_not_available(self):
        """Test when pandoc is not installed."""
        with patch("shutil.which", return_value=None):
            assert is_pandoc_available() is False


class TestExtractText:
    """Tests for the main extract_text function."""

    def test_pandoc_not_available(self, tmp_path: Path):
        """Test when pandoc is not installed."""
        test_file = tmp_path / "test.docx"
        test_file.touch()
        with patch("para_files.utils.pandoc.is_pandoc_available", return_value=False):
            result = extract_text(test_file)
            assert result is None

    def test_unsupported_extension(self, tmp_path: Path):
        """Test unsupported file extension."""
        test_file = tmp_path / "test.jpg"
        test_file.touch()
        result = extract_text(test_file)
        assert result is None

    def test_file_not_exists(self):
        """Test non-existent file."""
        result = extract_text(Path("/nonexistent/file.docx"))
        assert result is None

    @patch("para_files.utils.pandoc._run_pandoc_to_plain")
    def test_extract_text_success(self, mock_run: MagicMock, tmp_path: Path):
        """Test successful text extraction."""
        test_file = tmp_path / "document.docx"
        test_file.touch()

        mock_run.return_value = "This is the document content.\nWith multiple lines."

        result = extract_text(test_file)

        assert result is not None
        assert "This is the document content" in result.text
        assert result.format == "docx"
        assert result.char_count > 0
        assert result.word_count > 0

    @patch("para_files.utils.pandoc._run_pandoc_to_plain")
    def test_extract_text_truncates(self, mock_run: MagicMock, tmp_path: Path):
        """Test text extraction with max_chars limit."""
        test_file = tmp_path / "document.md"
        test_file.touch()

        # Return a long text
        mock_run.return_value = "word " * 1000  # 5000 chars

        result = extract_text(test_file, max_chars=100)

        assert result is not None
        assert len(result.text) <= 100

    @patch("para_files.utils.pandoc._run_pandoc_to_plain")
    def test_extract_text_empty_output(self, mock_run: MagicMock, tmp_path: Path):
        """Test when pandoc returns empty output."""
        test_file = tmp_path / "empty.docx"
        test_file.touch()

        mock_run.return_value = None
        result = extract_text(test_file)
        assert result is None


class TestExtractMetadata:
    """Tests for metadata extraction function."""

    def test_pandoc_not_available(self, tmp_path: Path):
        """Test when pandoc is not installed."""
        test_file = tmp_path / "test.md"
        test_file.touch()
        with patch("para_files.utils.pandoc.is_pandoc_available", return_value=False):
            result = extract_metadata(test_file)
            assert result is None

    def test_unsupported_format(self, tmp_path: Path):
        """Test unsupported file format."""
        test_file = tmp_path / "test.jpg"
        test_file.touch()
        result = extract_metadata(test_file)
        assert result is None

    def test_file_not_exists(self):
        """Test non-existent file."""
        result = extract_metadata(Path("/nonexistent/file.md"))
        assert result is None

    @patch("subprocess.run")
    def test_extract_metadata_success(self, mock_run: MagicMock, tmp_path: Path):
        """Test successful metadata extraction."""
        # Use .rst (in ALLOWED_EXTENSIONS) rather than .md (excluded, read as text directly)
        test_file = tmp_path / "document.rst"
        test_file.write_text("Test document content.")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="title: My Document\nauthor: John Doe\ndate: 2025-01-15",
        )

        with patch("para_files.utils.pandoc.is_pandoc_available", return_value=True):
            result = extract_metadata(test_file)

        assert result is not None
        assert result["title"] == "My Document"
        assert result["author"] == "John Doe"
        assert result["date"] == "2025-01-15"

    @patch("subprocess.run")
    def test_extract_metadata_no_metadata(self, mock_run: MagicMock, tmp_path: Path):
        """Test when document has no metadata."""
        test_file = tmp_path / "plain.rst"
        test_file.write_text("Just content.")

        mock_run.return_value = MagicMock(returncode=0, stdout="")

        with patch("para_files.utils.pandoc.is_pandoc_available", return_value=True):
            result = extract_metadata(test_file)

        assert result is None


class TestExtractTextIntegration:
    """Integration tests that require pandoc to be installed."""

    @pytest.fixture
    def check_pandoc(self):
        """Skip test if pandoc is not installed."""
        if not is_pandoc_available():
            pytest.skip("pandoc not installed")

    @pytest.mark.slow
    def test_extract_from_rst(self, check_pandoc, tmp_path: Path):
        """Test extracting text from a RST file.

        Note: .md files are excluded from ALLOWED_EXTENSIONS (read as text directly),
        so we use .rst which is in the subprocess allowlist.
        """
        rst_file = tmp_path / "test.rst"
        rst_file.write_text("Hello World\n===========\n\nThis is a test document.\n\n- Item 1\n- Item 2")

        result = extract_text(rst_file)

        assert result is not None
        assert "Hello World" in result.text
        assert "test document" in result.text
        assert result.format == "rst"
        assert result.word_count > 0

    @pytest.mark.slow
    def test_extract_from_html(self, check_pandoc, tmp_path: Path):
        """Test extracting text from an HTML file."""
        html_file = tmp_path / "test.html"
        html_file.write_text(
            "<html><head><title>Test</title></head><body><h1>Hello</h1><p>World</p></body></html>"
        )

        result = extract_text(html_file)

        assert result is not None
        assert "Hello" in result.text
        assert "World" in result.text
        assert result.format == "html"

    @pytest.mark.slow
    def test_extract_from_rst(self, check_pandoc, tmp_path: Path):
        """Test extracting text from reStructuredText file."""
        rst_file = tmp_path / "test.rst"
        rst_file.write_text("Title\n=====\n\nThis is a paragraph.\n\n* Bullet point")

        result = extract_text(rst_file)

        assert result is not None
        assert "Title" in result.text
        assert "paragraph" in result.text
        assert result.format == "rst"
