"""Tests for PDF metadata extraction utilities."""

from __future__ import annotations

from para_files.utils.pdf_metadata import (
    PdfMetadata,
    contains_book_keywords,
    extract_isbn,
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
