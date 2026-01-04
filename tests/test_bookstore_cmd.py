"""Tests for bookstore CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from para_files.cli.bookstore_cmd import (
    BOOK_EXTENSIONS,
    _build_book_filename,
    _detect_book,
    _extract_isbns_from_file,
    _find_book_files,
    _rename_after_move,
    _sanitize_book_title,
)
from para_files.mover import MoveResult
from para_files.utils.isbn_lookup import BookInfo


class TestSanitizeBookTitle:
    """Tests for _sanitize_book_title function."""

    def test_removes_invalid_chars(self):
        """Test removes invalid filesystem characters."""
        result = _sanitize_book_title('Hello: World<>"|?*')
        assert ":" not in result
        assert "<" not in result
        assert ">" not in result
        assert '"' not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result

    def test_collapses_underscores(self):
        """Test collapses multiple underscores."""
        result = _sanitize_book_title("Hello___World")
        assert "___" not in result
        assert "__" not in result

    def test_collapses_spaces(self):
        """Test collapses multiple spaces."""
        result = _sanitize_book_title("Hello   World")
        assert "   " not in result
        assert "  " not in result

    def test_trims_result(self):
        """Test trims leading/trailing underscores and spaces."""
        result = _sanitize_book_title("  _Hello World_  ")
        assert not result.startswith("_")
        assert not result.startswith(" ")
        assert not result.endswith("_")
        assert not result.endswith(" ")

    def test_truncates_long_titles(self):
        """Test truncates long titles."""
        long_title = "A" * 100 + " Last Word"
        result = _sanitize_book_title(long_title, max_length=80)
        assert len(result) <= 80


class TestBuildBookFilename:
    """Tests for _build_book_filename function."""

    def test_with_author_and_title(self):
        """Test building filename with author and title."""
        book_info = BookInfo(
            title="Python Programming",
            authors=["John Doe"],
            publish_date="2023-01-01",
        )
        result = _build_book_filename(book_info, "original.pdf", ".pdf")
        assert "John Doe" in result
        assert "Python Programming" in result
        assert "(2023)" in result
        assert result.endswith(".pdf")

    def test_without_author(self):
        """Test building filename without author."""
        book_info = BookInfo(
            title="Python Programming",
            authors=[],
            publish_date="2023-01-01",
        )
        result = _build_book_filename(book_info, "original.pdf", ".pdf")
        assert "Python Programming" in result
        assert "(2023)" in result
        assert result.endswith(".pdf")

    def test_without_publish_date(self):
        """Test building filename without publish date."""
        book_info = BookInfo(
            title="Python Programming",
            authors=["John Doe"],
            publish_date=None,
        )
        result = _build_book_filename(book_info, "original.pdf", ".pdf")
        assert "John Doe" in result
        assert "Python Programming" in result
        assert "(" not in result  # No year

    def test_without_title_returns_original(self):
        """Test returns original name when no title."""
        book_info = BookInfo(title=None, authors=[])
        result = _build_book_filename(book_info, "original.pdf", ".pdf")
        assert result == "original.pdf"

    def test_handles_epub_extension(self):
        """Test handles EPUB extension."""
        book_info = BookInfo(title="Test Book", authors=["Author"])
        result = _build_book_filename(book_info, "original.epub", ".epub")
        assert result.endswith(".epub")

    def test_handles_extension_without_dot(self):
        """Test handles extension without leading dot."""
        book_info = BookInfo(title="Test Book", authors=["Author"])
        result = _build_book_filename(book_info, "original.pdf", "pdf")
        assert result.endswith(".pdf")


class TestExtractIsbnsFromFile:
    """Tests for _extract_isbns_from_file function."""

    def test_pdf_extraction(self, tmp_path: Path):
        """Test ISBN extraction from PDF."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        with patch("para_files.cli.bookstore_cmd.extract_pdf_metadata") as mock_extract:
            mock_metadata = MagicMock()
            mock_metadata.isbns = ["9780134685991"]
            mock_extract.return_value = mock_metadata

            result = _extract_isbns_from_file(pdf_file)
            assert result == ["9780134685991"]

    def test_chm_extraction(self, tmp_path: Path):
        """Test ISBN extraction from CHM."""
        chm_file = tmp_path / "test.chm"
        chm_file.write_bytes(b"ITSF")

        with patch("para_files.cli.bookstore_cmd.extract_chm_metadata") as mock_extract:
            mock_metadata = MagicMock()
            mock_metadata.isbns = ["9780134685991"]
            mock_extract.return_value = mock_metadata

            result = _extract_isbns_from_file(chm_file)
            assert result == ["9780134685991"]

    def test_epub_extraction(self, tmp_path: Path):
        """Test ISBN extraction from EPUB."""
        epub_file = tmp_path / "test.epub"
        epub_file.write_bytes(b"PK")

        with patch("para_files.cli.bookstore_cmd.extract_epub_metadata") as mock_extract:
            mock_metadata = MagicMock()
            mock_metadata.isbns = ["9780134685991"]
            mock_extract.return_value = mock_metadata

            result = _extract_isbns_from_file(epub_file)
            assert result == ["9780134685991"]

    def test_unsupported_extension(self, tmp_path: Path):
        """Test returns None for unsupported extension."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")
        result = _extract_isbns_from_file(txt_file)
        assert result is None

    def test_extraction_failure(self, tmp_path: Path):
        """Test returns None when extraction fails."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        with patch(
            "para_files.cli.bookstore_cmd.extract_pdf_metadata",
            return_value=None,
        ):
            result = _extract_isbns_from_file(pdf_file)
            assert result is None


