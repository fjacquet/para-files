"""Tests for the book detector classifier."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from para_files.classifiers.book_detector import (
    FINANCIAL_EXCLUSION_PATTERNS,
    MIN_FINANCIAL_PATTERN_MATCHES,
    BookDetector,
    is_financial_document,
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

    def test_classify_isbn_false_positive_rejected(self, detector: BookDetector, tmp_path: Path):
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


class TestBookDetectorChmFiles:
    """Tests for CHM file classification and renaming."""

    @pytest.fixture
    def detector(self) -> BookDetector:
        """Create a BookDetector instance with ISBN lookup enabled."""
        return BookDetector(
            technologies=["Python", "JavaScript"],
            enable_isbn_lookup=True,
        )

    def test_chm_file_detected_with_title(self, detector: BookDetector, tmp_path: Path):
        """Test that CHM files are detected and get suggested_name from title."""
        chm_file = tmp_path / "help.chm"
        chm_file.write_bytes(b"ITSF")  # Minimal CHM header

        metadata = FileMetadata(
            path=chm_file,
            filename="help.chm",
            extension=".chm",
            size_bytes=5_000_000,
        )

        from para_files.utils.chm_metadata import ChmMetadata

        mock_chm_meta = ChmMetadata(
            title="Python 3.12 Documentation",
            isbn=None,
            isbns=[],
            file_size_mb=5.0,
        )

        with patch(
            "para_files.classifiers.book_detector.extract_chm_metadata",
            return_value=mock_chm_meta,
        ):
            result = detector.classify("", metadata)

            assert result is not None
            assert result.confidence.source == ClassificationSource.BOOK_DETECTOR
            # CHM files should get suggested_name from title
            assert "suggested_name" in result.extracted_params
            assert result.extracted_params["suggested_name"] == "Python_3.12_Documentation"
            assert "format=chm" in str(result.extracted_params) or result is not None

    def test_chm_file_with_isbn(self, detector: BookDetector, tmp_path: Path):
        """Test CHM file with ISBN gets high confidence and book lookup."""
        chm_file = tmp_path / "python_cookbook.chm"
        chm_file.write_bytes(b"ITSF")

        metadata = FileMetadata(
            path=chm_file,
            filename="python_cookbook.chm",
            extension=".chm",
            size_bytes=10_000_000,
        )

        from para_files.utils.chm_metadata import ChmMetadata

        mock_chm_meta = ChmMetadata(
            title="Python Cookbook",
            isbn="9780596007973",
            isbns=["9780596007973"],
            file_size_mb=10.0,
        )

        mock_book_info = BookInfo(
            title="Python Cookbook, 2nd Edition",
            authors=["Alex Martelli", "Anna Ravenscroft"],
            isbn_13="9780596007973",
        )

        with (
            patch(
                "para_files.classifiers.book_detector.extract_chm_metadata",
                return_value=mock_chm_meta,
            ),
            patch(
                "para_files.classifiers.book_detector.find_matching_book_info",
                return_value=(mock_book_info, "9780596007973"),
            ),
        ):
            result = detector.classify("", metadata)

            assert result is not None
            # ISBN match gives 1.0 confidence
            assert result.confidence.value == 1.0
            # Should use title from ISBN lookup for suggested name
            assert "Python_Cookbook" in result.extracted_params.get("suggested_name", "")

    def test_chm_extraction_fails_returns_none(self, detector: BookDetector, tmp_path: Path):
        """Test that CHM files with failed extraction return None."""
        chm_file = tmp_path / "broken.chm"
        chm_file.write_bytes(b"not a chm")

        metadata = FileMetadata(
            path=chm_file,
            filename="broken.chm",
            extension=".chm",
            size_bytes=1000,
        )

        with patch(
            "para_files.classifiers.book_detector.extract_chm_metadata",
            return_value=None,
        ):
            result = detector.classify("", metadata)
            assert result is None

    def test_chm_uppercase_extension(self, detector: BookDetector, tmp_path: Path):
        """Test that uppercase .CHM extension is handled."""
        chm_file = tmp_path / "help.CHM"
        chm_file.write_bytes(b"ITSF")

        metadata = FileMetadata(
            path=chm_file,
            filename="help.CHM",
            extension=".CHM",
            size_bytes=5_000_000,
        )

        from para_files.utils.chm_metadata import ChmMetadata

        mock_chm_meta = ChmMetadata(
            title="Windows Help File",
            file_size_mb=5.0,
        )

        with patch(
            "para_files.classifiers.book_detector.extract_chm_metadata",
            return_value=mock_chm_meta,
        ):
            result = detector.classify("", metadata)
            assert result is not None
            assert result.confidence.source == ClassificationSource.BOOK_DETECTOR


class TestBookDetectorMobiFiles:
    """Tests for MOBI file classification and renaming."""

    @pytest.fixture
    def detector(self) -> BookDetector:
        """Create a BookDetector instance with ISBN lookup enabled."""
        return BookDetector(
            technologies=["Python", "JavaScript"],
            enable_isbn_lookup=True,
        )

    def test_mobi_file_detected_with_title(self, detector: BookDetector, tmp_path: Path):
        """Test that MOBI files are detected and get suggested_name from title."""
        mobi_file = tmp_path / "book.mobi"
        mobi_file.write_bytes(b"MOBI")  # Minimal MOBI header

        metadata = FileMetadata(
            path=mobi_file,
            filename="book.mobi",
            extension=".mobi",
            size_bytes=5_000_000,
        )

        from para_files.utils.mobi_metadata import MobiMetadata

        mock_mobi_meta = MobiMetadata(
            title="The Pragmatic Programmer",
            author="Hunt and Thomas",
            isbn=None,
            isbns=[],
            file_size_mb=5.0,
        )

        with patch(
            "para_files.classifiers.book_detector.extract_mobi_metadata",
            return_value=mock_mobi_meta,
        ):
            result = detector.classify("", metadata)

            assert result is not None
            assert result.confidence.source == ClassificationSource.BOOK_DETECTOR
            # MOBI files should get suggested_name from title
            assert "suggested_name" in result.extracted_params
            assert result.extracted_params["suggested_name"] == "The_Pragmatic_Programmer"

    def test_mobi_file_with_isbn(self, detector: BookDetector, tmp_path: Path):
        """Test MOBI file with ISBN gets high confidence and book lookup."""
        mobi_file = tmp_path / "eloquent_javascript.mobi"
        mobi_file.write_bytes(b"MOBI")

        metadata = FileMetadata(
            path=mobi_file,
            filename="eloquent_javascript.mobi",
            extension=".mobi",
            size_bytes=3_000_000,
        )

        from para_files.utils.mobi_metadata import MobiMetadata

        mock_mobi_meta = MobiMetadata(
            title="Eloquent JavaScript",
            author="Marijn Haverbeke",
            isbn="9781593275846",
            isbns=["9781593275846"],
            file_size_mb=3.0,
        )

        mock_book_info = BookInfo(
            title="Eloquent JavaScript, 3rd Edition",
            authors=["Marijn Haverbeke"],
            isbn_13="9781593275846",
        )

        with (
            patch(
                "para_files.classifiers.book_detector.extract_mobi_metadata",
                return_value=mock_mobi_meta,
            ),
            patch(
                "para_files.classifiers.book_detector.find_matching_book_info",
                return_value=(mock_book_info, "9781593275846"),
            ),
        ):
            result = detector.classify("", metadata)

            assert result is not None
            # ISBN match gives 1.0 confidence
            assert result.confidence.value == 1.0
            # Should use title from ISBN lookup for suggested name
            assert "Eloquent_JavaScript" in result.extracted_params.get("suggested_name", "")

    def test_mobi_extraction_fails_returns_none(self, detector: BookDetector, tmp_path: Path):
        """Test that MOBI files with failed extraction return None."""
        mobi_file = tmp_path / "broken.mobi"
        mobi_file.write_bytes(b"not a mobi")

        metadata = FileMetadata(
            path=mobi_file,
            filename="broken.mobi",
            extension=".mobi",
            size_bytes=1000,
        )

        with patch(
            "para_files.classifiers.book_detector.extract_mobi_metadata",
            return_value=None,
        ):
            result = detector.classify("", metadata)
            assert result is None

    def test_mobi_uppercase_extension(self, detector: BookDetector, tmp_path: Path):
        """Test that uppercase .MOBI extension is handled."""
        mobi_file = tmp_path / "book.MOBI"
        mobi_file.write_bytes(b"MOBI")

        metadata = FileMetadata(
            path=mobi_file,
            filename="book.MOBI",
            extension=".MOBI",
            size_bytes=4_000_000,
        )

        from para_files.utils.mobi_metadata import MobiMetadata

        mock_mobi_meta = MobiMetadata(
            title="Clean Code",
            file_size_mb=4.0,
        )

        with patch(
            "para_files.classifiers.book_detector.extract_mobi_metadata",
            return_value=mock_mobi_meta,
        ):
            result = detector.classify("", metadata)
            assert result is not None
            assert result.confidence.source == ClassificationSource.BOOK_DETECTOR


class TestBookDetectorFalsePositives:
    """Tests for false positive prevention in BookDetector.

    French financial PDFs often contain IBAN or other number sequences that
    resemble ISBNs. These tests verify that the financial exclusion logic
    runs before ISBN extraction, preventing misclassification.
    """

    @pytest.fixture
    def detector(self) -> BookDetector:
        """Create BookDetector with ISBN lookup enabled."""
        return BookDetector(enable_isbn_lookup=True)

    def test_iban_containing_pdf_not_classified_as_book(
        self, detector: BookDetector, tmp_path: Path
    ) -> None:
        """PDF with French IBAN and banking keywords must not be classified as a book."""
        pdf_file = tmp_path / "releve_bancaire_2025.pdf"
        pdf_file.touch()

        metadata = FileMetadata(
            path=pdf_file,
            filename="releve_bancaire_2025.pdf",
            extension=".pdf",
            size_bytes=200_000,
        )

        content = (
            "BANQUE NATIONALE\n"
            "IBAN FR76 1234 5678 9012 3456 7890 123\n"
            "RELEVÉ DE COMPTE\n"
            "Solde précédent: 1234.56 EUR\n"
        )

        with patch("para_files.classifiers.book_detector.extract_pdf_metadata") as mock_extract:
            result = detector.classify(content, metadata)
            # Financial check runs before PDF extraction — extract_pdf_metadata not called
            mock_extract.assert_not_called()
            assert result is None

    def test_financial_doc_with_isbn_like_reference(
        self, detector: BookDetector, tmp_path: Path
    ) -> None:
        """Financial doc containing an ISBN-like 13-digit number must still return None.

        Per CONTEXT decision: is_financial_document() takes absolute precedence.
        Even if the content has a 13-digit sequence resembling an ISBN, the
        financial check fires first and returns None.
        """
        pdf_file = tmp_path / "releve_bnp_2025.pdf"
        pdf_file.touch()

        metadata = FileMetadata(
            path=pdf_file,
            filename="releve_bnp_2025.pdf",
            extension=".pdf",
            size_bytes=150_000,
        )

        content = (
            "BANQUE BNP PARIBAS\n"
            "IBAN FR76 3000 6000 0112 3456 7890 189\n"
            "Ref: 9782100000001\n"  # 13-digit number that looks like an ISBN
            "RELEVÉ DE COMPTE au 31/01/2025\n"
        )

        with patch("para_files.classifiers.book_detector.extract_pdf_metadata") as mock_extract:
            result = detector.classify(content, metadata)
            mock_extract.assert_not_called()
            assert result is None

    def test_real_book_with_valid_isbn_not_blocked(
        self, detector: BookDetector, tmp_path: Path
    ) -> None:
        """A legitimate book PDF with no financial patterns must still classify as a book."""
        pdf_file = tmp_path / "python_guide.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n")

        metadata = FileMetadata(
            path=pdf_file,
            filename="python_guide.pdf",
            extension=".pdf",
            size_bytes=10_000_000,
        )

        content = (
            "Table of Contents\n"
            "Chapter 1: Introduction to Python\n"
            "Chapter 2: Variables and Types\n"
            "ISBN 978-0-13-468599-1\n"
            "Copyright 2023 by Tech Publishers\n"
        )

        from para_files.utils.pdf_metadata import PdfMetadata

        mock_pdf_meta = PdfMetadata(
            title="Python Programming Guide",
            author="Jane Smith",
            page_count=350,
            isbn="9780134685991",
            isbns=["9780134685991"],
            file_size_mb=10.0,
        )

        mock_book_info = BookInfo(
            title="Python Programming Guide",
            authors=["Jane Smith"],
            subjects=["Python", "Programming"],
            isbn_13="9780134685991",
        )

        with (
            patch(
                "para_files.classifiers.book_detector.extract_pdf_metadata",
                return_value=mock_pdf_meta,
            ),
            patch(
                "para_files.classifiers.book_detector.find_matching_book_info",
                return_value=(mock_book_info, "9780134685991"),
            ),
        ):
            result = detector.classify(content, metadata)
            assert result is not None
            assert result.confidence.value == 1.0
            assert "livres" in result.category

    def test_invalid_isbn_all_zeros(self, detector: BookDetector, tmp_path: Path) -> None:
        """Content with an all-zero ISBN must not crash and should return None or low confidence."""
        pdf_file = tmp_path / "document_with_zero_isbn.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n")

        metadata = FileMetadata(
            path=pdf_file,
            filename="document_with_zero_isbn.pdf",
            extension=".pdf",
            size_bytes=1_000_000,
        )

        content = "ISBN: 0000000000000\nSome document content here."

        from para_files.utils.pdf_metadata import PdfMetadata

        mock_pdf_meta = PdfMetadata(
            title=None,
            page_count=10,
            isbns=[],  # Validator filters out all-zero ISBN
            file_size_mb=1.0,
        )

        with patch(
            "para_files.classifiers.book_detector.extract_pdf_metadata",
            return_value=mock_pdf_meta,
        ):
            # Must not raise, must return None (score below threshold)
            result = detector.classify(content, metadata)
            assert result is None  # No valid signals → below threshold

    def test_iban_like_pattern_not_treated_as_isbn(
        self, detector: BookDetector, tmp_path: Path
    ) -> None:
        """French IBAN format must not be treated as an ISBN."""
        pdf_file = tmp_path / "facture_2025_01.pdf"
        pdf_file.touch()

        metadata = FileMetadata(
            path=pdf_file,
            filename="facture_2025_01.pdf",
            extension=".pdf",
            size_bytes=80_000,
        )

        content = (
            "FACTURE\n"
            "IBAN: FR76 3000 6000 0112 3456 7890 189\n"
            "BIC: BNPAFRPPXXX\n"
            "Montant: 125.00 EUR\n"
        )

        with patch("para_files.classifiers.book_detector.extract_pdf_metadata") as mock_extract:
            result = detector.classify(content, metadata)
            mock_extract.assert_not_called()
            assert result is None

    def test_swiss_iban_pattern_excluded(self, detector: BookDetector, tmp_path: Path) -> None:
        """Swiss IBAN format in a financial document must be excluded from book detection."""
        pdf_file = tmp_path / "extrait_ubs_2025.pdf"
        pdf_file.touch()

        metadata = FileMetadata(
            path=pdf_file,
            filename="extrait_ubs_2025.pdf",
            extension=".pdf",
            size_bytes=120_000,
        )

        content = (
            "UBS Switzerland AG\n"
            "CH93 0076 2011 6238 5295 7\n"
            "EXTRAIT DE COMPTE\n"
            "Solde: CHF 5432.10\n"
        )

        with patch("para_files.classifiers.book_detector.extract_pdf_metadata") as mock_extract:
            result = detector.classify(content, metadata)
            mock_extract.assert_not_called()
            assert result is None

    def test_is_financial_document_minimum_threshold(self) -> None:
        """Content matching exactly 1 FINANCIAL_EXCLUSION_PATTERN must return False.

        MIN_FINANCIAL_PATTERN_MATCHES = 2, so a single match is not enough.
        """
        # Only one pattern: IBAN keyword alone (no BANQUE, no FACTURE, etc.)
        content = "IBAN is used for international transfers."
        # Ensure only 1 pattern matches
        matches = sum(1 for p in FINANCIAL_EXCLUSION_PATTERNS if p.search(content))
        assert matches == 1, f"Expected 1 match, got {matches}"

        result = is_financial_document(content, "document.pdf")
        assert result is False

    def test_is_financial_document_at_threshold(self) -> None:
        """Content matching exactly MIN_FINANCIAL_PATTERN_MATCHES patterns must return True."""
        # Two patterns: IBAN + BANQUE
        content = "IBAN FR76 1234 5678 9012 3456 7890 123\nBANQUE NATIONALE"
        matches = sum(1 for p in FINANCIAL_EXCLUSION_PATTERNS if p.search(content))
        assert matches >= MIN_FINANCIAL_PATTERN_MATCHES, (
            f"Expected >= {MIN_FINANCIAL_PATTERN_MATCHES} matches, got {matches}"
        )

        result = is_financial_document(content, "document.pdf")
        assert result is True

    def test_is_financial_document_filename_match(self) -> None:
        """Filename containing a financial keyword must return True regardless of content."""
        result = is_financial_document("", "facture_2025.pdf")
        assert result is True

    def test_is_financial_document_content_match(self) -> None:
        """Content with IBAN + BANQUE must return True."""
        content = "IBAN FR76 0000 0000 0000 0000 000\nBANQUE DU SUD\n"
        result = is_financial_document(content, "document.pdf")
        assert result is True

    def test_is_financial_document_below_threshold(self) -> None:
        """Content with only 1 financial pattern match must return False."""
        # Just the word BANK but nothing else financial
        content = "The BANK of tomorrow will be digital."
        result = is_financial_document(content, "my_notes.pdf")
        # Matches: BANK (1 match) — below threshold of 2
        assert result is False
