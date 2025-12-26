"""Tests for NFO file parser."""

from __future__ import annotations

from pathlib import Path

from para_files.utils.nfo_parser import (
    NfoHints,
    find_associated_nfo,
    get_nfo_hints_for_file,
    parse_nfo,
)


class TestNfoHints:
    """Test NfoHints dataclass."""

    def test_empty_hints_has_no_hints(self) -> None:
        """Test empty hints reports has_hints as False."""
        hints = NfoHints()
        assert not hints.has_hints()

    def test_hints_with_title_has_hints(self) -> None:
        """Test hints with title reports has_hints as True."""
        hints = NfoHints(title="Test Title")
        assert hints.has_hints()

    def test_hints_with_tags_has_hints(self) -> None:
        """Test hints with tags reports has_hints as True."""
        hints = NfoHints(tags=["tag1", "tag2"])
        assert hints.has_hints()


class TestParseNfo:
    """Test parse_nfo function."""

    def test_parse_title(self, tmp_path: Path) -> None:
        """Test parsing title from NFO."""
        nfo = tmp_path / "test.nfo"
        nfo.write_text("Title: My Great Book\nSome other content")

        hints = parse_nfo(nfo)

        assert hints.title == "My Great Book"

    def test_parse_category(self, tmp_path: Path) -> None:
        """Test parsing category from NFO."""
        nfo = tmp_path / "test.nfo"
        nfo.write_text("Category: Technical\nContent here")

        hints = parse_nfo(nfo)

        assert hints.category == "Technical"

    def test_parse_year(self, tmp_path: Path) -> None:
        """Test parsing year from NFO."""
        nfo = tmp_path / "test.nfo"
        nfo.write_text("Year: 2024\nContent here")

        hints = parse_nfo(nfo)

        assert hints.year == 2024

    def test_parse_standalone_year(self, tmp_path: Path) -> None:
        """Test parsing standalone year from NFO."""
        nfo = tmp_path / "test.nfo"
        nfo.write_text("Published in 2023\nContent here")

        hints = parse_nfo(nfo)

        assert hints.year == 2023

    def test_parse_author(self, tmp_path: Path) -> None:
        """Test parsing author from NFO."""
        nfo = tmp_path / "test.nfo"
        nfo.write_text("Author: John Doe\nContent here")

        hints = parse_nfo(nfo)

        assert hints.author == "John Doe"

    def test_parse_publisher(self, tmp_path: Path) -> None:
        """Test parsing publisher from NFO."""
        nfo = tmp_path / "test.nfo"
        nfo.write_text("Publisher: O'Reilly Media\nContent here")

        hints = parse_nfo(nfo)

        assert hints.publisher == "O'Reilly Media"

    def test_parse_language(self, tmp_path: Path) -> None:
        """Test parsing language from NFO."""
        nfo = tmp_path / "test.nfo"
        nfo.write_text("Language: English\nContent here")

        hints = parse_nfo(nfo)

        assert hints.language == "English"

    def test_parse_tags(self, tmp_path: Path) -> None:
        """Test parsing tags from NFO."""
        nfo = tmp_path / "test.nfo"
        nfo.write_text("Tags: python, programming, tutorial")

        hints = parse_nfo(nfo)

        assert "python" in hints.tags
        assert "programming" in hints.tags

    def test_parse_source(self, tmp_path: Path) -> None:
        """Test parsing source from NFO."""
        nfo = tmp_path / "test.nfo"
        nfo.write_text("Source: Amazon Kindle")

        hints = parse_nfo(nfo)

        assert hints.source == "Amazon Kindle"

    def test_raw_text_preserved(self, tmp_path: Path) -> None:
        """Test raw text is preserved in hints."""
        nfo = tmp_path / "test.nfo"
        content = "Title: Test\nContent here"
        nfo.write_text(content)

        hints = parse_nfo(nfo)

        assert hints.raw_text == content

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test parsing empty NFO file."""
        nfo = tmp_path / "empty.nfo"
        nfo.write_text("")

        hints = parse_nfo(nfo)

        assert not hints.has_hints()

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Test parsing nonexistent NFO file."""
        nfo = tmp_path / "nonexistent.nfo"

        hints = parse_nfo(nfo)

        assert not hints.has_hints()


