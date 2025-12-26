"""Tests for ISBN lookup utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from para_files.utils.isbn_lookup import (
    BookInfo,
    infer_technology_from_subjects,
    isbn_to_isbn13,
    lookup_isbn,
    normalize_isbn,
    validate_isbn,
)


class TestValidateIsbn:
    """Tests for validate_isbn function."""

    def test_valid_isbn13(self):
        """Test valid ISBN-13."""
        # 978-0-596-51774-8 is a valid ISBN
        assert validate_isbn("9780596517748") is True

    def test_valid_isbn13_with_dashes(self):
        """Test valid ISBN-13 with dashes."""
        assert validate_isbn("978-0-596-51774-8") is True

    def test_valid_isbn10(self):
        """Test valid ISBN-10."""
        # 0-596-51774-2 (Python Cookbook)
        assert validate_isbn("0596517742") is True

    def test_valid_isbn10_with_x(self):
        """Test valid ISBN-10 with X checksum."""
        # 155860832X (The Design of the UNIX Operating System) has X checksum
        assert validate_isbn("155860832X") is True

    def test_wrong_length(self):
        """Test ISBN with wrong length."""
        assert validate_isbn("123456") is False

    def test_non_numeric(self):
        """Test non-numeric string."""
        assert validate_isbn("not-an-isbn") is False

    def test_empty_string(self):
        """Test empty string."""
        assert validate_isbn("") is False


class TestNormalizeIsbn:
    """Tests for normalize_isbn function."""

    def test_remove_dashes(self):
        """Test removing dashes from ISBN."""
        result = normalize_isbn("978-1-234567-89-0")
        assert result is not None
        assert "-" not in result

    def test_remove_spaces(self):
        """Test removing spaces from ISBN."""
        result = normalize_isbn("978 0 596 51774 8")
        assert result is not None
        assert " " not in result

    def test_already_normalized(self):
        """Test already normalized ISBN."""
        assert normalize_isbn("9780596517748") == "9780596517748"

    def test_invalid_returns_none(self):
        """Test invalid ISBN returns None."""
        result = normalize_isbn("invalid")
        # May return None or empty string depending on isbnlib behavior
        assert result is None or result == ""


class TestIsbnToIsbn13:
    """Tests for isbn_to_isbn13 function."""

    def test_convert_isbn10_to_isbn13(self):
        """Test converting ISBN-10 to ISBN-13."""
        result = isbn_to_isbn13("0596517742")
        assert result is not None
        assert len(result) == 13
        assert result.startswith("978")

    def test_isbn13_unchanged(self):
        """Test that ISBN-13 is returned unchanged."""
        result = isbn_to_isbn13("9780596517748")
        assert result == "9780596517748"

    def test_invalid_isbn_returns_none(self):
        """Test that invalid ISBN returns None."""
        result = isbn_to_isbn13("invalid")
        assert result is None


class TestInferTechnologyFromSubjects:
    """Tests for infer_technology_from_subjects function."""

    def test_python_subject_match(self):
        """Test inferring Python from subjects."""
        subjects = ["Python programming", "Computer Science"]
        known = ["Python", "Java", "JavaScript"]
        result = infer_technology_from_subjects(subjects, known)
        assert result == "Python"

    def test_javascript_subject_match(self):
        """Test inferring JavaScript from subjects."""
        subjects = ["JavaScript", "Web Development"]
        known = ["Python", "JavaScript", "Java"]
        result = infer_technology_from_subjects(subjects, known)
        assert result == "JavaScript"

    def test_no_match_returns_none(self):
        """Test no match returns None."""
        subjects = ["Fiction", "Novel", "Literature"]
        known = ["Python", "Java", "JavaScript"]
        result = infer_technology_from_subjects(subjects, known)
        assert result is None

    def test_empty_subjects(self):
        """Test empty subjects list."""
        result = infer_technology_from_subjects([], ["Python", "Java"])
        assert result is None

    def test_empty_known_technologies(self):
        """Test empty known technologies."""
        result = infer_technology_from_subjects(["Python"], [])
        assert result is None

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        subjects = ["PYTHON PROGRAMMING"]
        known = ["Python", "Java"]
        result = infer_technology_from_subjects(subjects, known)
        assert result == "Python"

    def test_common_mapping_machine_learning(self):
        """Test common subject mapping for machine learning."""
        subjects = ["machine learning", "artificial intelligence"]
        known = ["AI", "Python", "Java"]
        result = infer_technology_from_subjects(subjects, known)
        assert result == "AI"

    def test_common_mapping_kubernetes(self):
        """Test common subject mapping for Kubernetes."""
        subjects = ["kubernetes"]
        known = ["Kubernetes", "Docker", "Cloud"]
        result = infer_technology_from_subjects(subjects, known)
        assert result == "Kubernetes"


class TestBookInfo:
    """Tests for BookInfo dataclass."""

    def test_create_default_book_info(self):
        """Test creating BookInfo with defaults."""
        info = BookInfo()
        assert info.title is None
        assert info.authors == []
        assert info.publishers == []
        assert info.publish_date is None
        assert info.subjects == []
        assert info.isbn_10 is None
        assert info.isbn_13 is None
        assert info.language is None
        assert info.description is None
        assert info.cover_url is None

    def test_create_full_book_info(self):
        """Test creating BookInfo with all fields."""
        info = BookInfo(
            title="Python Programming Guide",
            authors=["John Doe", "Jane Smith"],
            publishers=["Tech Books Inc"],
            publish_date="2024",
            subjects=["Python", "Programming", "Computer Science"],
            isbn_10="0596517742",
            isbn_13="9780596517748",
            language="en",
            description="A comprehensive guide to Python programming.",
            cover_url="https://example.com/cover.jpg",
        )
        assert info.title == "Python Programming Guide"
        assert len(info.authors) == 2
        assert info.publish_date == "2024"
        assert "Python" in info.subjects
        assert info.isbn_13 == "9780596517748"

    def test_book_info_with_single_author(self):
        """Test BookInfo with single author."""
        info = BookInfo(
            title="Solo Author Book",
            authors=["Single Author"],
        )
        assert len(info.authors) == 1
        assert info.authors[0] == "Single Author"


class TestLookupIsbn:
    """Tests for lookup_isbn function."""

    def test_lookup_invalid_isbn_returns_none(self):
        """Test lookup with clearly invalid ISBN returns None."""
        result = lookup_isbn("invalid")
        assert result is None

    def test_lookup_empty_string_returns_none(self):
        """Test lookup with empty string returns None."""
        result = lookup_isbn("")
        assert result is None

    def test_lookup_with_valid_isbn_structure(self):
        """Test lookup with valid ISBN structure (may or may not find book)."""
        # 9780596517748 is Python Cookbook - valid ISBN
        # This test verifies the function runs without error
        # The actual result depends on network/API availability
        result = lookup_isbn("9780596517748")
        # Just verify no exception and returns BookInfo or None
        assert result is None or isinstance(result, BookInfo)
