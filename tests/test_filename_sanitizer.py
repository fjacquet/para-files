"""Tests for filename sanitization utilities."""

from __future__ import annotations

from para_files.utils.filename_sanitizer import (
    INVALID_FILENAME_CHARS,
    get_invalid_chars,
    is_valid_filename,
    sanitize_filename,
    sanitize_path_component,
)


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_empty_string(self) -> None:
        """Empty string returns empty."""
        assert sanitize_filename("") == ""

    def test_clean_string(self) -> None:
        """Clean string is unchanged."""
        assert sanitize_filename("hello_world") == "hello_world"

    def test_colon_replaced(self) -> None:
        """Colon is replaced with underscore."""
        assert sanitize_filename("Hello: World") == "Hello_World"

    def test_slash_replaced(self) -> None:
        """Slash is replaced with underscore."""
        assert sanitize_filename("path/to/file") == "path_to_file"

    def test_backslash_replaced(self) -> None:
        """Backslash is replaced with underscore."""
        assert sanitize_filename("path\\to\\file") == "path_to_file"

    def test_hash_replaced(self) -> None:
        """Hash is replaced with underscore."""
        assert sanitize_filename("File#1") == "File_1"

    def test_comma_replaced(self) -> None:
        """Comma is replaced with underscore."""
        assert sanitize_filename("one, two, three") == "one_two_three"

    def test_asterisk_replaced(self) -> None:
        """Asterisk is replaced with underscore."""
        assert sanitize_filename("file*.txt") == "file_.txt"

    def test_question_mark_replaced(self) -> None:
        """Question mark is replaced with underscore."""
        # Note: trailing underscores are stripped
        assert sanitize_filename("what?") == "what"
        assert sanitize_filename("wh?at") == "wh_at"

    def test_angle_brackets_replaced(self) -> None:
        """Angle brackets are replaced."""
        # Note: leading/trailing underscores are stripped
        assert sanitize_filename("<input>") == "input"
        assert sanitize_filename("a<b>c") == "a_b_c"

    def test_double_quote_replaced(self) -> None:
        """Double quote is replaced."""
        # Note: trailing underscores are stripped, spaces are replaced
        assert sanitize_filename('say "hello"') == "say_hello"
        assert sanitize_filename('"test"') == "test"

    def test_pipe_replaced(self) -> None:
        """Pipe is replaced."""
        assert sanitize_filename("a|b") == "a_b"

    def test_multiple_underscores_collapsed(self) -> None:
        """Multiple consecutive underscores are collapsed to one."""
        assert sanitize_filename("a::b") == "a_b"
        assert sanitize_filename("a///b") == "a_b"

    def test_leading_trailing_stripped(self) -> None:
        """Leading/trailing replacement chars are stripped."""
        assert sanitize_filename(":hello:") == "hello"
        assert sanitize_filename("///path///") == "path"

    def test_max_length(self) -> None:
        """Max length is respected."""
        result = sanitize_filename("this_is_a_very_long_filename", max_length=15)
        assert len(result) <= 15

    def test_max_length_word_boundary(self) -> None:
        """Truncation prefers word boundaries."""
        result = sanitize_filename("hello_world_test", max_length=12)
        assert result == "hello_world"

    def test_preserve_extension(self) -> None:
        """Extension is preserved when requested."""
        result = sanitize_filename(
            "very_long_filename_here.pdf", max_length=15, preserve_extension=True
        )
        assert result.endswith(".pdf")

    def test_custom_replacement(self) -> None:
        """Custom replacement character is used."""
        result = sanitize_filename("Hello: World", replacement="-")
        assert ":" not in result
        assert "-" in result

    def test_all_invalid_chars(self) -> None:
        """All invalid characters are replaced."""
        invalid = ',#"*:<>?/\\|'
        result = sanitize_filename(f"test{invalid}test")
        for char in invalid:
            assert char not in result


class TestSanitizePathComponent:
    """Tests for sanitize_path_component function."""

    def test_empty_string(self) -> None:
        """Empty string returns empty."""
        assert sanitize_path_component("") == ""

    def test_colon_with_spaces(self) -> None:
        """Colon is replaced with proper spacing."""
        result = sanitize_path_component("Arts : généralités")
        assert ":" not in result
        assert "Arts" in result
        assert "généralités" in result

    def test_ampersand_replaced(self) -> None:
        """Ampersand is replaced with 'et'."""
        result = sanitize_path_component("Art & Design")
        assert "&" not in result
        assert "et" in result

    def test_slash_replaced(self) -> None:
        """Slash is replaced."""
        result = sanitize_path_component("Radio / podcasts")
        assert "/" not in result

    def test_unicode_preserved(self) -> None:
        """Unicode characters are preserved."""
        result = sanitize_path_component("Éducation française")
        assert "É" in result
        assert "ç" in result


class TestIsValidFilename:
    """Tests for is_valid_filename function."""

    def test_valid_filename(self) -> None:
        """Valid filename returns True."""
        assert is_valid_filename("hello_world.txt")
        assert is_valid_filename("document-2024")
        assert is_valid_filename("Éducation")

    def test_invalid_with_colon(self) -> None:
        """Filename with colon is invalid."""
        assert not is_valid_filename("Hello: World")

    def test_invalid_with_slash(self) -> None:
        """Filename with slash is invalid."""
        assert not is_valid_filename("path/file")

    def test_invalid_with_hash(self) -> None:
        """Filename with hash is invalid."""
        assert not is_valid_filename("file#1")

    def test_empty_is_invalid(self) -> None:
        """Empty string is invalid."""
        assert not is_valid_filename("")


class TestGetInvalidChars:
    """Tests for get_invalid_chars function."""

    def test_no_invalid_chars(self) -> None:
        """Clean string has no invalid chars."""
        assert get_invalid_chars("hello_world") == []

    def test_finds_colon(self) -> None:
        """Finds colon in string."""
        assert ":" in get_invalid_chars("Hello: World")

    def test_finds_multiple(self) -> None:
        """Finds multiple invalid chars."""
        chars = get_invalid_chars("a:b/c#d")
        assert ":" in chars
        assert "/" in chars
        assert "#" in chars

    def test_finds_duplicates(self) -> None:
        """Finds duplicate invalid chars."""
        chars = get_invalid_chars("a:b:c")
        assert chars.count(":") == 2


class TestInvalidCharsPattern:
    """Tests for INVALID_FILENAME_CHARS constant."""

    def test_contains_required_chars(self) -> None:
        """Pattern includes all required invalid characters."""
        import re

        pattern = re.compile(INVALID_FILENAME_CHARS)
        required = [",", "#", '"', "*", ":", "<", ">", "?", "/", "\\", "|"]
        for char in required:
            assert pattern.search(char), f"Pattern should match '{char}'"
