"""Tests for file and path validation utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from para_files.utils.validation import validate_directory_exists, validate_file_exists


class TestValidateFileExists:
    """Test validate_file_exists function."""

    def test_existing_file_returns_true(self, tmp_path: Path) -> None:
        """Test that an existing file returns True."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        assert validate_file_exists(test_file) is True

    def test_nonexistent_file_returns_false(self, tmp_path: Path) -> None:
        """Test that a nonexistent file returns False."""
        test_file = tmp_path / "nonexistent.txt"
        assert validate_file_exists(test_file) is False

    def test_directory_returns_false(self, tmp_path: Path) -> None:
        """Test that a directory path returns False (not a file)."""
        assert validate_file_exists(tmp_path) is False

    def test_nonexistent_file_with_exit_on_error_raises(self, tmp_path: Path) -> None:
        """Test that exit_on_error=True raises SystemExit for nonexistent file."""
        test_file = tmp_path / "nonexistent.txt"
        with pytest.raises(SystemExit) as exc_info:
            validate_file_exists(test_file, exit_on_error=True)
        assert exc_info.value.code == 1

    def test_directory_with_exit_on_error_raises(self, tmp_path: Path) -> None:
        """Test that exit_on_error=True raises SystemExit for directory."""
        with pytest.raises(SystemExit) as exc_info:
            validate_file_exists(tmp_path, exit_on_error=True)
        assert exc_info.value.code == 1

    def test_existing_file_with_exit_on_error_returns_true(self, tmp_path: Path) -> None:
        """Test that an existing file with exit_on_error=True returns True."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        assert validate_file_exists(test_file, exit_on_error=True) is True


class TestValidateDirectoryExists:
    """Test validate_directory_exists function."""

    def test_existing_directory_returns_true(self, tmp_path: Path) -> None:
        """Test that an existing directory returns True."""
        assert validate_directory_exists(tmp_path) is True

    def test_nonexistent_directory_returns_false(self, tmp_path: Path) -> None:
        """Test that a nonexistent directory returns False."""
        test_dir = tmp_path / "nonexistent"
        assert validate_directory_exists(test_dir) is False

    def test_file_returns_false(self, tmp_path: Path) -> None:
        """Test that a file path returns False (not a directory)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        assert validate_directory_exists(test_file) is False

    def test_nonexistent_directory_with_exit_on_error_raises(self, tmp_path: Path) -> None:
        """Test that exit_on_error=True raises SystemExit for nonexistent directory."""
        test_dir = tmp_path / "nonexistent"
        with pytest.raises(SystemExit) as exc_info:
            validate_directory_exists(test_dir, exit_on_error=True)
        assert exc_info.value.code == 1

    def test_file_with_exit_on_error_raises(self, tmp_path: Path) -> None:
        """Test that exit_on_error=True raises SystemExit for file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        with pytest.raises(SystemExit) as exc_info:
            validate_directory_exists(test_file, exit_on_error=True)
        assert exc_info.value.code == 1

    def test_existing_directory_with_exit_on_error_returns_true(self, tmp_path: Path) -> None:
        """Test that an existing directory with exit_on_error=True returns True."""
        assert validate_directory_exists(tmp_path, exit_on_error=True) is True

    def test_nested_directory_returns_true(self, tmp_path: Path) -> None:
        """Test that a nested directory returns True."""
        nested = tmp_path / "level1" / "level2"
        nested.mkdir(parents=True)
        assert validate_directory_exists(nested) is True