class TestFindAssociatedNfo:
    """Test find_associated_nfo function."""

    def test_finds_same_name_nfo(self, tmp_path: Path) -> None:
        """Test finds NFO with same basename."""
        file = tmp_path / "document.pdf"
        file.touch()
        nfo = tmp_path / "document.nfo"
        nfo.touch()

        result = find_associated_nfo(file)

        assert result == nfo

    def test_finds_case_insensitive_nfo(self, tmp_path: Path) -> None:
        """Test finds NFO with different case."""
        file = tmp_path / "Document.pdf"
        file.touch()
        nfo = tmp_path / "document.NFO"
        nfo.touch()

        result = find_associated_nfo(file)

        assert result is not None
        assert result.suffix.lower() == ".nfo"

    def test_finds_folder_nfo(self, tmp_path: Path) -> None:
        """Test finds NFO named after folder."""
        subdir = tmp_path / "MyBook"
        subdir.mkdir()
        file = subdir / "chapter1.pdf"
        file.touch()
        nfo = subdir / "MyBook.nfo"
        nfo.touch()

        result = find_associated_nfo(file)

        assert result == nfo

    def test_finds_single_nfo_in_dir(self, tmp_path: Path) -> None:
        """Test finds single NFO in directory."""
        file = tmp_path / "document.pdf"
        file.touch()
        nfo = tmp_path / "info.nfo"
        nfo.touch()

        result = find_associated_nfo(file)

        assert result == nfo

    def test_prefers_shorter_name_nfo(self, tmp_path: Path) -> None:
        """Test prefers shorter named NFO when multiple exist."""
        file = tmp_path / "document.pdf"
        file.touch()
        nfo1 = tmp_path / "a.nfo"
        nfo1.touch()
        nfo2 = tmp_path / "longer_name.nfo"
        nfo2.touch()

        result = find_associated_nfo(file)

        assert result == nfo1

    def test_returns_none_when_no_nfo(self, tmp_path: Path) -> None:
        """Test returns None when no NFO exists."""
        file = tmp_path / "document.pdf"
        file.touch()

        result = find_associated_nfo(file)

        assert result is None

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Test returns None for nonexistent file."""
        file = tmp_path / "nonexistent.pdf"

        result = find_associated_nfo(file)

        assert result is None


class TestGetNfoHintsForFile:
    """Test get_nfo_hints_for_file function."""

    def test_returns_hints_when_nfo_exists(self, tmp_path: Path) -> None:
        """Test returns hints when NFO with content exists."""
        file = tmp_path / "book.pdf"
        file.touch()
        nfo = tmp_path / "book.nfo"
        nfo.write_text("Title: My Book\nYear: 2024")

        hints = get_nfo_hints_for_file(file)

        assert hints is not None
        assert hints.title == "My Book"
        assert hints.year == 2024

    def test_returns_none_when_no_nfo(self, tmp_path: Path) -> None:
        """Test returns None when no NFO exists."""
        file = tmp_path / "document.pdf"
        file.touch()

        hints = get_nfo_hints_for_file(file)

        assert hints is None

    def test_returns_none_for_empty_nfo(self, tmp_path: Path) -> None:
        """Test returns None for NFO with no useful hints."""
        file = tmp_path / "document.pdf"
        file.touch()
        nfo = tmp_path / "document.nfo"
        nfo.write_text("")  # Empty NFO

        hints = get_nfo_hints_for_file(file)

        assert hints is None


class TestNfoEncodingHandling:
    """Test NFO file encoding handling."""

    def test_utf8_encoding(self, tmp_path: Path) -> None:
        """Test reading UTF-8 encoded NFO."""
        nfo = tmp_path / "test.nfo"
        nfo.write_text("Title: Héllo Wörld", encoding="utf-8")

        hints = parse_nfo(nfo)

        assert hints.title == "Héllo Wörld"

    def test_latin1_encoding(self, tmp_path: Path) -> None:
        """Test reading Latin-1 encoded NFO."""
        nfo = tmp_path / "test.nfo"
        nfo.write_bytes("Title: Caf\xe9".encode("latin-1"))

        hints = parse_nfo(nfo)

        assert hints.title is not None
        assert "Caf" in hints.title
