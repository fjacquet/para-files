"""Tests for EPUB metadata extraction."""

from __future__ import annotations

import zipfile
from pathlib import Path

from para_files.utils.epub_metadata import (
    EpubMetadata,
    _extract_isbns_from_opf,
    _extract_metadata_from_opf,
    _find_opf_path,
    extract_epub_metadata,
)


class TestFindOpfPath:
    """Tests for _find_opf_path function."""

    def test_finds_opf_from_container(self, tmp_path: Path):
        """Test finding OPF path from container.xml."""
        epub_file = tmp_path / "test.epub"

        with zipfile.ZipFile(epub_file, "w") as zf:
            container_xml = """<?xml version="1.0"?>
            <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
              <rootfiles>
                <rootfile full-path="OEBPS/content.opf"
                          media-type="application/oebps-package+xml"/>
              </rootfiles>
            </container>"""
            zf.writestr("META-INF/container.xml", container_xml)

        with zipfile.ZipFile(epub_file, "r") as zf:
            result = _find_opf_path(zf)
            assert result == "OEBPS/content.opf"

    def test_fallback_to_opf_file(self, tmp_path: Path):
        """Test fallback to finding .opf file directly."""
        epub_file = tmp_path / "test.epub"

        with zipfile.ZipFile(epub_file, "w") as zf:
            zf.writestr("content.opf", "<package/>")

        with zipfile.ZipFile(epub_file, "r") as zf:
            result = _find_opf_path(zf)
            assert result == "content.opf"

    def test_returns_none_when_not_found(self, tmp_path: Path):
        """Test returns None when no OPF found."""
        epub_file = tmp_path / "test.epub"

        with zipfile.ZipFile(epub_file, "w") as zf:
            zf.writestr("dummy.txt", "content")

        with zipfile.ZipFile(epub_file, "r") as zf:
            result = _find_opf_path(zf)
            assert result is None


class TestExtractIsbnsFromOpf:
    """Tests for _extract_isbns_from_opf function."""

    def test_extracts_isbn_from_identifier(self):
        """Test extracting ISBN from dc:identifier."""
        opf = b"""<?xml version="1.0"?>
        <package xmlns="http://www.idpf.org/2007/opf"
                 xmlns:dc="http://purl.org/dc/elements/1.1/">
          <metadata>
            <dc:identifier id="isbn">9781234567890</dc:identifier>
          </metadata>
        </package>"""
        result = _extract_isbns_from_opf(opf)
        assert "9781234567890" in result

    def test_extracts_isbn_with_scheme(self):
        """Test extracting ISBN with scheme attribute."""
        opf = b"""<?xml version="1.0"?>
        <package xmlns="http://www.idpf.org/2007/opf"
                 xmlns:dc="http://purl.org/dc/elements/1.1/"
                 xmlns:opf="http://www.idpf.org/2007/opf">
          <metadata>
            <dc:identifier opf:scheme="ISBN">9781234567890</dc:identifier>
          </metadata>
        </package>"""
        result = _extract_isbns_from_opf(opf)
        assert len(result) > 0
        assert "9781234567890" in result

    def test_extracts_multiple_isbns(self):
        """Test extracting multiple ISBNs."""
        opf = b"""<?xml version="1.0"?>
        <package xmlns="http://www.idpf.org/2007/opf"
                 xmlns:dc="http://purl.org/dc/elements/1.1/">
          <metadata>
            <dc:identifier id="isbn13">9781234567890</dc:identifier>
            <dc:identifier id="isbn10">1234567890</dc:identifier>
          </metadata>
        </package>"""
        result = _extract_isbns_from_opf(opf)
        assert len(result) >= 1

    def test_returns_empty_for_no_isbn(self):
        """Test returns empty list when no ISBN found."""
        opf = b"""<?xml version="1.0"?>
        <package xmlns="http://www.idpf.org/2007/opf">
          <metadata>
            <dc:title>Test Book</dc:title>
          </metadata>
        </package>"""
        result = _extract_isbns_from_opf(opf)
        assert result == []


