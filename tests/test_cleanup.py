"""Tests for cleanup utilities."""

from __future__ import annotations

from pathlib import Path

from para_files.utils.cleanup import (
    JUNK_DIRECTORIES,
    JUNK_PATTERNS,
    cleanup_empty_dirs,
    cleanup_junk,
    delete_junk_directory,
    delete_junk_file,
    is_junk_directory,
    is_junk_file,
    scan_for_junk,
)


class TestJunkPatterns:
    """Test junk file pattern definitions."""

    def test_junk_patterns_not_empty(self) -> None:
        """Ensure JUNK_PATTERNS is populated."""
        assert len(JUNK_PATTERNS) > 0

    def test_junk_directories_not_empty(self) -> None:
        """Ensure JUNK_DIRECTORIES is populated."""
        assert len(JUNK_DIRECTORIES) > 0

    def test_ds_store_in_patterns(self) -> None:
        """Ensure .DS_Store is a known junk pattern."""
        assert ".DS_Store" in JUNK_PATTERNS

    def test_thumbs_db_in_patterns(self) -> None:
        """Ensure Thumbs.db is a known junk pattern."""
        assert "Thumbs.db" in JUNK_PATTERNS


class TestIsJunkFile:
    """Test is_junk_file detection."""

    def test_ds_store_is_junk(self, tmp_path: Path) -> None:
        """Test .DS_Store is detected as junk."""
        junk = tmp_path / ".DS_Store"
        junk.touch()
        assert is_junk_file(junk)

    def test_apple_double_is_junk(self, tmp_path: Path) -> None:
        """Test AppleDouble files (._*) are detected as junk."""
        junk = tmp_path / "._myfile.txt"
        junk.touch()
        assert is_junk_file(junk)

    def test_thumbs_db_is_junk(self, tmp_path: Path) -> None:
        """Test Thumbs.db is detected as junk."""
        junk = tmp_path / "Thumbs.db"
        junk.touch()
        assert is_junk_file(junk)

    def test_desktop_ini_is_junk(self, tmp_path: Path) -> None:
        """Test desktop.ini is detected as junk."""
        junk = tmp_path / "desktop.ini"
        junk.touch()
        assert is_junk_file(junk)

    def test_normal_file_not_junk(self, tmp_path: Path) -> None:
        """Test normal files are not detected as junk."""
        normal = tmp_path / "document.pdf"
        normal.touch()
        assert not is_junk_file(normal)

    def test_hidden_file_not_junk(self, tmp_path: Path) -> None:
        """Test normal hidden files are not detected as junk."""
        hidden = tmp_path / ".gitignore"
        hidden.touch()
        assert not is_junk_file(hidden)


class TestIsJunkDirectory:
    """Test is_junk_directory detection."""

    def test_spotlight_is_junk(self, tmp_path: Path) -> None:
        """Test .Spotlight-V100 is detected as junk directory."""
        junk = tmp_path / ".Spotlight-V100"
        junk.mkdir()
        assert is_junk_directory(junk)

    def test_trashes_is_junk(self, tmp_path: Path) -> None:
        """Test .Trashes is detected as junk directory."""
        junk = tmp_path / ".Trashes"
        junk.mkdir()
        assert is_junk_directory(junk)

    def test_normal_dir_not_junk(self, tmp_path: Path) -> None:
        """Test normal directories are not detected as junk."""
        normal = tmp_path / "Documents"
        normal.mkdir()
        assert not is_junk_directory(normal)

    def test_file_not_junk_dir(self, tmp_path: Path) -> None:
        """Test files are not detected as junk directories."""
        file = tmp_path / ".Spotlight-V100"
        file.touch()  # Create as file, not directory
        assert not is_junk_directory(file)


class TestDeleteJunkFile:
    """Test delete_junk_file function."""

    def test_dry_run_preserves_file(self, tmp_path: Path) -> None:
        """Test dry run doesn't delete the file."""
        junk = tmp_path / ".DS_Store"
        junk.touch()

        result = delete_junk_file(junk, dry_run=True)

        assert result is True
        assert junk.exists()

    def test_actual_delete_removes_file(self, tmp_path: Path) -> None:
        """Test actual deletion removes the file."""
        junk = tmp_path / ".DS_Store"
        junk.touch()

        result = delete_junk_file(junk, dry_run=False)

        assert result is True
        assert not junk.exists()

    def test_refuses_normal_file(self, tmp_path: Path) -> None:
        """Test refuses to delete non-junk files."""
        normal = tmp_path / "important.pdf"
        normal.touch()

        result = delete_junk_file(normal, dry_run=False)

        assert result is False
        assert normal.exists()

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Test handling of nonexistent file."""
        nonexistent = tmp_path / ".DS_Store"

        result = delete_junk_file(nonexistent, dry_run=False)

        assert result is False


class TestDeleteJunkDirectory:
    """Test delete_junk_directory function."""

    def test_dry_run_preserves_dir(self, tmp_path: Path) -> None:
        """Test dry run doesn't delete the directory."""
        junk = tmp_path / ".Spotlight-V100"
        junk.mkdir()

        result = delete_junk_directory(junk, dry_run=True)

        assert result is True
        assert junk.exists()

    def test_actual_delete_removes_dir(self, tmp_path: Path) -> None:
        """Test actual deletion removes the directory."""
        junk = tmp_path / ".Spotlight-V100"
        junk.mkdir()
        (junk / "store").touch()  # Add content

        result = delete_junk_directory(junk, dry_run=False)

        assert result is True
        assert not junk.exists()

    def test_refuses_normal_dir(self, tmp_path: Path) -> None:
        """Test refuses to delete non-junk directories."""
        normal = tmp_path / "Documents"
        normal.mkdir()

        result = delete_junk_directory(normal, dry_run=False)

        assert result is False
        assert normal.exists()


