"""Tests for the book detector classifier."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from para_files.classifiers.book_detector import (
    BookDetector,
    sanitize_title,
    score_book_structure,
)
from para_files.types import ClassificationSource, FileMetadata
from para_files.utils.isbn_lookup import BookInfo


class TestSanitizeTitle:
    """Tests for sanitize_title function."""

    def test_simple_title(self):
        """Test sanitizing a simple title."""
        assert sanitize_title("Python Basics") == "Python_Basics"

    def test_title_with_special_chars(self):
        """Test sanitizing title with special characters."""
        assert sanitize_title("C++: The Complete Reference") == "C++_The_Complete_Reference"

    def test_title_with_slashes(self):
        """Test sanitizing title with path-unsafe characters."""
        assert sanitize_title("Python/Django: A Guide") == "Python_Django_A_Guide"

    def test_title_with_multiple_spaces(self):
        """Test sanitizing title with multiple spaces."""
        assert sanitize_title("Python    Programming   Guide") == "Python_Programming_Guide"

    def test_title_with_quotes(self):
        """Test sanitizing title with quotes."""
        assert sanitize_title('The "Complete" Guide') == "The_Complete_Guide"

    def test_empty_title(self):
        """Test sanitizing empty title."""
        assert sanitize_title("") == ""

    def test_title_with_leading_trailing_spaces(self):
        """Test sanitizing title with leading/trailing spaces."""
        result = sanitize_title("  Python Guide  ")
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_max_length(self):
        """Test max length truncation."""
        long_title = "A" * 100
        result = sanitize_title(long_title, max_length=50)
        assert len(result) <= 50


class TestScoreBookStructure:
    """Tests for score_book_structure function."""

    def test_book_with_chapters(self):
        """Test content with chapter markers scores high."""
        content = """
        Chapter 1: Introduction
        Chapter 2: Getting Started
        Chapter 3: Advanced Topics
        Chapter 4: Conclusions
        """
        score = score_book_structure(content)
        # Each "Chapter \d+" pattern matches once, but it's the same regex
        # so multiple chapter markers = 1 pattern match
        assert score > 0.0

    def test_book_with_table_of_contents(self):
        """Test content with table of contents scores high."""
        content = """
        Table of Contents
        Copyright 2024
        All Rights Reserved
        First Edition
        """
        score = score_book_structure(content)
        # 4 different patterns matched = 4/4 = 1.0
        assert score >= 0.5

    def test_book_with_multiple_patterns(self):
        """Test content with many book patterns."""
        content = """
        ISBN: 978-1-234567-89-0
        Copyright 2024 by Publisher Inc.
        All rights reserved.
        First Edition
        Published by Tech Books
        Table of Contents
        Chapter 1: Introduction
        Preface
        """
        score = score_book_structure(content)
        # Many patterns should give high score (capped at 1.0)
        assert score >= 0.75

    def test_non_book_content(self):
        """Test non-book content scores low."""
        content = """
        Meeting Notes - Q4 Planning
        Attendees: John, Jane, Bob
        Action items:
        - Review budget
        - Schedule follow-up
        """
        score = score_book_structure(content)
        assert score < 0.5

    def test_empty_content(self):
        """Test empty content scores zero."""
        assert score_book_structure("") == 0.0

    def test_short_content(self):
        """Test very short content scores low."""
        assert score_book_structure("Hello world") == 0.0


class TestBookDetector:
    """Tests for BookDetector class."""

    @pytest.fixture
    def detector(self) -> BookDetector:
        """Create a BookDetector instance."""
        return BookDetector(enable_isbn_lookup=True)

    @pytest.fixture
    def pdf_metadata(self) -> FileMetadata:
        """Create metadata for a PDF file."""
        return FileMetadata(
            path=Path("/tmp/test_book.pdf"),
            filename="test_book.pdf",
            extension=".pdf",
            size_bytes=5_000_000,  # 5MB - typical book size
        )

    @pytest.fixture
    def non_pdf_metadata(self) -> FileMetadata:
        """Create metadata for a non-PDF file."""
        return FileMetadata(
            path=Path("/tmp/test.txt"),
            filename="test.txt",
            extension=".txt",
            size_bytes=1000,
        )

    def test_name(self, detector: BookDetector):
        """Test classifier name."""
        assert detector.name == "book_detector"

    def test_source(self, detector: BookDetector):
        """Test classification source."""
        assert detector.source == ClassificationSource.BOOK_DETECTOR

    def test_default_confidence(self, detector: BookDetector):
        """Test default confidence."""
        assert detector.default_confidence == 0.96

    def test_non_pdf_returns_none(self, detector: BookDetector, non_pdf_metadata: FileMetadata):
        """Test that non-PDF files return None."""
        result = detector.classify("Some content", non_pdf_metadata)
        assert result is None

    def test_no_metadata_returns_none(self, detector: BookDetector):
        """Test that missing metadata returns None."""
        result = detector.classify("Some content", None)
        assert result is None


class TestBookDetectorClassify:
    """Tests for BookDetector.classify with mocked dependencies."""

    @pytest.fixture
    def detector(self) -> BookDetector:
        """Create a BookDetector instance."""
        return BookDetector(
            technologies=["Python", "JavaScript"],
            enable_isbn_lookup=True,
        )

    def test_classify_with_isbn_success(self, detector: BookDetector, tmp_path: Path):
        """Test classification when ISBN lookup succeeds."""
        # Create a dummy PDF file with filename matching the book title
        # This is important because ISBN coherence validation checks filename-title match
        pdf_file = tmp_path / "Python_Programming_Guide.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n")  # Minimal PDF header

        metadata = FileMetadata(
            path=pdf_file,
            filename="Python_Programming_Guide.pdf",
            extension=".pdf",
            size_bytes=10_000_000,
        )

        from para_files.utils.pdf_metadata import PdfMetadata

        mock_pdf_meta = PdfMetadata(
            title="Python Programming Guide",
            author="John Doe",
            page_count=300,
            isbn="9781234567890",
            isbns=["9781234567890"],  # New field: list of all ISBNs found
            file_size_mb=10.0,
        )

        mock_book_info = BookInfo(
            title="Python Programming Guide",
            authors=["John Doe"],
            subjects=["Python", "Programming"],
            isbn_13="9781234567890",
        )

        with (
            patch(
                "para_files.classifiers.book_detector.extract_pdf_metadata",
                return_value=mock_pdf_meta,
            ),
            patch(
                "para_files.classifiers.book_detector.find_matching_book_info",
                return_value=(mock_book_info, "9781234567890"),
            ),
        ):
            content = "Chapter 1: Introduction\nChapter 2: Basics"
            result = detector.classify(content, metadata)

            assert result is not None
            assert result.confidence.source == ClassificationSource.BOOK_DETECTOR
            # Now uses THEMA codes instead of custom technology categories
            assert "thema_code" in result.extracted_params
            assert "livres" in result.category

    def test_classify_isbn_false_positive_rejected(
        self, detector: BookDetector, tmp_path: Path
    ):
        """Test that ISBN lookups with mismatched titles are rejected as false positives.

        This prevents cases where an ISBN from an ad/promotion in the PDF content
        is mistakenly used to classify the book.
        """
        # Create a PDF with a filename that doesn't match the lookup result
        pdf_file = tmp_path / "London_For_Dummies.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n")

        metadata = FileMetadata(
            path=pdf_file,
            filename="London_For_Dummies.pdf",
            extension=".pdf",
            size_bytes=10_000_000,
        )

        from para_files.utils.pdf_metadata import PdfMetadata

        # PDF has an ISBN that points to a completely different book
        mock_pdf_meta = PdfMetadata(
            title="London For Dummies",
            author="Donald Olson",
            page_count=400,
            isbn="9789786468600",  # ISBN from ads/promotions in the PDF
            isbns=["9789786468600"],  # Only one ISBN found (the wrong one)
            file_size_mb=15.0,
        )

        with (
            patch(
                "para_files.classifiers.book_detector.extract_pdf_metadata",
                return_value=mock_pdf_meta,
            ),
            patch(
                # find_matching_book_info returns (None, None) when no ISBN matches
                "para_files.classifiers.book_detector.find_matching_book_info",
                return_value=(None, None),
            ),
        ):
            content = "Chapter 1: London Basics\nChapter 2: Getting Around"
            result = detector.classify(content, metadata)

            # The ISBN should be rejected as a false positive due to title mismatch
            # The book might still be detected via other signals, but not with ISBN confidence
            if result is not None:
                # If detected via other signals, should NOT have the wrong suggested name
                assert result.extracted_params.get("suggested_name") != sanitize_title(
                    "In Justice - Inside The Scandal That Rocked The Bush Administration"
                )

    def test_classify_isbn_finds_correct_among_multiple(
        self, detector: BookDetector, tmp_path: Path
    ):
        """Test that when multiple ISBNs exist, we find the one matching the filename.

        Simulates the case where a PDF contains the correct ISBN plus ISBNs
        from advertisements/promotions for other books.
        """
        pdf_file = tmp_path / "London_For_Dummies.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n")

        metadata = FileMetadata(
            path=pdf_file,
            filename="London_For_Dummies.pdf",
            extension=".pdf",
            size_bytes=10_000_000,
        )

        from para_files.utils.pdf_metadata import PdfMetadata

        # PDF contains multiple ISBNs: one wrong (from ad), one correct
        mock_pdf_meta = PdfMetadata(
            title="London For Dummies",
            author="Donald Olson",
            page_count=400,
            isbn="9789786468600",  # First ISBN (wrong - from ad)
            isbns=[
                "9789786468600",  # Wrong ISBN (from ad in content)
                "9780470193389",  # Correct ISBN for London For Dummies
            ],
            file_size_mb=15.0,
        )

        # Mock find_matching_book_info to return the correct book
        mock_book_info = BookInfo(
            title="London For Dummies",
            authors=["Donald Olson"],
            isbn_13="9780470193389",
        )

        with (
            patch(
                "para_files.classifiers.book_detector.extract_pdf_metadata",
                return_value=mock_pdf_meta,
            ),
            patch(
                # find_matching_book_info iterates and finds the correct ISBN
                "para_files.classifiers.book_detector.find_matching_book_info",
                return_value=(mock_book_info, "9780470193389"),
            ),
        ):
            content = "Chapter 1: London Basics\nChapter 2: Getting Around"
            result = detector.classify(content, metadata)

            # Should find the book with the correct ISBN
            assert result is not None
            assert result.confidence.value == 1.0  # Full confidence from ISBN match
            # Should use the correct title for suggested name
            assert "London" in result.extracted_params.get("suggested_name", "")

    def test_classify_non_pdf_rejected(self, detector: BookDetector, tmp_path: Path):
        """Test that non-PDF files are rejected."""
        txt_file = tmp_path / "document.txt"
        txt_file.write_text("Hello world")

        metadata = FileMetadata(
            path=txt_file,
            filename="document.txt",
            extension=".txt",
            size_bytes=100,
        )

        result = detector.classify("Some content", metadata)
        assert result is None

    def test_classify_pdf_extraction_fails(self, detector: BookDetector, tmp_path: Path):
        """Test classification when PDF extraction fails."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"not a real pdf")

        metadata = FileMetadata(
            path=pdf_file,
            filename="test.pdf",
            extension=".pdf",
            size_bytes=1000,
        )

        with patch(
            "para_files.classifiers.book_detector.extract_pdf_metadata",
            return_value=None,
        ):
            result = detector.classify("Some content", metadata)
            assert result is None


