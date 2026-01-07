"""Tests for MOBI metadata extraction."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from para_files.utils.mobi_metadata import (
    MIN_TITLE_LENGTH,
    MobiMetadata,
    _extract_title_from_mobi_metadata,
    _scan_mobi_pages_for_isbns,
    extract_mobi_metadata,
)


class TestExtractTitleFromMobiMetadata:
    """Tests for _extract_title_from_mobi_metadata function."""

    def test_extracts_title_field(self):
        """Test extracting title from metadata dict."""
        metadata = {"title": "The Pragmatic Programmer", "author": "Hunt and Thomas"}
        result = _extract_title_from_mobi_metadata(metadata)
        assert result == "The Pragmatic Programmer"

    def test_extracts_subject_fallback(self):
        """Test extracting title from Subject field as fallback."""
        metadata = {"Subject": "Clean Code"}
        result = _extract_title_from_mobi_metadata(metadata)
        assert result == "Clean Code"

    def test_prefers_title_over_subject(self):
        """Test that title is preferred over Subject."""
        metadata = {
            "title": "Python Cookbook",
            "Subject": "Clean Code",
        }
        result = _extract_title_from_mobi_metadata(metadata)
        assert result == "Python Cookbook"

    def test_rejects_too_short_title(self):
        """Test that titles shorter than MIN_TITLE_LENGTH are rejected."""
        metadata = {"title": "AB"}  # Shorter than MIN_TITLE_LENGTH
        result = _extract_title_from_mobi_metadata(metadata)
        assert result is None

    def test_strips_whitespace(self):
        """Test that whitespace is stripped from title."""
        metadata = {"title": "  The Pragmatic Programmer  "}
        result = _extract_title_from_mobi_metadata(metadata)
        assert result == "The Pragmatic Programmer"

    def test_returns_none_for_non_string_title(self):
        """Test returns None when title is not a string."""
        metadata = {"title": 123, "Subject": "Test Book"}
        result = _extract_title_from_mobi_metadata(metadata)
        assert result is None

    def test_returns_none_for_empty_metadata(self):
        """Test returns None when metadata is empty."""
        metadata: dict = {}
        result = _extract_title_from_mobi_metadata(metadata)
        assert result is None


class TestScanMobiPagesForIsbns:
    """Tests for _scan_mobi_pages_for_isbns function."""

    def test_scans_pages_for_isbns(self):
        """Test scanning pages for ISBNs."""
        # Create mock document
        mock_page = MagicMock()
        mock_page.get_text.return_value = "ISBN 9781593275846"

        mock_doc = MagicMock()
        mock_doc.page_count = 5
        mock_doc.__getitem__.return_value = mock_page

        result = _scan_mobi_pages_for_isbns(mock_doc, [])

        assert "9781593275846" in result

    def test_includes_filename_isbns(self):
        """Test that filename ISBNs are included in result."""
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Some text"
        mock_doc.__getitem__.return_value = mock_page

        filename_isbns = ["9781234567890"]
        result = _scan_mobi_pages_for_isbns(mock_doc, filename_isbns)

        assert "9781234567890" in result

    def test_deduplicates_isbns(self):
        """Test that duplicate ISBNs are not included twice."""
        mock_page = MagicMock()
        mock_page.get_text.return_value = "ISBN 9781593275846"

        mock_doc = MagicMock()
        mock_doc.page_count = 2
        mock_doc.__getitem__.return_value = mock_page

        filename_isbns = ["9781593275846"]  # Same ISBN in filename
        result = _scan_mobi_pages_for_isbns(mock_doc, filename_isbns)

        # Should only appear once
        assert result.count("9781593275846") == 1

    def test_scans_max_5_pages(self):
        """Test that only first 5 pages are scanned."""
        mock_doc = MagicMock()
        mock_doc.page_count = 100
        mock_page = MagicMock()
        mock_page.get_text.return_value = "No ISBN"
        mock_doc.__getitem__.return_value = mock_page

        _scan_mobi_pages_for_isbns(mock_doc, [])

        # Should be called at most 5 times (pages 0-4)
        assert mock_doc.__getitem__.call_count <= 5

    def test_handles_page_read_errors(self):
        """Test that page read errors are skipped gracefully."""
        mock_doc = MagicMock()
        mock_doc.page_count = 3

        # First page errors, second succeeds with ISBN, third errors
        page_results = [OSError("Can't read"), MagicMock(), OSError("Can't read")]
        pages = []
        for result in page_results:
            if isinstance(result, OSError):
                page = MagicMock()
                page.get_text.side_effect = result
            else:
                page = result
                page.get_text.return_value = "ISBN 9781593275846"
            pages.append(page)

        mock_doc.__getitem__.side_effect = pages

        result = _scan_mobi_pages_for_isbns(mock_doc, [])

        # Should find ISBN from successful page
        assert "9781593275846" in result


class TestExtractMobiMetadata:
    """Tests for extract_mobi_metadata function."""

    def test_extracts_title_and_isbns(self, tmp_path: Path):
        """Test extracting metadata from MOBI file."""
        mobi_file = tmp_path / "test.mobi"
        mobi_file.write_bytes(b"MOBI")

        mock_doc = MagicMock()
        mock_doc.metadata = {
            "title": "Python Programming Guide",
            "author": "John Doe",
        }
        mock_doc.page_count = 1
        mock_page = MagicMock()
        # Use a valid ISBN-13: 978-0-13-595705-9 (Python Programming by Guido)
        mock_page.get_text.return_value = "ISBN 9780135957059"
        mock_doc.__getitem__.return_value = mock_page

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc
        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            result = extract_mobi_metadata(mobi_file)

            assert result is not None
            assert result.title == "Python Programming Guide"
            assert result.author == "John Doe"
            assert "9780135957059" in result.isbns

    def test_returns_none_for_invalid_extension(self, tmp_path: Path):
        """Test returns None for non-MOBI files."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Not a MOBI file")

        result = extract_mobi_metadata(txt_file)
        assert result is None

    def test_returns_none_for_nonexistent_file(self):
        """Test returns None for nonexistent files."""
        result = extract_mobi_metadata(Path("/nonexistent/file.mobi"))
        assert result is None

    def test_returns_partial_metadata_on_extract_failure(self, tmp_path: Path):
        """Test returns partial metadata if ISBN found in filename but extraction fails."""
        mobi_file = tmp_path / "9781593275846_book.mobi"
        mobi_file.write_bytes(b"MOBI")

        mock_fitz = MagicMock()
        mock_fitz.open.side_effect = RuntimeError("Cannot open MOBI")
        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            result = extract_mobi_metadata(mobi_file)

            assert result is not None
            assert result.isbn == "9781593275846"
            assert "9781593275846" in result.isbns
            assert result.title is None

    def test_returns_none_on_extract_failure_without_filename_isbn(self, tmp_path: Path):
        """Test returns None if extraction fails and no ISBN in filename."""
        mobi_file = tmp_path / "book.mobi"
        mobi_file.write_bytes(b"MOBI")

        mock_fitz = MagicMock()
        mock_fitz.open.side_effect = RuntimeError("Cannot open MOBI")
        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            result = extract_mobi_metadata(mobi_file)
            assert result is None

    def test_mobi_metadata_dataclass(self):
        """Test MobiMetadata dataclass creation."""
        meta = MobiMetadata(
            title="Test Book",
            author="Test Author",
            isbn="9781234567890",
            isbns=["9781234567890", "9789876543210"],
            file_size_mb=5.0,
        )

        assert meta.title == "Test Book"
        assert meta.author == "Test Author"
        assert meta.isbn == "9781234567890"
        assert len(meta.isbns) == 2
        assert meta.file_size_mb == 5.0

    def test_mobi_metadata_defaults(self):
        """Test MobiMetadata with default values."""
        meta = MobiMetadata()

        assert meta.title is None
        assert meta.author is None
        assert meta.isbn is None
        assert meta.isbns == []
        assert meta.file_size_mb == 0.0

    def test_extracts_filename_isbns(self, tmp_path: Path):
        """Test that ISBNs are extracted from filename."""
        mobi_file = tmp_path / "9780596007973_Python_Cookbook.mobi"
        mobi_file.write_bytes(b"MOBI")

        mock_doc = MagicMock()
        mock_doc.metadata = {"title": "Python Cookbook"}
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.get_text.return_value = "No ISBN here"
        mock_doc.__getitem__.return_value = mock_page

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc
        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            result = extract_mobi_metadata(mobi_file)

            assert result is not None
            assert "9780596007973" in result.isbns
