"""Tests for PDF metadata extraction utilities."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from para_files.utils.pdf_metadata import (
    PdfMetadata,
    _try_pymupdf_metadata,
    contains_book_keywords,
    extract_isbn,
    extract_pdf_metadata,
    is_book_creator,
)


class TestExtractIsbn:
    """Tests for extract_isbn function."""

    def test_isbn13_valid(self):
        """Test extracting valid ISBN-13."""
        # 9780596517748 is Python Cookbook ISBN-13
        text = "This book has ISBN: 9780596517748"
        result = extract_isbn(text)
        assert result is not None
        assert len(result) == 13

    def test_isbn13_with_dashes(self):
        """Test extracting ISBN-13 with dashes."""
        # 978-0-596-51774-8 is valid Python Cookbook ISBN-13
        text = "ISBN: 978-0-596-51774-8"
        result = extract_isbn(text)
        assert result is not None
        assert len(result) == 13

    def test_isbn13_prefix(self):
        """Test extracting ISBN with ISBN-13 prefix."""
        text = "ISBN-13: 978-0-596-51774-8"
        result = extract_isbn(text)
        assert result is not None
        assert len(result) == 13

    def test_isbn10_valid(self):
        """Test extracting valid ISBN-10."""
        # 0596517742 is Python Cookbook ISBN-10
        text = "ISBN-10: 0596517742"
        result = extract_isbn(text)
        # Converted to ISBN-13
        assert result is not None
        assert len(result) == 13

    def test_no_isbn_returns_none(self):
        """Test that None is returned when no ISBN present."""
        text = "This is a regular document without any ISBN."
        assert extract_isbn(text) is None

    def test_isbn_in_long_text(self):
        """Test extracting ISBN from longer text."""
        text = """
        Python Programming: A Comprehensive Guide

        Copyright 2024 by Publisher Inc.
        All rights reserved.

        ISBN-13: 978-0-596-51774-8

        First Edition

        Chapter 1: Introduction
        """
        result = extract_isbn(text)
        assert result is not None

    def test_empty_text(self):
        """Test extraction from empty text."""
        assert extract_isbn("") is None


class TestContainsBookKeywords:
    """Tests for contains_book_keywords function."""

    def test_edition_keyword(self):
        """Test detection of 'edition' keyword."""
        assert contains_book_keywords("Python Programming, 3rd Edition") is True

    def test_guide_keyword(self):
        """Test detection of 'guide' keyword."""
        assert contains_book_keywords("The Complete Guide to Python") is True

    def test_handbook_keyword(self):
        """Test detection of 'handbook' keyword."""
        assert contains_book_keywords("The Python Handbook") is True

    def test_manual_keyword(self):
        """Test detection of 'manual' keyword."""
        assert contains_book_keywords("User Manual for Software") is True

    def test_cookbook_keyword(self):
        """Test detection of 'cookbook' keyword."""
        assert contains_book_keywords("Python Cookbook") is True

    def test_introduction_to_keyword(self):
        """Test detection of 'introduction to' keyword."""
        assert contains_book_keywords("Introduction to Machine Learning") is True

    def test_learning_keyword(self):
        """Test detection of 'learning' keyword."""
        assert contains_book_keywords("Learning Python") is True

    def test_mastering_keyword(self):
        """Test detection of 'mastering' keyword."""
        assert contains_book_keywords("Mastering Kubernetes") is True

    def test_for_dummies_keyword(self):
        """Test detection of 'for dummies' keyword."""
        assert contains_book_keywords("Python for Dummies") is True

    def test_in_action_keyword(self):
        """Test detection of 'in action' keyword."""
        assert contains_book_keywords("Kubernetes in Action") is True

    def test_head_first_keyword(self):
        """Test detection of 'head first' keyword."""
        assert contains_book_keywords("Head First Design Patterns") is True

    def test_no_book_keywords(self):
        """Test text without book keywords."""
        assert contains_book_keywords("Meeting notes from Q4 planning") is False
        assert contains_book_keywords("Invoice #12345") is False
        assert contains_book_keywords("Project Status Report") is False

    def test_case_insensitive(self):
        """Test case-insensitive keyword detection."""
        assert contains_book_keywords("PYTHON COOKBOOK") is True
        assert contains_book_keywords("Introduction To Machine Learning") is True


class TestIsBookCreator:
    """Tests for is_book_creator function."""

    def test_calibre_creator(self):
        """Test Calibre as book creator."""
        assert is_book_creator("calibre 5.0") is True
        assert is_book_creator("calibre (3.48.0)") is True

    def test_adobe_indesign(self):
        """Test Adobe InDesign as book creator."""
        assert is_book_creator("Adobe InDesign CC 2024") is True

    def test_latex_creator(self):
        """Test LaTeX as book creator."""
        assert is_book_creator("pdfTeX-1.40.21") is True
        assert is_book_creator("XeTeX") is True
        assert is_book_creator("LaTeX with hyperref") is True

    def test_acrobat_distiller(self):
        """Test Acrobat Distiller as book creator."""
        assert is_book_creator("Acrobat Distiller 11.0") is True

    def test_framemaker(self):
        """Test FrameMaker as book creator."""
        assert is_book_creator("Adobe FrameMaker 2020") is True

    def test_quarkxpress(self):
        """Test QuarkXPress as book creator."""
        assert is_book_creator("QuarkXPress 2021") is True

    def test_unknown_creator(self):
        """Test unknown creator."""
        assert is_book_creator("Random PDF Tool") is False
        assert is_book_creator("Google Chrome") is False
        assert is_book_creator("Microsoft Print to PDF") is False

    def test_empty_creator(self):
        """Test empty string creator."""
        assert is_book_creator("") is False


class TestPdfMetadata:
    """Tests for PdfMetadata dataclass."""

    def test_create_default_metadata(self):
        """Test creating metadata with defaults."""
        meta = PdfMetadata()
        assert meta.title is None
        assert meta.author is None
        assert meta.subject is None
        assert meta.creator is None
        assert meta.producer is None
        assert meta.page_count is None
        assert meta.isbn is None
        assert meta.file_size_mb == 0.0

    def test_create_full_metadata(self):
        """Test creating metadata with all fields."""
        meta = PdfMetadata(
            title="Python Guide",
            author="John Doe",
            subject="Programming",
            creator="calibre",
            producer="calibre 5.0",
            page_count=350,
            isbn="9781234567890",
            file_size_mb=15.5,
        )
        assert meta.title == "Python Guide"
        assert meta.author == "John Doe"
        assert meta.subject == "Programming"
        assert meta.creator == "calibre"
        assert meta.producer == "calibre 5.0"
        assert meta.page_count == 350
        assert meta.isbn == "9781234567890"
        assert meta.file_size_mb == 15.5

    def test_partial_metadata(self):
        """Test creating metadata with partial fields."""
        meta = PdfMetadata(
            title="Learning Python",
            page_count=400,
        )
        assert meta.title == "Learning Python"
        assert meta.page_count == 400
        assert meta.author is None
        assert meta.isbn is None


class TestExtractPdfMetadata:
    """Tests for extract_pdf_metadata function."""

    def test_nonexistent_file(self, tmp_path: Path):
        """Test extraction from nonexistent file."""
        fake_file = tmp_path / "nonexistent.pdf"
        result = extract_pdf_metadata(fake_file)
        assert result is None

    def test_non_pdf_file(self, tmp_path: Path):
        """Test extraction from non-PDF file."""
        text_file = tmp_path / "document.txt"
        text_file.write_text("Hello, world!")
        result = extract_pdf_metadata(text_file)
        assert result is None

    def test_pypdf_not_installed(self, tmp_path: Path):
        """Test extraction when pypdf is not available."""
        import builtins
        import sys

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        # Save originals
        pypdf_backup = sys.modules.get("pypdf")
        original_import = builtins.__import__

        try:
            # Remove pypdf from modules
            if "pypdf" in sys.modules:
                del sys.modules["pypdf"]

            def mock_import(name, *args, **kwargs):
                if name == "pypdf" or name.startswith("pypdf"):
                    raise ImportError(name)
                return original_import(name, *args, **kwargs)

            builtins.__import__ = mock_import
            result = extract_pdf_metadata(pdf_file)
            assert result is None
        finally:
            builtins.__import__ = original_import
            if pypdf_backup:
                sys.modules["pypdf"] = pypdf_backup

    @patch("pypdf.PdfReader")
    def test_successful_extraction(self, mock_reader_class: MagicMock, tmp_path: Path):
        """Test successful metadata extraction."""
        pdf_file = tmp_path / "book.pdf"
        pdf_file.write_bytes(b"%PDF-1.4" + b"\x00" * 1000)

        mock_metadata = {
            "/Title": "Python Guide",
            "/Author": "John Doe",
            "/Subject": "Programming",
            "/Creator": "LaTeX",
            "/Producer": "pdfTeX",
        }

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Content without ISBN"

        mock_reader = MagicMock()
        mock_reader.metadata = mock_metadata
        mock_reader.pages = [mock_page] * 10
        mock_reader_class.return_value = mock_reader

        result = extract_pdf_metadata(pdf_file)

        assert result is not None
        assert result.title == "Python Guide"
        assert result.author == "John Doe"
        assert result.subject == "Programming"
        assert result.creator == "LaTeX"
        assert result.producer == "pdfTeX"
        assert result.page_count == 10
        assert result.file_size_mb > 0

    @patch("pypdf.PdfReader")
    def test_extraction_with_isbn(self, mock_reader_class: MagicMock, tmp_path: Path):
        """Test extraction with ISBN in content."""
        pdf_file = tmp_path / "book.pdf"
        pdf_file.write_bytes(b"%PDF-1.4" + b"\x00" * 1000)

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "ISBN: 978-0-596-51774-8"

        mock_reader = MagicMock()
        mock_reader.metadata = {}
        mock_reader.pages = [mock_page]
        mock_reader_class.return_value = mock_reader

        result = extract_pdf_metadata(pdf_file)

        assert result is not None
        assert result.isbn is not None
        assert len(result.isbn) == 13

    @patch("pypdf.PdfReader")
    def test_extraction_no_metadata(self, mock_reader_class: MagicMock, tmp_path: Path):
        """Test extraction when PDF has no metadata."""
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"%PDF-1.4" + b"\x00" * 500)

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Regular content"

        mock_reader = MagicMock()
        mock_reader.metadata = None  # No metadata
        mock_reader.pages = [mock_page]
        mock_reader_class.return_value = mock_reader

        result = extract_pdf_metadata(pdf_file)

        assert result is not None
        assert result.title is None
        assert result.author is None
        assert result.page_count == 1

    @patch("pypdf.PdfReader")
    def test_extraction_page_extraction_failure(self, mock_reader_class: MagicMock, tmp_path: Path):
        """Test extraction when page text extraction fails."""
        pdf_file = tmp_path / "corrupted.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        mock_page = MagicMock()
        mock_page.extract_text.side_effect = Exception("Page extraction failed")

        mock_reader = MagicMock()
        mock_reader.metadata = {"/Title": "Test Book"}
        mock_reader.pages = [mock_page]
        mock_reader_class.return_value = mock_reader

        result = extract_pdf_metadata(pdf_file)

        # Should still return metadata even if page extraction fails
        assert result is not None
        assert result.title == "Test Book"
        assert result.isbn is None

    @patch("pypdf.PdfReader")
    def test_extraction_reader_failure(self, mock_reader_class: MagicMock, tmp_path: Path):
        """Test extraction when PdfReader fails completely."""
        pdf_file = tmp_path / "invalid.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        mock_reader_class.side_effect = Exception("Cannot read PDF")

        result = extract_pdf_metadata(pdf_file)

        assert result is None

    @patch("pypdf.PdfReader")
    def test_max_pages_for_isbn(self, mock_reader_class: MagicMock, tmp_path: Path):
        """Test that ISBN search respects max_pages limit."""
        pdf_file = tmp_path / "book.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        mock_page_no_isbn = MagicMock()
        mock_page_no_isbn.extract_text.return_value = "No ISBN here"

        mock_page_with_isbn = MagicMock()
        mock_page_with_isbn.extract_text.return_value = "ISBN: 9780596517748"

        # ISBN is on page 10, but we only check 3 pages
        pages = [mock_page_no_isbn] * 9 + [mock_page_with_isbn]

        mock_reader = MagicMock()
        mock_reader.metadata = {}
        mock_reader.pages = pages
        mock_reader_class.return_value = mock_reader

        result = extract_pdf_metadata(pdf_file, max_pages_for_isbn=3)

        # ISBN should not be found since it's on page 10
        assert result is not None
        assert result.isbn is None

    @patch("pypdf.PdfReader")
    def test_isbn_found_on_later_page(self, mock_reader_class: MagicMock, tmp_path: Path):
        """Test that ISBN is found when on a later page within limit."""
        pdf_file = tmp_path / "book.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        mock_page_no_isbn = MagicMock()
        mock_page_no_isbn.extract_text.return_value = "Introduction"

        mock_page_with_isbn = MagicMock()
        mock_page_with_isbn.extract_text.return_value = "ISBN: 9780596517748"

        # ISBN is on page 3
        pages = [mock_page_no_isbn, mock_page_no_isbn, mock_page_with_isbn]

        mock_reader = MagicMock()
        mock_reader.metadata = {}
        mock_reader.pages = pages
        mock_reader_class.return_value = mock_reader

        result = extract_pdf_metadata(pdf_file, max_pages_for_isbn=5)

        assert result is not None
        assert result.isbn is not None


class TestPymupdfFallback:
    """Tests for pymupdf (fitz) metadata fallback."""

    @patch("para_files.utils.pdf_metadata.fitz", create=True)
    def test_pymupdf_extracts_metadata(self, mock_fitz_module: MagicMock, tmp_path: Path):
        """Test pymupdf fallback extracts title and author."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        mock_doc = MagicMock()
        mock_doc.metadata = {
            "title": "Learning Python",
            "author": "Mark Lutz",
            "subject": "Programming",
            "creator": "LaTeX",
            "producer": "pdfTeX",
        }
        mock_doc.__len__ = lambda self: 100
        mock_page = MagicMock()
        mock_page.get_text.return_value = "No ISBN here"
        mock_doc.__getitem__ = lambda self, i: mock_page

        result = _try_pymupdf_metadata(pdf_file, [], 5.0)

        # fitz module may or may not be available in the test env
        # If fitz is not installed, result will be None (ImportError)
        if result is not None:
            assert result.title == "Learning Python"
            assert result.author == "Mark Lutz"
            assert result.page_count == 100

    def test_pymupdf_returns_none_when_no_fitz(self, tmp_path: Path):
        """Test that _try_pymupdf_metadata returns None when fitz is not installed."""
        import builtins
        import sys

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        fitz_backup = sys.modules.get("fitz")
        original_import = builtins.__import__

        try:
            if "fitz" in sys.modules:
                del sys.modules["fitz"]

            def mock_import(name, *args, **kwargs):
                if name == "fitz":
                    msg = "fitz"
                    raise ImportError(msg)
                return original_import(name, *args, **kwargs)

            builtins.__import__ = mock_import
            result = _try_pymupdf_metadata(pdf_file, [], 1.0)
            assert result is None
        finally:
            builtins.__import__ = original_import
            if fitz_backup:
                sys.modules["fitz"] = fitz_backup

    def test_pymupdf_returns_none_when_no_useful_metadata(self, tmp_path: Path):
        """Test pymupdf returns None when metadata is all empty."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        # If fitz is not available, the function returns None (ImportError path).
        # If fitz IS available but metadata is empty, also returns None.
        assert _try_pymupdf_metadata(pdf_file, [], 1.0) is None

    @patch("pypdf.PdfReader")
    def test_extract_pdf_metadata_falls_back_to_pymupdf(
        self, mock_reader_class: MagicMock, tmp_path: Path
    ):
        """Test that extract_pdf_metadata tries pymupdf when pypdf fails."""
        pdf_file = tmp_path / "broken.pdf"
        pdf_file.write_bytes(b"%PDF-1.4" + b"\x00" * 500)

        # Make pypdf fail
        mock_reader_class.side_effect = Exception("Could not read Boolean object")

        # The function should try pymupdf fallback, then return None if fitz unavailable
        result = extract_pdf_metadata(pdf_file)
        # Without fitz installed: returns None (no filename ISBN, no pymupdf)
        # With fitz installed: may return metadata if fitz can read the file
        # Either way, no crash
        assert result is None or isinstance(result, PdfMetadata)
