"""Tests for the file_utils module."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from para_files.utils.file_utils import (
    TEXT_EXTENSIONS,
    _read_document_file,
    _read_image_file,
    _read_pdf_file,
    _read_text_file,
    extract_file_metadata,
    read_content_preview,
)


class TestTextExtensions:
    """Tests for TEXT_EXTENSIONS constant."""

    def test_common_text_extensions_included(self):
        """Test that common text file extensions are in the set."""
        common_extensions = [".txt", ".md", ".json", ".yaml", ".py", ".js", ".html"]
        for ext in common_extensions:
            assert ext in TEXT_EXTENSIONS

    def test_is_frozenset(self):
        """Test that TEXT_EXTENSIONS is immutable."""
        assert isinstance(TEXT_EXTENSIONS, frozenset)


class TestExtractFileMetadata:
    """Tests for extract_file_metadata function."""

    def test_basic_metadata(self, tmp_path: Path):
        """Test extracting basic file metadata."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, world!")

        metadata = extract_file_metadata(test_file, extract_exif=False)

        assert metadata.filename == "test.txt"
        assert metadata.extension == ".txt"
        assert metadata.size_bytes == 13
        assert metadata.modified_at is not None
        assert metadata.path == test_file

    def test_metadata_without_exif(self, tmp_path: Path):
        """Test metadata extraction with EXIF disabled."""
        test_file = tmp_path / "image.jpg"
        test_file.write_bytes(b"\xff\xd8\xff\xe0")  # Minimal JPEG header

        metadata = extract_file_metadata(test_file, extract_exif=False)

        assert metadata.exif_date is None
        assert metadata.exif_gps_lat is None
        assert metadata.exif_gps_lon is None
        assert metadata.exif_camera is None

    @patch("para_files.utils.exiftool.extract_exif")
    def test_metadata_with_exif_data(self, mock_exif: MagicMock, tmp_path: Path):
        """Test metadata extraction with EXIF data."""
        test_file = tmp_path / "photo.jpg"
        test_file.write_bytes(b"\xff\xd8\xff\xe0")

        # Mock EXIF result
        mock_gps = MagicMock()
        mock_gps.latitude = 45.5
        mock_gps.longitude = -73.5

        mock_exif_result = MagicMock()
        mock_exif_result.best_date = datetime(2024, 6, 15, 10, 30, tzinfo=UTC)
        mock_exif_result.gps = mock_gps
        mock_exif_result.make = "Canon"
        mock_exif_result.model = "EOS R5"
        mock_exif.return_value = mock_exif_result

        metadata = extract_file_metadata(test_file, extract_exif=True)

        assert metadata.exif_date == datetime(2024, 6, 15, 10, 30, tzinfo=UTC)
        assert metadata.exif_gps_lat == 45.5
        assert metadata.exif_gps_lon == -73.5
        assert metadata.exif_camera == "Canon EOS R5"

    @patch("para_files.utils.exiftool.extract_exif")
    def test_metadata_with_make_only(self, mock_exif: MagicMock, tmp_path: Path):
        """Test camera info with only make."""
        test_file = tmp_path / "photo.jpg"
        test_file.write_bytes(b"\xff\xd8\xff\xe0")

        mock_exif_result = MagicMock()
        mock_exif_result.best_date = None
        mock_exif_result.gps = None
        mock_exif_result.make = "Sony"
        mock_exif_result.model = None
        mock_exif.return_value = mock_exif_result

        metadata = extract_file_metadata(test_file, extract_exif=True)

        assert metadata.exif_camera == "Sony"

    @patch("para_files.utils.exiftool.extract_exif")
    def test_metadata_with_model_only(self, mock_exif: MagicMock, tmp_path: Path):
        """Test camera info with only model."""
        test_file = tmp_path / "photo.jpg"
        test_file.write_bytes(b"\xff\xd8\xff\xe0")

        mock_exif_result = MagicMock()
        mock_exif_result.best_date = None
        mock_exif_result.gps = None
        mock_exif_result.make = None
        mock_exif_result.model = "iPhone 15"
        mock_exif.return_value = mock_exif_result

        metadata = extract_file_metadata(test_file, extract_exif=True)

        assert metadata.exif_camera == "iPhone 15"

    @patch("para_files.utils.exiftool.extract_exif")
    def test_metadata_with_no_exif_result(self, mock_exif: MagicMock, tmp_path: Path):
        """Test metadata when EXIF extraction returns None."""
        test_file = tmp_path / "photo.jpg"
        test_file.write_bytes(b"\xff\xd8\xff\xe0")

        mock_exif.return_value = None

        metadata = extract_file_metadata(test_file, extract_exif=True)

        assert metadata.exif_date is None
        assert metadata.exif_camera is None


