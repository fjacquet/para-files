"""Tests for ISBN lookup utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from para_files.utils.isbn_lookup import (
    BookInfo,
    _extract_subjects_from_description,
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

    def test_lookup_isbnlib_not_available(self):
        """Test lookup when isbnlib is not installed."""
        import builtins
        import sys

        # Save originals
        isbnlib_backup = sys.modules.get("isbnlib")
        original_import = builtins.__import__

        try:
            # Remove isbnlib from modules
            if "isbnlib" in sys.modules:
                del sys.modules["isbnlib"]

            def mock_import(name, *args, **kwargs):
                if name == "isbnlib":
                    raise ImportError(name)
                return original_import(name, *args, **kwargs)

            builtins.__import__ = mock_import
            result = lookup_isbn("9780596517748")
            assert result is None
        finally:
            builtins.__import__ = original_import
            if isbnlib_backup:
                sys.modules["isbnlib"] = isbnlib_backup

    @patch("isbnlib.canonical")
    def test_lookup_invalid_canonical(self, mock_canonical: MagicMock):
        """Test lookup when canonical returns empty string."""
        mock_canonical.return_value = ""
        result = lookup_isbn("9780596517748")
        assert result is None

    @patch("isbnlib.canonical")
    @patch("isbnlib.is_isbn10")
    @patch("isbnlib.is_isbn13")
    def test_lookup_validation_failed(
        self,
        mock_is_isbn13: MagicMock,
        mock_is_isbn10: MagicMock,
        mock_canonical: MagicMock,
    ):
        """Test lookup when ISBN validation fails."""
        mock_canonical.return_value = "1234567890"
        mock_is_isbn10.return_value = False
        mock_is_isbn13.return_value = False
        result = lookup_isbn("1234567890")
        assert result is None

    @patch("isbnlib.canonical")
    @patch("isbnlib.is_isbn10")
    @patch("isbnlib.is_isbn13")
    @patch("isbnlib.to_isbn13")
    @patch("isbnlib.meta")
    def test_lookup_no_metadata_found(
        self,
        mock_meta: MagicMock,
        mock_to_isbn13: MagicMock,
        mock_is_isbn13: MagicMock,
        mock_is_isbn10: MagicMock,
        mock_canonical: MagicMock,
    ):
        """Test lookup when no metadata is found from any service."""
        mock_canonical.return_value = "9780596517748"
        mock_is_isbn10.return_value = False
        mock_is_isbn13.return_value = True
        mock_to_isbn13.return_value = "9780596517748"
        mock_meta.return_value = None
        result = lookup_isbn("9780596517748")
        assert result is None

    @patch("isbnlib.canonical")
    @patch("isbnlib.is_isbn10")
    @patch("isbnlib.is_isbn13")
    @patch("isbnlib.to_isbn13")
    @patch("isbnlib.meta")
    @patch("isbnlib.desc")
    @patch("isbnlib.cover")
    def test_lookup_success_with_enrichment(  # noqa: PLR0913
        self,
        mock_cover: MagicMock,
        mock_desc: MagicMock,
        mock_meta: MagicMock,
        mock_to_isbn13: MagicMock,
        mock_is_isbn13: MagicMock,
        mock_is_isbn10: MagicMock,
        mock_canonical: MagicMock,
    ):
        """Test successful lookup with description and cover enrichment."""
        mock_canonical.return_value = "9780596517748"
        mock_is_isbn10.return_value = False
        mock_is_isbn13.return_value = True
        mock_to_isbn13.return_value = "9780596517748"
        mock_meta.return_value = {
            "Title": "Python Cookbook",
            "Authors": ["David Beazley", "Brian K. Jones"],
            "Publisher": "O'Reilly Media",
            "Year": "2013",
            "Language": "en",
        }
        mock_desc.return_value = "A comprehensive guide to Python programming."
        mock_cover.return_value = {"thumbnail": "https://example.com/cover.jpg"}

        result = lookup_isbn("9780596517748")

        assert result is not None
        assert result.title == "Python Cookbook"
        assert len(result.authors) == 2
        assert result.publishers == ["O'Reilly Media"]
        assert result.publish_date == "2013"
        assert result.description is not None
        assert result.cover_url == "https://example.com/cover.jpg"

    @patch("isbnlib.canonical")
    @patch("isbnlib.is_isbn10")
    @patch("isbnlib.is_isbn13")
    @patch("isbnlib.to_isbn13")
    @patch("isbnlib.to_isbn10")
    @patch("isbnlib.meta")
    @patch("isbnlib.desc")
    @patch("isbnlib.cover")
    def test_lookup_isbn10_input(  # noqa: PLR0913
        self,
        mock_cover: MagicMock,
        mock_desc: MagicMock,
        mock_meta: MagicMock,
        mock_to_isbn10: MagicMock,
        mock_to_isbn13: MagicMock,
        mock_is_isbn13: MagicMock,
        mock_is_isbn10: MagicMock,
        mock_canonical: MagicMock,
    ):
        """Test lookup with ISBN-10 input."""
        mock_canonical.return_value = "0596517742"  # 10 chars
        mock_is_isbn10.return_value = True
        mock_is_isbn13.return_value = False
        mock_to_isbn13.return_value = "9780596517748"
        mock_to_isbn10.return_value = "0596517742"
        mock_meta.return_value = {"Title": "Test Book"}
        mock_desc.return_value = None
        mock_cover.return_value = None

        result = lookup_isbn("0596517742")

        assert result is not None
        assert result.isbn_10 == "0596517742"
        assert result.isbn_13 == "9780596517748"

    @patch("isbnlib.canonical")
    @patch("isbnlib.is_isbn10")
    @patch("isbnlib.is_isbn13")
    @patch("isbnlib.to_isbn13")
    @patch("isbnlib.meta")
    @patch("isbnlib.desc")
    @patch("isbnlib.cover")
    def test_lookup_enrichment_failures(  # noqa: PLR0913
        self,
        mock_cover: MagicMock,
        mock_desc: MagicMock,
        mock_meta: MagicMock,
        mock_to_isbn13: MagicMock,
        mock_is_isbn13: MagicMock,
        mock_is_isbn10: MagicMock,
        mock_canonical: MagicMock,
    ):
        """Test lookup when description and cover retrieval fail."""
        mock_canonical.return_value = "9780596517748"
        mock_is_isbn10.return_value = False
        mock_is_isbn13.return_value = True
        mock_to_isbn13.return_value = "9780596517748"
        mock_meta.return_value = {"Title": "Test Book"}
        mock_desc.side_effect = Exception("API error")
        mock_cover.side_effect = Exception("API error")

        result = lookup_isbn("9780596517748")

        assert result is not None
        assert result.title == "Test Book"
        assert result.description is None
        assert result.cover_url is None

    @patch("isbnlib.canonical")
    @patch("isbnlib.is_isbn10")
    @patch("isbnlib.is_isbn13")
    @patch("isbnlib.to_isbn13")
    @patch("isbnlib.meta")
    def test_lookup_specific_service(
        self,
        mock_meta: MagicMock,
        mock_to_isbn13: MagicMock,
        mock_is_isbn13: MagicMock,
        mock_is_isbn10: MagicMock,
        mock_canonical: MagicMock,
    ):
        """Test lookup with specific service parameter."""
        mock_canonical.return_value = "9780596517748"
        mock_is_isbn10.return_value = False
        mock_is_isbn13.return_value = True
        mock_to_isbn13.return_value = "9780596517748"
        mock_meta.return_value = {"Title": "From Google"}

        result = lookup_isbn("9780596517748", service="goob")

        assert result is not None
        mock_meta.assert_called_once()
        # Verify service was passed
        assert mock_meta.call_args.kwargs.get("service") == "goob"

    @patch("isbnlib.canonical")
    @patch("isbnlib.is_isbn10")
    @patch("isbnlib.is_isbn13")
    @patch("isbnlib.to_isbn13")
    @patch("isbnlib.meta")
    def test_lookup_service_fallback(
        self,
        mock_meta: MagicMock,
        mock_to_isbn13: MagicMock,
        mock_is_isbn13: MagicMock,
        mock_is_isbn10: MagicMock,
        mock_canonical: MagicMock,
    ):
        """Test that lookup tries multiple services when default is used."""
        mock_canonical.return_value = "9780596517748"
        mock_is_isbn10.return_value = False
        mock_is_isbn13.return_value = True
        mock_to_isbn13.return_value = "9780596517748"
        # First service fails, second succeeds
        mock_meta.side_effect = [
            Exception("Google failed"),
            {"Title": "From Open Library"},
            None,  # Won't be reached
        ]

        result = lookup_isbn("9780596517748")

        assert result is not None
        assert result.title == "From Open Library"


class TestIsbnErrorDistinction:
    """Tests for transient vs data error distinction in lookup_isbn."""

    @patch("isbnlib.canonical")
    @patch("isbnlib.is_isbn10")
    @patch("isbnlib.is_isbn13")
    @patch("isbnlib.to_isbn13")
    @patch("isbnlib.meta")
    @patch("isbnlib.desc")
    @patch("isbnlib.cover")
    def test_isbn_service_unavailable_retries(  # noqa: PLR0913
        self,
        mock_cover: MagicMock,
        mock_desc: MagicMock,
        mock_meta: MagicMock,
        mock_to_isbn13: MagicMock,
        mock_is_isbn13: MagicMock,
        mock_is_isbn10: MagicMock,
        mock_canonical: MagicMock,
    ):
        """ConnectionError triggers one retry; second call succeeds and returns BookInfo."""
        mock_canonical.return_value = "9780596517748"
        mock_is_isbn10.return_value = False
        mock_is_isbn13.return_value = True
        mock_to_isbn13.return_value = "9780596517748"
        # First call raises ConnectionError, second call succeeds
        mock_meta.side_effect = [
            ConnectionError("network down"),
            {"Title": "Python Cookbook", "Authors": ["David Beazley"]},
        ]
        mock_desc.return_value = None
        mock_cover.return_value = None

        result = lookup_isbn("9780596517748", service="openl")

        assert result is not None
        assert result.title == "Python Cookbook"
        # meta should be called twice (original + 1 retry)
        assert mock_meta.call_count == 2

    @patch("isbnlib.canonical")
    @patch("isbnlib.is_isbn10")
    @patch("isbnlib.is_isbn13")
    @patch("isbnlib.to_isbn13")
    @patch("isbnlib.meta")
    def test_isbn_data_error_no_retry(
        self,
        mock_meta: MagicMock,
        mock_to_isbn13: MagicMock,
        mock_is_isbn13: MagicMock,
        mock_is_isbn10: MagicMock,
        mock_canonical: MagicMock,
    ):
        """ValueError (data error) does not trigger retry — meta called once per service."""
        mock_canonical.return_value = "9780596517748"
        mock_is_isbn10.return_value = False
        mock_is_isbn13.return_value = True
        mock_to_isbn13.return_value = "9780596517748"
        mock_meta.side_effect = ValueError("bad data")

        result = lookup_isbn("9780596517748", service="openl")

        assert result is None
        # Each of the 1 service gets 1 attempt (no retry)
        assert mock_meta.call_count == 1

    @patch("isbnlib.canonical")
    @patch("isbnlib.is_isbn10")
    @patch("isbnlib.is_isbn13")
    @patch("isbnlib.to_isbn13")
    @patch("isbnlib.meta")
    def test_isbn_timeout_logs_warning(
        self,
        mock_meta: MagicMock,
        mock_to_isbn13: MagicMock,
        mock_is_isbn13: MagicMock,
        mock_is_isbn10: MagicMock,
        mock_canonical: MagicMock,
    ):
        """TimeoutError (transient) logs at WARNING level with 'unavailable' in message."""
        from loguru import logger

        log_messages: list[str] = []

        def sink(message: object) -> None:
            log_messages.append(str(message))

        # Add a temporary sink to capture loguru output
        sink_id = logger.add(sink, level="WARNING")
        try:
            mock_canonical.return_value = "9780596517748"
            mock_is_isbn10.return_value = False
            mock_is_isbn13.return_value = True
            mock_to_isbn13.return_value = "9780596517748"
            mock_meta.side_effect = TimeoutError("timed out")

            lookup_isbn("9780596517748", service="openl")
        finally:
            logger.remove(sink_id)

        # At least one warning mentioning "unavailable" should have been logged
        assert any("unavailable" in msg.lower() for msg in log_messages)

    def test_isbn_invalid_returns_none(self):
        """Non-ISBN string returns None immediately."""
        result = lookup_isbn("not-an-isbn")
        assert result is None


class TestExtractSubjectsFromDescription:
    """Tests for _extract_subjects_from_description function."""

    def test_extract_python_keyword(self):
        """Test extracting Python keyword from description."""
        desc = "A comprehensive guide to Python programming."
        subjects = _extract_subjects_from_description(desc)
        assert "Python" in subjects

    def test_extract_multiple_keywords(self):
        """Test extracting multiple keywords."""
        desc = "Learn Docker and Kubernetes for modern cloud deployments."
        subjects = _extract_subjects_from_description(desc)
        assert "Docker" in subjects
        assert "Kubernetes" in subjects
        assert "Cloud" in subjects

    def test_extract_no_keywords(self):
        """Test with text containing no tech keywords."""
        desc = "A story about adventure and friendship."
        subjects = _extract_subjects_from_description(desc)
        assert subjects == []

    def test_extract_case_insensitive(self):
        """Test case-insensitive matching."""
        desc = "PYTHON and JAVASCRIPT programming fundamentals."
        subjects = _extract_subjects_from_description(desc)
        assert "Python" in subjects
        assert "Javascript" in subjects

    def test_extract_machine_learning(self):
        """Test extracting machine learning keywords."""
        desc = "Deep learning and artificial intelligence techniques."
        subjects = _extract_subjects_from_description(desc)
        assert "Deep Learning" in subjects
        assert "Artificial Intelligence" in subjects

    def test_extract_database_keywords(self):
        """Test extracting database-related keywords."""
        desc = "SQL and MongoDB database management."
        subjects = _extract_subjects_from_description(desc)
        assert "Sql" in subjects
        assert "Mongodb" in subjects


class TestValidateIsbnExceptionHandling:
    """Tests for exception handling in validate_isbn."""

    def test_validate_handles_exception(self):
        """Test that validate_isbn handles exceptions gracefully."""
        import builtins
        import sys

        isbnlib_backup = sys.modules.get("isbnlib")
        original_import = builtins.__import__

        try:
            if "isbnlib" in sys.modules:
                del sys.modules["isbnlib"]

            def mock_import(name, *args, **kwargs):
                if name == "isbnlib":
                    raise RuntimeError(name)
                return original_import(name, *args, **kwargs)

            builtins.__import__ = mock_import
            result = validate_isbn("9780596517748")
            assert result is False
        finally:
            builtins.__import__ = original_import
            if isbnlib_backup:
                sys.modules["isbnlib"] = isbnlib_backup


class TestNormalizeIsbnExceptionHandling:
    """Tests for exception handling in normalize_isbn."""

    def test_normalize_handles_exception(self):
        """Test that normalize_isbn handles exceptions gracefully."""
        import builtins
        import sys

        isbnlib_backup = sys.modules.get("isbnlib")
        original_import = builtins.__import__

        try:
            if "isbnlib" in sys.modules:
                del sys.modules["isbnlib"]

            def mock_import(name, *args, **kwargs):
                if name == "isbnlib":
                    raise RuntimeError(name)
                return original_import(name, *args, **kwargs)

            builtins.__import__ = mock_import
            result = normalize_isbn("9780596517748")
            assert result is None
        finally:
            builtins.__import__ = original_import
            if isbnlib_backup:
                sys.modules["isbnlib"] = isbnlib_backup


class TestIsbnToIsbn13ExceptionHandling:
    """Tests for exception handling in isbn_to_isbn13."""

    def test_isbn_to_isbn13_handles_exception(self):
        """Test that isbn_to_isbn13 handles exceptions gracefully."""
        import builtins
        import sys

        isbnlib_backup = sys.modules.get("isbnlib")
        original_import = builtins.__import__

        try:
            if "isbnlib" in sys.modules:
                del sys.modules["isbnlib"]

            def mock_import(name, *args, **kwargs):
                if name == "isbnlib":
                    raise RuntimeError(name)
                return original_import(name, *args, **kwargs)

            builtins.__import__ = mock_import
            result = isbn_to_isbn13("0596517742")
            assert result is None
        finally:
            builtins.__import__ = original_import
            if isbnlib_backup:
                sys.modules["isbnlib"] = isbnlib_backup


class TestInferTechnologyExtended:
    """Extended tests for infer_technology_from_subjects."""

    def test_subject_to_tech_mapping_cloud(self):
        """Test cloud computing mapping."""
        subjects = ["amazon web services", "cloud computing"]
        known = ["Cloud", "AWS", "Azure"]
        result = infer_technology_from_subjects(subjects, known)
        assert result == "Cloud"

    def test_subject_to_tech_mapping_security(self):
        """Test cybersecurity mapping."""
        subjects = ["cybersecurity", "network security"]
        known = ["Security", "Networking"]
        result = infer_technology_from_subjects(subjects, known)
        assert result == "Security"

    def test_subject_to_tech_mapping_databases(self):
        """Test database management mapping."""
        subjects = ["database management"]
        known = ["Databases", "NoSQL"]
        result = infer_technology_from_subjects(subjects, known)
        assert result == "Databases"

    def test_direct_match_takes_priority(self):
        """Test that direct match is found before mapping."""
        subjects = ["Python", "machine learning"]
        known = ["Python", "AI"]
        result = infer_technology_from_subjects(subjects, known)
        # Should find Python first via direct match
        assert result == "Python"