class TestFindBookFiles:
    """Tests for _find_book_files function."""

    def test_finds_pdf_files(self, tmp_path: Path):
        """Test finds PDF files."""
        (tmp_path / "book1.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "book2.pdf").write_bytes(b"%PDF-1.4")

        result = _find_book_files(tmp_path, recursive=False)
        assert len(result) == 2
        assert all(f.suffix.lower() == ".pdf" for f in result)

    def test_finds_epub_files(self, tmp_path: Path):
        """Test finds EPUB files."""
        (tmp_path / "book.epub").write_bytes(b"PK")

        result = _find_book_files(tmp_path, recursive=False)
        assert len(result) == 1
        assert result[0].suffix.lower() == ".epub"

    def test_finds_chm_files(self, tmp_path: Path):
        """Test finds CHM files."""
        (tmp_path / "book.chm").write_bytes(b"ITSF")

        result = _find_book_files(tmp_path, recursive=False)
        assert len(result) == 1
        assert result[0].suffix.lower() == ".chm"

    def test_recursive_search(self, tmp_path: Path):
        """Test recursive search in subdirectories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "book1.pdf").write_bytes(b"%PDF-1.4")
        (subdir / "book2.pdf").write_bytes(b"%PDF-1.4")

        result = _find_book_files(tmp_path, recursive=True)
        assert len(result) == 2

    def test_non_recursive_search(self, tmp_path: Path):
        """Test non-recursive search stays in current directory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "book1.pdf").write_bytes(b"%PDF-1.4")
        (subdir / "book2.pdf").write_bytes(b"%PDF-1.4")

        result = _find_book_files(tmp_path, recursive=False)
        assert len(result) == 1

    def test_uppercase_extension(self, tmp_path: Path):
        """Test finds files with uppercase extensions."""
        (tmp_path / "book.PDF").write_bytes(b"%PDF-1.4")

        result = _find_book_files(tmp_path, recursive=False)
        assert len(result) == 1


