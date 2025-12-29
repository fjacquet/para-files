"""Tests for dedupe command."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from para_files.cli.dedupe_cmd import (
    _DUPLICATE_SUFFIX_PATTERN,
    _find_suffixed_duplicates,
    _handle_different_files,
    _handle_identical_duplicate,
    _process_duplicate_pair,
)


class TestDuplicateSuffixPattern:
    """Test the duplicate suffix regex pattern."""

    def test_matches_single_digit(self) -> None:
        """Test pattern matches files with single digit suffix."""
        match = _DUPLICATE_SUFFIX_PATTERN.match("document_1.pdf")
        assert match is not None
        assert match.group(1) == "document"
        assert match.group(2) == "1"
        assert match.group(3) == ".pdf"

    def test_matches_multi_digit(self) -> None:
        """Test pattern matches files with multi-digit suffix."""
        match = _DUPLICATE_SUFFIX_PATTERN.match("file_123.txt")
        assert match is not None
        assert match.group(1) == "file"
        assert match.group(2) == "123"
        assert match.group(3) == ".txt"

    def test_does_not_match_no_suffix(self) -> None:
        """Test pattern does not match files without suffix."""
        match = _DUPLICATE_SUFFIX_PATTERN.match("document.pdf")
        assert match is None

    def test_does_not_match_non_numeric(self) -> None:
        """Test pattern does not match files with non-numeric suffix."""
        match = _DUPLICATE_SUFFIX_PATTERN.match("document_a.pdf")
        assert match is None

    def test_matches_complex_base_name(self) -> None:
        """Test pattern matches complex base names."""
        match = _DUPLICATE_SUFFIX_PATTERN.match("my-complex_file_name_2.pdf")
        assert match is not None
        assert match.group(1) == "my-complex_file_name"
        assert match.group(2) == "2"


class TestFindSuffixedDuplicates:
    """Test _find_suffixed_duplicates function."""

    def test_finds_duplicates(self, tmp_path: Path) -> None:
        """Test finding files with matching originals."""
        # Create original and duplicate
        original = tmp_path / "document.pdf"
        original.write_text("original content")
        duplicate = tmp_path / "document_1.pdf"
        duplicate.write_text("duplicate content")

        result = _find_suffixed_duplicates(tmp_path)
        assert len(result) == 1
        assert result[0] == (duplicate, original)

    def test_ignores_without_original(self, tmp_path: Path) -> None:
        """Test ignores suffixed files without original."""
        # Create only duplicate, no original
        duplicate = tmp_path / "orphan_1.pdf"
        duplicate.write_text("content")

        result = _find_suffixed_duplicates(tmp_path)
        assert len(result) == 0

    def test_recursive_search(self, tmp_path: Path) -> None:
        """Test recursive search finds files in subdirectories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        original = subdir / "file.txt"
        original.write_text("content")
        duplicate = subdir / "file_1.txt"
        duplicate.write_text("content")

        result = _find_suffixed_duplicates(tmp_path, recursive=True)
        assert len(result) == 1

    def test_non_recursive_search(self, tmp_path: Path) -> None:
        """Test non-recursive search ignores subdirectories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        original = subdir / "file.txt"
        original.write_text("content")
        duplicate = subdir / "file_1.txt"
        duplicate.write_text("content")

        result = _find_suffixed_duplicates(tmp_path, recursive=False)
        assert len(result) == 0

    def test_multiple_duplicates(self, tmp_path: Path) -> None:
        """Test finding multiple duplicate pairs."""
        # First pair
        (tmp_path / "doc1.pdf").write_text("content1")
        (tmp_path / "doc1_1.pdf").write_text("content1")
        # Second pair
        (tmp_path / "doc2.txt").write_text("content2")
        (tmp_path / "doc2_1.txt").write_text("content2")

        result = _find_suffixed_duplicates(tmp_path)
        assert len(result) == 2


class TestHandleIdenticalDuplicate:
    """Test _handle_identical_duplicate function."""

    def test_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        """Test dry run mode does not delete files."""
        duplicate = tmp_path / "file_1.pdf"
        duplicate.write_text("content")
        original = tmp_path / "file.pdf"
        original.write_text("content")

        results: dict[str, Any] = {"deleted": [], "kept": [], "different": []}

        status = _handle_identical_duplicate(
            duplicate,
            original,
            results,
            dry_run=True,
            output_json=False,
            verbose=False,
        )

        assert status == "deleted"
        assert duplicate.exists()  # Not actually deleted

    def test_actual_delete(self, tmp_path: Path) -> None:
        """Test actual deletion when not dry run."""
        duplicate = tmp_path / "file_1.pdf"
        duplicate.write_text("content")
        original = tmp_path / "file.pdf"
        original.write_text("content")

        results: dict[str, Any] = {"deleted": [], "kept": [], "different": []}

        status = _handle_identical_duplicate(
            duplicate,
            original,
            results,
            dry_run=False,
            output_json=False,
            verbose=False,
        )

        assert status == "deleted"
        assert not duplicate.exists()  # Actually deleted

    def test_json_output(self, tmp_path: Path) -> None:
        """Test JSON output accumulation."""
        duplicate = tmp_path / "file_1.pdf"
        duplicate.write_text("content")
        original = tmp_path / "file.pdf"
        original.write_text("content")

        results: dict[str, Any] = {"deleted": [], "kept": [], "different": []}

        _handle_identical_duplicate(
            duplicate,
            original,
            results,
            dry_run=True,
            output_json=True,
            verbose=False,
        )

        assert len(results["deleted"]) == 1
        assert results["deleted"][0]["file"] == str(duplicate)
        assert results["deleted"][0]["original"] == str(original)


class TestHandleDifferentFiles:
    """Test _handle_different_files function."""

    def test_records_different_files(self, tmp_path: Path) -> None:
        """Test recording different files in results."""
        duplicate = tmp_path / "file_1.pdf"
        duplicate.write_text("different content")
        original = tmp_path / "file.pdf"
        original.write_text("original content")

        results: dict[str, Any] = {"deleted": [], "kept": [], "different": []}

        status = _handle_different_files(
            duplicate,
            original,
            results,
            output_json=True,
            verbose=False,
        )

        assert status == "different"
        assert len(results["different"]) == 1
        assert results["different"][0]["action"] == "kept (different content)"

    def test_verbose_output(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Test verbose output for different files."""
        duplicate = tmp_path / "file_1.pdf"
        duplicate.write_text("different")
        original = tmp_path / "file.pdf"
        original.write_text("original")

        results: dict[str, Any] = {"deleted": [], "kept": [], "different": []}

        _handle_different_files(
            duplicate,
            original,
            results,
            output_json=False,
            verbose=True,
        )

        captured = capsys.readouterr()
        assert "Kept" in captured.out