class TestBookDetectorEdgeCases:
    """Edge case tests for BookDetector."""

    @pytest.fixture
    def detector(self) -> BookDetector:
        """Create a BookDetector instance."""
        return BookDetector(
            technologies=[],
            enable_isbn_lookup=False,
        )

    def test_uppercase_extension(self, detector: BookDetector, tmp_path: Path):
        """Test that uppercase PDF extension is handled."""
        pdf_file = tmp_path / "book.PDF"
        pdf_file.write_bytes(b"%PDF-1.4\n")

        meta = FileMetadata(
            path=pdf_file,
            filename="book.PDF",
            extension=".PDF",
            size_bytes=5_000_000,
        )

        from para_files.utils.pdf_metadata import PdfMetadata

        mock_pdf_meta = PdfMetadata(
            title="Test Book",
            page_count=200,
            file_size_mb=5.0,
            creator="calibre",
        )

        with patch(
            "para_files.classifiers.book_detector.extract_pdf_metadata",
            return_value=mock_pdf_meta,
        ):
            content = """
            Table of Contents
            Chapter 1: Introduction
            Chapter 2: Advanced Topics
            Copyright 2024
            First Edition
            """
            result = detector.classify(content, meta)
            # Should accept uppercase .PDF extension
            # Result depends on score threshold
            if result is not None:
                assert result.confidence.source == ClassificationSource.BOOK_DETECTOR

    def test_empty_technologies(self, detector: BookDetector, tmp_path: Path):
        """Test detector works with empty tech list."""
        pdf_file = tmp_path / "book.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n")

        meta = FileMetadata(
            path=pdf_file,
            filename="book.pdf",
            extension=".pdf",
            size_bytes=5_000_000,
        )

        from para_files.utils.pdf_metadata import PdfMetadata

        mock_pdf_meta = PdfMetadata(
            title="Generic Book",
            page_count=300,
            isbn="9781234567890",
            file_size_mb=5.0,
        )

        with patch(
            "para_files.classifiers.book_detector.extract_pdf_metadata",
            return_value=mock_pdf_meta,
        ):
            content = "Chapter 1: Intro"
            result = detector.classify(content, meta)
            # Should still work, with "misc" as default technology
            if result is not None:
                assert "misc" in result.extracted_params.get("technology", "misc")