class TestCleanupEmptyDirs:
    """Test cleanup_empty_dirs function."""

    def test_removes_empty_dirs(self, tmp_path: Path) -> None:
        """Test removes empty directories."""
        empty = tmp_path / "empty_folder"
        empty.mkdir()

        deleted = cleanup_empty_dirs(tmp_path, dry_run=False)

        assert len(deleted) == 1
        assert empty in deleted
        assert not empty.exists()

    def test_preserves_non_empty_dirs(self, tmp_path: Path) -> None:
        """Test preserves directories with content."""
        non_empty = tmp_path / "has_content"
        non_empty.mkdir()
        (non_empty / "file.txt").touch()

        deleted = cleanup_empty_dirs(tmp_path, dry_run=False)

        assert len(deleted) == 0
        assert non_empty.exists()

    def test_dry_run_preserves_empty_dirs(self, tmp_path: Path) -> None:
        """Test dry run lists but preserves empty directories."""
        empty = tmp_path / "empty_folder"
        empty.mkdir()

        deleted = cleanup_empty_dirs(tmp_path, dry_run=True)

        assert len(deleted) == 1
        assert empty.exists()  # Still exists in dry-run

    def test_bottom_up_deletion(self, tmp_path: Path) -> None:
        """Test nested empty dirs are deleted bottom-up."""
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)

        deleted = cleanup_empty_dirs(tmp_path, dry_run=False)

        # Should delete c, then b, then a (all empty)
        assert len(deleted) == 3
        assert not (tmp_path / "a").exists()


class TestScanForJunk:
    """Test scan_for_junk function."""

    def test_finds_junk_files(self, tmp_path: Path) -> None:
        """Test finds junk files in directory."""
        (tmp_path / ".DS_Store").touch()
        (tmp_path / "normal.txt").touch()

        junk_files, junk_dirs = scan_for_junk(tmp_path, recursive=False)

        assert len(junk_files) == 1
        assert junk_files[0].name == ".DS_Store"
        assert len(junk_dirs) == 0

    def test_finds_junk_dirs(self, tmp_path: Path) -> None:
        """Test finds junk directories."""
        (tmp_path / ".Spotlight-V100").mkdir()
        (tmp_path / "Documents").mkdir()

        junk_files, junk_dirs = scan_for_junk(tmp_path, recursive=False)

        assert len(junk_files) == 0
        assert len(junk_dirs) == 1
        assert junk_dirs[0].name == ".Spotlight-V100"

    def test_recursive_scan(self, tmp_path: Path) -> None:
        """Test recursive scanning finds nested junk."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / ".DS_Store").touch()

        # Non-recursive shouldn't find it
        junk_files, _ = scan_for_junk(tmp_path, recursive=False)
        assert len(junk_files) == 0

        # Recursive should find it
        junk_files, _ = scan_for_junk(tmp_path, recursive=True)
        assert len(junk_files) == 1


class TestCleanupJunk:
    """Test cleanup_junk function."""

    def test_cleans_junk_files(self, tmp_path: Path) -> None:
        """Test cleans junk files."""
        (tmp_path / ".DS_Store").touch()
        (tmp_path / "Thumbs.db").touch()
        (tmp_path / "normal.txt").touch()

        deleted_files, deleted_dirs = cleanup_junk(tmp_path, recursive=True, dry_run=False)

        assert len(deleted_files) == 2
        assert not (tmp_path / ".DS_Store").exists()
        assert not (tmp_path / "Thumbs.db").exists()
        assert (tmp_path / "normal.txt").exists()

    def test_cleans_junk_dirs(self, tmp_path: Path) -> None:
        """Test cleans junk directories."""
        junk_dir = tmp_path / ".Spotlight-V100"
        junk_dir.mkdir()
        (junk_dir / "store.db").touch()

        deleted_files, deleted_dirs = cleanup_junk(tmp_path, recursive=True, dry_run=False)

        assert len(deleted_dirs) == 1
        assert not junk_dir.exists()

    def test_dry_run_cleans_nothing(self, tmp_path: Path) -> None:
        """Test dry run doesn't actually clean."""
        (tmp_path / ".DS_Store").touch()

        deleted_files, _ = cleanup_junk(tmp_path, recursive=True, dry_run=True)

        assert len(deleted_files) == 1
        assert (tmp_path / ".DS_Store").exists()
