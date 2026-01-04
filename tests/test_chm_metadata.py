"""Tests for CHM metadata extraction."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from para_files.utils.chm_metadata import (
    MIN_TITLE_LENGTH,
    ChmMetadata,
    _extract_title_from_html,
    _find_7z_binary,
    extract_chm_metadata,
)


class TestFind7zBinary:
    """Tests for _find_7z_binary function."""

    def test_finds_7z(self):
        """Test finding 7z binary."""
        with patch("shutil.which", return_value="/usr/bin/7z"):
            result = _find_7z_binary()
            assert result == "/usr/bin/7z"

    def test_finds_7zz(self):
        """Test finding 7zz binary."""
        with patch("shutil.which", side_effect=[None, "/usr/bin/7zz", None]):
            result = _find_7z_binary()
            assert result == "/usr/bin/7zz"

    def test_finds_7za(self):
        """Test finding 7za binary."""
        with patch("shutil.which", side_effect=[None, None, "/usr/bin/7za"]):
            result = _find_7z_binary()
            assert result == "/usr/bin/7za"

    def test_returns_none_when_not_found(self):
        """Test returns None when no 7z binary found."""
        with patch("shutil.which", return_value=None):
            result = _find_7z_binary()
            assert result is None


class TestExtractTitleFromHtml:
    """Tests for _extract_title_from_html function."""

    def test_extracts_title_tag(self):
        """Test extracting title from <title> tag."""
        html = "<html><head><title>Python Programming Guide</title></head></html>"
        result = _extract_title_from_html(html)
        assert result == "Python Programming Guide"

    def test_extracts_h1_tag(self):
        """Test extracting title from <h1> tag when no title tag."""
        html = "<html><body><h1>Learn Python Today</h1></body></html>"
        result = _extract_title_from_html(html)
        assert result == "Learn Python Today"

    def test_prefers_title_over_h1(self):
        """Test that <title> is preferred over <h1>."""
        html = "<html><head><title>Real Title</title></head><body><h1>Heading</h1></body></html>"
        result = _extract_title_from_html(html)
        assert result == "Real Title"

    def test_ignores_short_title(self):
        """Test that short titles are ignored."""
        html = f"<html><head><title>{'A' * MIN_TITLE_LENGTH}</title></head></html>"
        result = _extract_title_from_html(html)
        assert result is None

    def test_returns_none_for_empty_html(self):
        """Test returns None for empty HTML."""
        result = _extract_title_from_html("")
        assert result is None

    def test_handles_title_with_attributes(self):
        """Test handles title tag with attributes."""
        html = '<title lang="en">Programming Book</title>'
        result = _extract_title_from_html(html)
        assert result == "Programming Book"


class TestExtractChmMetadata:
    """Tests for extract_chm_metadata function."""

    def test_returns_none_for_nonexistent_file(self, tmp_path: Path):
        """Test returns None for nonexistent file."""
        result = extract_chm_metadata(tmp_path / "nonexistent.chm")
        assert result is None

    def test_returns_none_for_non_chm_file(self, tmp_path: Path):
        """Test returns None for non-CHM file."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")
        result = extract_chm_metadata(pdf_file)
        assert result is None

    def test_extracts_isbn_from_filename(self, tmp_path: Path):
        """Test extracts ISBN from filename when extraction fails."""
        # Use valid ISBN-13 (passes checksum validation)
        chm_file = tmp_path / "9781234567897_Book.chm"
        chm_file.write_bytes(b"ITSF")  # CHM magic bytes

        with patch(
            "para_files.utils.chm_metadata._extract_chm_to_temp",
            return_value=False,
        ):
            result = extract_chm_metadata(chm_file)
            assert result is not None
            assert result.isbn == "9781234567897"
            assert "9781234567897" in result.isbns

    def test_returns_none_when_no_7z_and_no_filename_isbn(self, tmp_path: Path):
        """Test returns None when extraction fails and no ISBN in filename."""
        chm_file = tmp_path / "book.chm"
        chm_file.write_bytes(b"ITSF")

        with patch(
            "para_files.utils.chm_metadata._extract_chm_to_temp",
            return_value=False,
        ):
            result = extract_chm_metadata(chm_file)
            assert result is None

    def test_successful_extraction(self, tmp_path: Path):
        """Test successful CHM metadata extraction with mocked internals."""
        chm_file = tmp_path / "book.chm"
        chm_file.write_bytes(b"ITSF")

        # Mock the internal functions that extract data
        with (
            patch(
                "para_files.utils.chm_metadata._extract_chm_to_temp",
                return_value=True,
            ),
            patch(
                "para_files.utils.chm_metadata._scan_html_files_for_isbns",
                return_value=["9780123456789"],
            ),
            patch(
                "para_files.utils.chm_metadata._extract_title_from_files",
                return_value="Test Book",
            ),
        ):
            result = extract_chm_metadata(chm_file)
            assert result is not None
            assert result.title == "Test Book"
            assert "9780123456789" in result.isbns


class TestChmMetadataDataclass:
    """Tests for ChmMetadata dataclass."""

    def test_default_values(self):
        """Test default values."""
        meta = ChmMetadata()
        assert meta.title is None
        assert meta.isbn is None
        assert meta.isbns == []
        assert meta.file_size_mb == 0.0

    def test_with_values(self):
        """Test with values."""
        meta = ChmMetadata(
            title="Test Book",
            isbn="9781234567890",
            isbns=["9781234567890", "9780987654321"],
            file_size_mb=5.5,
        )
        assert meta.title == "Test Book"
        assert meta.isbn == "9781234567890"
        assert len(meta.isbns) == 2
        assert meta.file_size_mb == 5.5