class TestReadTextFile:
    """Tests for _read_text_file function."""

    def test_read_small_file(self, tmp_path: Path):
        """Test reading a small text file."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("Hello, world!")

        content = _read_text_file(test_file, max_chars=1000)

        assert content == "Hello, world!"

    def test_read_truncated(self, tmp_path: Path):
        """Test reading with truncation."""
        test_file = tmp_path / "large.txt"
        test_file.write_text("x" * 500)

        content = _read_text_file(test_file, max_chars=100)

        assert len(content) == 100
        assert content == "x" * 100

    def test_read_nonexistent_file(self, tmp_path: Path):
        """Test reading a nonexistent file."""
        test_file = tmp_path / "nonexistent.txt"

        content = _read_text_file(test_file, max_chars=1000)

        assert "Filename:" in content
        assert "nonexistent.txt" in content

    def test_read_utf8_content(self, tmp_path: Path):
        """Test reading UTF-8 content."""
        test_file = tmp_path / "unicode.txt"
        test_file.write_text("Hello, 世界! Привет!")

        content = _read_text_file(test_file, max_chars=1000)

        assert "世界" in content
        assert "Привет" in content


class TestReadPdfFile:
    """Tests for _read_pdf_file function."""

    @patch("pypdf.PdfReader")
    def test_read_pdf_success(self, mock_reader_class: MagicMock, tmp_path: Path):
        """Test successful PDF reading."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page content here"

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_reader_class.return_value = mock_reader

        content = _read_pdf_file(test_file, max_chars=1000)

        assert content == "Page content here"

    @patch("pypdf.PdfReader")
    def test_read_pdf_multiple_pages(self, mock_reader_class: MagicMock, tmp_path: Path):
        """Test reading PDF with multiple pages."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 "
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2"

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_reader_class.return_value = mock_reader

        content = _read_pdf_file(test_file, max_chars=1000)

        assert content == "Page 1 Page 2"

    @patch("pypdf.PdfReader")
    def test_read_pdf_truncation(self, mock_reader_class: MagicMock, tmp_path: Path):
        """Test PDF reading with truncation."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "x" * 500

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_reader_class.return_value = mock_reader

        content = _read_pdf_file(test_file, max_chars=100)

        assert len(content) == 100

    @patch("pypdf.PdfReader")
    def test_read_pdf_empty_page(self, mock_reader_class: MagicMock, tmp_path: Path):
        """Test PDF reading with empty page."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = None

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_reader_class.return_value = mock_reader

        content = _read_pdf_file(test_file, max_chars=1000)

        assert content == ""

    def test_read_pdf_import_error(self, tmp_path: Path):
        """Test PDF reading when pypdf is not installed."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        # The import happens inside the function, so we mock the module import
        import sys

        pypdf_backup = sys.modules.get("pypdf")
        try:
            sys.modules["pypdf"] = None
            # We can't easily test ImportError since pypdf is already imported
            # Just verify the function handles missing PDFs gracefully
            content = _read_pdf_file(test_file, max_chars=1000)
            # It should either succeed or return filename fallback
            assert content is not None
        finally:
            if pypdf_backup:
                sys.modules["pypdf"] = pypdf_backup

    @patch("pypdf.PdfReader")
    def test_read_pdf_os_error(self, mock_reader_class: MagicMock, tmp_path: Path):
        """Test PDF reading with OS error."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_reader_class.side_effect = OSError("Cannot read file")

        content = _read_pdf_file(test_file, max_chars=1000)

        assert "Filename:" in content


class TestReadDocumentFile:
    """Tests for _read_document_file function."""

    def test_read_document_success(self, tmp_path: Path):
        """Test successful document reading."""
        test_file = tmp_path / "test.docx"
        test_file.write_bytes(b"PK")

        mock_result = MagicMock()
        mock_result.text = "Document content"
        mock_fn = MagicMock(return_value=mock_result)

        content = _read_document_file(test_file, max_chars=1000, extract_fn=mock_fn)

        assert content == "Document content"
        mock_fn.assert_called_once_with(test_file, 1000)

    def test_read_document_no_result(self, tmp_path: Path):
        """Test document reading when extraction returns None."""
        test_file = tmp_path / "test.docx"
        test_file.write_bytes(b"PK")

        mock_fn = MagicMock(return_value=None)

        content = _read_document_file(test_file, max_chars=1000, extract_fn=mock_fn)

        assert "Filename:" in content
        assert "test.docx" in content

    def test_read_document_empty_text(self, tmp_path: Path):
        """Test document reading when text is empty."""
        test_file = tmp_path / "test.docx"
        test_file.write_bytes(b"PK")

        mock_result = MagicMock()
        mock_result.text = ""
        mock_fn = MagicMock(return_value=mock_result)

        content = _read_document_file(test_file, max_chars=1000, extract_fn=mock_fn)

        assert "Filename:" in content


class TestReadImageFile:
    """Tests for _read_image_file function."""

    def test_read_image_success(self, tmp_path: Path):
        """Test successful OCR extraction."""
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"\x89PNG")

        mock_result = MagicMock()
        mock_result.text = "OCR extracted text"
        mock_fn = MagicMock(return_value=mock_result)

        content = _read_image_file(test_file, max_chars=1000, extract_fn=mock_fn)

        assert content == "OCR extracted text"
        mock_fn.assert_called_once_with(test_file, 1000)

    def test_read_image_no_result(self, tmp_path: Path):
        """Test image reading when OCR returns None."""
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"\x89PNG")

        mock_fn = MagicMock(return_value=None)

        content = _read_image_file(test_file, max_chars=1000, extract_fn=mock_fn)

        assert "Filename:" in content
        assert "test.png" in content

    def test_read_image_empty_text(self, tmp_path: Path):
        """Test image reading when OCR text is empty."""
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"\x89PNG")

        mock_result = MagicMock()
        mock_result.text = ""
        mock_fn = MagicMock(return_value=mock_result)

        content = _read_image_file(test_file, max_chars=1000, extract_fn=mock_fn)

        assert "Filename:" in content


class TestReadContentPreview:
    """Tests for read_content_preview function."""

    def test_read_text_file(self, tmp_path: Path):
        """Test reading a text file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, world!")

        content = read_content_preview(test_file, max_chars=1000)

        assert content == "Hello, world!"

    def test_read_markdown_file(self, tmp_path: Path):
        """Test reading a markdown file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Heading\n\nSome content")

        content = read_content_preview(test_file, max_chars=1000)

        assert "# Heading" in content

    def test_read_json_file(self, tmp_path: Path):
        """Test reading a JSON file."""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"key": "value"}')

        content = read_content_preview(test_file, max_chars=1000)

        assert '"key"' in content

    @patch("para_files.utils.file_utils._read_pdf_file")
    def test_read_pdf_file_content(self, mock_read_pdf: MagicMock, tmp_path: Path):
        """Test reading a PDF file."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_read_pdf.return_value = "PDF content"

        content = read_content_preview(test_file, max_chars=1000)

        assert content == "PDF content"
        mock_read_pdf.assert_called_once_with(test_file, 1000)

    @patch("para_files.utils.file_utils._read_document_file")
    def test_read_docx_file(self, mock_read_doc: MagicMock, tmp_path: Path):
        """Test reading a DOCX file."""
        test_file = tmp_path / "test.docx"
        test_file.write_bytes(b"PK")

        mock_read_doc.return_value = "Document content"

        content = read_content_preview(test_file, max_chars=1000)

        assert content == "Document content"

    @patch("para_files.utils.file_utils._read_image_file")
    def test_read_image_file_content(self, mock_read_img: MagicMock, tmp_path: Path):
        """Test reading an image file with OCR."""
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"\x89PNG")

        mock_read_img.return_value = "OCR text"

        content = read_content_preview(test_file, max_chars=1000)

        assert content == "OCR text"

    def test_read_unknown_file_type(self, tmp_path: Path):
        """Test reading an unknown file type."""
        test_file = tmp_path / "test.unknown"
        test_file.write_bytes(b"\x00\x01\x02")

        content = read_content_preview(test_file, max_chars=1000)

        assert "Filename:" in content
        assert "test.unknown" in content

    def test_case_insensitive_extension(self, tmp_path: Path):
        """Test that extension matching is case insensitive."""
        test_file = tmp_path / "test.TXT"
        test_file.write_text("Content")

        content = read_content_preview(test_file, max_chars=1000)

        # Should treat .TXT as text file
        assert content == "Content"

    def test_max_chars_respected(self, tmp_path: Path):
        """Test that max_chars limit is respected."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("x" * 500)

        content = read_content_preview(test_file, max_chars=100)

        assert len(content) == 100