class TestRenameAfterMove:
    """Tests for _rename_after_move function."""

    def test_renames_file_when_needed(self, tmp_path: Path):
        """Test renames file when name differs."""
        moved_file = tmp_path / "original.pdf"
        moved_file.write_bytes(b"%PDF-1.4")

        move_result = MoveResult(
            source=tmp_path / "source.pdf",
            destination=moved_file,
            success=True,
            action="moved",
        )

        result = _rename_after_move(
            move_result,
            new_filename="renamed.pdf",
            original_name="original.pdf",
            dry_run=False,
        )

        assert result == tmp_path / "renamed.pdf"
        assert (tmp_path / "renamed.pdf").exists()
        assert not (tmp_path / "original.pdf").exists()

    def test_no_rename_on_dry_run(self, tmp_path: Path):
        """Test doesn't rename in dry run mode."""
        moved_file = tmp_path / "original.pdf"
        moved_file.write_bytes(b"%PDF-1.4")

        move_result = MoveResult(
            source=tmp_path / "source.pdf",
            destination=moved_file,
            success=True,
            action="moved",
        )

        result = _rename_after_move(
            move_result,
            new_filename="renamed.pdf",
            original_name="original.pdf",
            dry_run=True,
        )

        assert result == moved_file
        assert (tmp_path / "original.pdf").exists()

    def test_no_rename_when_same_name(self, tmp_path: Path):
        """Test doesn't rename when names are the same."""
        moved_file = tmp_path / "book.pdf"
        moved_file.write_bytes(b"%PDF-1.4")

        move_result = MoveResult(
            source=tmp_path / "source.pdf",
            destination=moved_file,
            success=True,
            action="moved",
        )

        result = _rename_after_move(
            move_result,
            new_filename="book.pdf",
            original_name="book.pdf",
            dry_run=False,
        )

        assert result == moved_file

    def test_no_rename_when_move_failed(self, tmp_path: Path):
        """Test doesn't rename when move failed."""
        move_result = MoveResult(
            source=tmp_path / "source.pdf",
            destination=tmp_path / "original.pdf",
            success=False,
            action="error",
        )

        result = _rename_after_move(
            move_result,
            new_filename="renamed.pdf",
            original_name="original.pdf",
            dry_run=False,
        )

        assert result == tmp_path / "original.pdf"

    def test_no_rename_when_destination_exists(self, tmp_path: Path):
        """Test doesn't overwrite existing file."""
        moved_file = tmp_path / "original.pdf"
        moved_file.write_bytes(b"%PDF-1.4")
        existing_file = tmp_path / "renamed.pdf"
        existing_file.write_bytes(b"%PDF-existing")

        move_result = MoveResult(
            source=tmp_path / "source.pdf",
            destination=moved_file,
            success=True,
            action="moved",
        )

        result = _rename_after_move(
            move_result,
            new_filename="renamed.pdf",
            original_name="original.pdf",
            dry_run=False,
        )

        # Should return the original file since rename was skipped
        assert result == moved_file
        assert (tmp_path / "original.pdf").exists()


class TestBookExtensions:
    """Tests for BOOK_EXTENSIONS constant."""

    def test_contains_pdf(self):
        """Test contains PDF extension."""
        assert ".pdf" in BOOK_EXTENSIONS

    def test_contains_epub(self):
        """Test contains EPUB extension."""
        assert ".epub" in BOOK_EXTENSIONS

    def test_contains_chm(self):
        """Test contains CHM extension."""
        assert ".chm" in BOOK_EXTENSIONS


class TestDetectBook:
    """Tests for _detect_book function."""

    def test_returns_none_for_unsupported_extension(self, tmp_path: Path):
        """Test returns None for unsupported file type."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")
        result = _detect_book(txt_file, tmp_path)
        assert result is None

    def test_returns_none_when_no_isbns(self, tmp_path: Path):
        """Test returns None when no ISBNs found."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        with patch(
            "para_files.cli.bookstore_cmd._extract_isbns_from_file",
            return_value=None,
        ):
            result = _detect_book(pdf_file, tmp_path)
            assert result is None

    def test_returns_none_when_no_matching_book_info(self, tmp_path: Path):
        """Test returns None when no matching book info found."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        with (
            patch(
                "para_files.cli.bookstore_cmd._extract_isbns_from_file",
                return_value=["9780134685991"],
            ),
            patch(
                "para_files.cli.bookstore_cmd.find_matching_book_info",
                return_value=(None, None),
            ),
        ):
            result = _detect_book(pdf_file, tmp_path)
            assert result is None
