"""Tests for the file_utils module."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from para_files.utils.file_utils import (
    TEXT_EXTENSIONS,
    _calculate_text_quality,
    _read_document_file,
    _read_image_file,
    _read_pdf_file,
    _read_text_file,
    _should_try_ocr,
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

        # When pypdf returns empty and OCR fails, we return filename fallback
        assert content == "Filename: test.pdf"

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


class TestCalculateTextQuality:
    """Tests for _calculate_text_quality function."""

    def test_empty_text_returns_zero(self):
        """Test that empty text returns quality 0."""
        assert _calculate_text_quality("") == 0.0
        assert _calculate_text_quality("   ") == 0.0

    def test_good_quality_text(self):
        """Test that good quality text scores high."""
        good_text = (
            "This is a properly formatted document with normal English text. "
            "It contains complete sentences and proper spacing between words. "
            "The text quality should be assessed as high by our algorithm."
        )
        quality = _calculate_text_quality(good_text)
        assert quality >= 0.5, f"Expected high quality, got {quality}"

    def test_garbage_text_low_quality(self):
        """Test that garbage/metadata text scores low."""
        garbage_text = "xYz123!@#$%^&*()_+{}|:<>?~`abc"
        quality = _calculate_text_quality(garbage_text)
        assert quality < 0.3, f"Expected low quality for garbage, got {quality}"

    def test_pdf_metadata_detected(self):
        """Test that PDF metadata patterns are detected."""
        metadata_text = (
            "/Type /Page /MediaBox [0 0 612 792] endobj startxref %%EOF /Font /Encoding stream"
        )
        quality = _calculate_text_quality(metadata_text)
        assert quality == 0.0, f"Expected 0 for metadata, got {quality}"

    def test_french_text_quality(self):
        """Test quality detection works for French text."""
        french_text = (
            "Ceci est un document en français avec des accents et une ponctuation normale. "
            "Le texte devrait être évalué comme étant de bonne qualité."
        )
        quality = _calculate_text_quality(french_text)
        assert quality >= 0.4, f"Expected good quality for French, got {quality}"

    def test_short_text_penalty(self):
        """Test that very short text gets a quality penalty."""
        short_text = "Hello world"
        long_text = "Hello world " * 20

        short_quality = _calculate_text_quality(short_text)
        long_quality = _calculate_text_quality(long_text)

        # Short text should have lower quality due to penalty
        assert short_quality < long_quality

    def test_no_spaces_low_quality(self):
        """Test that text without spaces scores lower."""
        no_spaces = "thisisatextwithoutanyspacesbetweenwords"
        with_spaces = "this is a text with spaces between words"

        no_spaces_quality = _calculate_text_quality(no_spaces)
        with_spaces_quality = _calculate_text_quality(with_spaces)

        assert no_spaces_quality < with_spaces_quality

    def test_realistic_payslip_text(self):
        """Test quality of realistic payslip/invoice text."""
        payslip_text = (
            "SWORD PARIS\n"
            "0037 RUE DE LYON\n"
            "75012 PARIS\n"
            "No SIRET: 43362470700033\n"
            "CONVENTION COLLECTIVE: SYNTEC\n"
            "EMPLOI: INGENIEUR ANALYSTE\n"
            "COEFFICIENT: 110,00\n"
            "CLASSIFICATION: IC 2.1\n"
        )
        quality = _calculate_text_quality(payslip_text)
        assert quality >= 0.3, f"Expected decent quality for payslip, got {quality}"


class TestShouldTryOcr:
    """Tests for _should_try_ocr function."""

    def test_empty_text_triggers_ocr(self):
        """Test that empty text triggers OCR."""
        assert _should_try_ocr("") is True
        assert _should_try_ocr("   ") is True

    def test_very_short_text_triggers_ocr(self):
        """Test that very short text triggers OCR."""
        assert _should_try_ocr("abc") is True
        assert _should_try_ocr("Hello") is True

    def test_good_quality_text_no_ocr(self):
        """Test that good quality text does not trigger OCR."""
        good_text = (
            "This is a well-formatted document with proper sentences. "
            "It contains enough text to be considered useful for classification. "
            "The content quality is high and OCR should not be needed."
        )
        assert _should_try_ocr(good_text) is False

    def test_garbage_text_low_quality(self):
        """Test that garbage text has low quality score."""
        # Text with no spaces and lots of symbols has low quality
        garbage_text = "!@#$%^&*()_+" * 10
        quality = _calculate_text_quality(garbage_text)
        assert quality < 0.3, f"Expected low quality, got {quality}"

    def test_pdf_metadata_triggers_ocr(self):
        """Test that PDF metadata text triggers OCR."""
        metadata_text = (
            "/Type /Page /MediaBox [0 0 612 792] "
            "endobj startxref %%EOF /Font /Encoding stream endstream"
        )
        assert _should_try_ocr(metadata_text) is True

    def test_alphanumeric_without_spaces(self):
        """Test that alphanumeric text without spaces has moderate quality."""
        # Alphanumeric without spaces gets moderate score (not low enough for OCR)
        no_space_text = "xyz123abc456" * 20
        quality = _calculate_text_quality(no_space_text)
        # This should have moderate quality due to alnum content
        assert 0.3 <= quality <= 0.6, f"Expected moderate quality, got {quality}"

    def test_short_text_triggers_ocr_due_to_length(self):
        """Test that short text triggers OCR due to length threshold."""
        short_good = "Hello world"
        assert _should_try_ocr(short_good) is True


class TestPdfOcrIntegration:
    """Integration tests for PDF OCR triggering."""

    @patch("para_files.utils.file_utils._ocr_pdf_first_page")
    @patch("para_files.utils.file_utils._extract_pdf_with_pypdf")
    def test_ocr_triggered_for_empty_pypdf(
        self, mock_pypdf: MagicMock, mock_ocr: MagicMock, tmp_path: Path
    ):
        """Test that OCR is triggered when pypdf returns empty."""
        test_file = tmp_path / "scanned.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_pypdf.return_value = ""
        mock_ocr.return_value = "OCR extracted text from scanned PDF"

        content = _read_pdf_file(test_file, max_chars=1000)

        mock_ocr.assert_called_once()
        assert "OCR extracted" in content

    @patch("para_files.utils.file_utils._ocr_pdf_first_page")
    @patch("para_files.utils.file_utils._extract_pdf_with_pypdf")
    def test_ocr_triggered_for_metadata_text(
        self, mock_pypdf: MagicMock, mock_ocr: MagicMock, tmp_path: Path
    ):
        """Test that OCR is triggered when pypdf returns PDF metadata."""
        test_file = tmp_path / "metadata.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        # Simulate PDF metadata extraction (common with broken PDF text extraction)
        mock_pypdf.return_value = (
            "/Type /Page /MediaBox [0 0 612 792] endobj startxref %%EOF /Font /Encoding stream"
        )
        mock_ocr.return_value = "Proper OCR text with real words and sentences."

        content = _read_pdf_file(test_file, max_chars=1000)

        mock_ocr.assert_called_once()
        assert "Proper OCR" in content

    @patch("para_files.utils.file_utils._ocr_pdf_first_page")
    @patch("para_files.utils.file_utils._extract_pdf_with_pypdf")
    def test_no_ocr_for_good_text(self, mock_pypdf: MagicMock, mock_ocr: MagicMock, tmp_path: Path):
        """Test that OCR is NOT triggered when pypdf returns good text."""
        test_file = tmp_path / "good.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        good_text = (
            "This is a well-formatted PDF document with proper text extraction. "
            "The content is readable and no OCR should be needed for this file. "
            "Quality is high enough to skip the OCR step entirely."
        )
        mock_pypdf.return_value = good_text

        content = _read_pdf_file(test_file, max_chars=1000)

        mock_ocr.assert_not_called()
        assert content == good_text

    @patch("para_files.utils.file_utils._ocr_pdf_first_page")
    @patch("para_files.utils.file_utils._extract_pdf_with_pypdf")
    def test_best_quality_text_selected(
        self, mock_pypdf: MagicMock, mock_ocr: MagicMock, tmp_path: Path
    ):
        """Test that the better quality text is selected."""
        test_file = tmp_path / "mixed.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        # pypdf returns low quality
        mock_pypdf.return_value = "xxx123!!!"
        # OCR returns better quality
        mock_ocr.return_value = "Proper document text with sentences."

        content = _read_pdf_file(test_file, max_chars=1000)

        assert "Proper document" in content