class TestExtractMetadataFromOpf:
    """Tests for _extract_metadata_from_opf function."""

    def test_extracts_title(self):
        """Test extracting title."""
        opf = b"""<?xml version="1.0"?>
        <package xmlns:dc="http://purl.org/dc/elements/1.1/">
          <metadata>
            <dc:title>Python Programming</dc:title>
          </metadata>
        </package>"""
        result = _extract_metadata_from_opf(opf)
        assert result["title"] == "Python Programming"

    def test_extracts_author(self):
        """Test extracting author (creator)."""
        opf = b"""<?xml version="1.0"?>
        <package xmlns:dc="http://purl.org/dc/elements/1.1/">
          <metadata>
            <dc:creator>John Doe</dc:creator>
          </metadata>
        </package>"""
        result = _extract_metadata_from_opf(opf)
        assert result["author"] == "John Doe"

    def test_extracts_language(self):
        """Test extracting language."""
        opf = b"""<?xml version="1.0"?>
        <package xmlns:dc="http://purl.org/dc/elements/1.1/">
          <metadata>
            <dc:language>en</dc:language>
          </metadata>
        </package>"""
        result = _extract_metadata_from_opf(opf)
        assert result["language"] == "en"

    def test_extracts_publisher(self):
        """Test extracting publisher."""
        opf = b"""<?xml version="1.0"?>
        <package xmlns:dc="http://purl.org/dc/elements/1.1/">
          <metadata>
            <dc:publisher>O'Reilly Media</dc:publisher>
          </metadata>
        </package>"""
        result = _extract_metadata_from_opf(opf)
        assert result["publisher"] == "O'Reilly Media"

    def test_handles_missing_metadata(self):
        """Test handles missing metadata gracefully."""
        opf = b"""<?xml version="1.0"?><package><metadata/></package>"""
        result = _extract_metadata_from_opf(opf)
        assert result["title"] is None
        assert result["author"] is None


class TestExtractEpubMetadata:
    """Tests for extract_epub_metadata function."""

    def test_returns_none_for_nonexistent_file(self, tmp_path: Path):
        """Test returns None for nonexistent file."""
        result = extract_epub_metadata(tmp_path / "nonexistent.epub")
        assert result is None

    def test_returns_none_for_non_epub_file(self, tmp_path: Path):
        """Test returns None for non-EPUB file."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")
        result = extract_epub_metadata(pdf_file)
        assert result is None

    def test_returns_none_for_invalid_zip(self, tmp_path: Path):
        """Test returns None for invalid ZIP file."""
        epub_file = tmp_path / "invalid.epub"
        epub_file.write_bytes(b"not a zip file")
        result = extract_epub_metadata(epub_file)
        assert result is None

    def test_returns_none_when_no_opf(self, tmp_path: Path):
        """Test returns None when no OPF file found."""
        epub_file = tmp_path / "test.epub"
        with zipfile.ZipFile(epub_file, "w") as zf:
            zf.writestr("dummy.txt", "content")
        result = extract_epub_metadata(epub_file)
        assert result is None

    def test_extracts_full_metadata(self, tmp_path: Path):
        """Test extracting full metadata from EPUB."""
        epub_file = tmp_path / "test.epub"

        container_xml = """<?xml version="1.0"?>
        <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
          <rootfiles>
            <rootfile full-path="content.opf"
                      media-type="application/oebps-package+xml"/>
          </rootfiles>
        </container>"""

        opf_content = """<?xml version="1.0"?>
        <package xmlns="http://www.idpf.org/2007/opf"
                 xmlns:dc="http://purl.org/dc/elements/1.1/">
          <metadata>
            <dc:title>Python for Beginners</dc:title>
            <dc:creator>Jane Smith</dc:creator>
            <dc:language>en</dc:language>
            <dc:publisher>Tech Books Inc</dc:publisher>
            <dc:identifier id="isbn">9781234567890</dc:identifier>
          </metadata>
        </package>"""

        with zipfile.ZipFile(epub_file, "w") as zf:
            zf.writestr("META-INF/container.xml", container_xml)
            zf.writestr("content.opf", opf_content)

        result = extract_epub_metadata(epub_file)

        assert result is not None
        assert result.title == "Python for Beginners"
        assert result.author == "Jane Smith"
        assert result.language == "en"
        assert result.publisher == "Tech Books Inc"
        assert result.isbn == "9781234567890"
        assert "9781234567890" in result.isbns
        assert result.file_size_mb > 0


class TestEpubMetadataDataclass:
    """Tests for EpubMetadata dataclass."""

    def test_default_values(self):
        """Test default values."""
        meta = EpubMetadata()
        assert meta.title is None
        assert meta.author is None
        assert meta.isbn is None
        assert meta.isbns == []
        assert meta.language is None
        assert meta.publisher is None
        assert meta.file_size_mb == 0.0

    def test_with_values(self):
        """Test with values."""
        meta = EpubMetadata(
            title="Test Book",
            author="Author Name",
            isbn="9781234567890",
            isbns=["9781234567890"],
            language="en",
            publisher="Publisher",
            file_size_mb=2.5,
        )
        assert meta.title == "Test Book"
        assert meta.author == "Author Name"
        assert meta.isbn == "9781234567890"
        assert meta.language == "en"
        assert meta.publisher == "Publisher"
        assert meta.file_size_mb == 2.5