class TestProcessDuplicatePair:
    """Test _process_duplicate_pair function."""

    def test_deletes_identical(self, tmp_path: Path) -> None:
        """Test deletion of identical files."""
        content = "same content"
        duplicate = tmp_path / "file_1.pdf"
        duplicate.write_text(content)
        original = tmp_path / "file.pdf"
        original.write_text(content)

        results: dict[str, Any] = {"deleted": [], "kept": [], "different": []}

        status = _process_duplicate_pair(
            duplicate,
            original,
            results,
            dry_run=False,
            output_json=False,
            verbose=False,
        )

        assert status == "deleted"
        assert not duplicate.exists()

    def test_keeps_different(self, tmp_path: Path) -> None:
        """Test keeping different files."""
        duplicate = tmp_path / "file_1.pdf"
        duplicate.write_text("content A")
        original = tmp_path / "file.pdf"
        original.write_text("content B")

        results: dict[str, Any] = {"deleted": [], "kept": [], "different": []}

        status = _process_duplicate_pair(
            duplicate,
            original,
            results,
            dry_run=False,
            output_json=True,
            verbose=False,
        )

        assert status == "different"
        assert duplicate.exists()

    def test_handles_error(self, tmp_path: Path) -> None:
        """Test error handling when file operations fail."""
        duplicate = tmp_path / "file_1.pdf"
        duplicate.write_text("content")
        # Original doesn't exist - will cause error when comparing
        original = tmp_path / "nonexistent.pdf"

        results: dict[str, Any] = {"deleted": [], "kept": [], "different": []}

        status = _process_duplicate_pair(
            duplicate,
            original,
            results,
            dry_run=False,
            output_json=True,
            verbose=False,
        )

        assert status == "error"
        assert len(results["kept"]) == 1
        assert "error" in results["kept"][0]
