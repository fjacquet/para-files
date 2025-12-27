"""Tests for the file mover module."""

from __future__ import annotations

from pathlib import Path

from para_files.mover import (
    ConflictStrategy,
    FileMover,
    MoveResult,
    _compute_file_hash,
    files_are_identical,
    move_classified_file,
)


class TestMoveResult:
    """Tests for MoveResult model."""

    def test_move_result_basic(self):
        """Test MoveResult with basic values."""
        result = MoveResult(
            source=Path("/src/file.txt"),
            destination=Path("/dst/file.txt"),
            success=True,
            action="moved",
        )
        assert result.source == Path("/src/file.txt")
        assert result.destination == Path("/dst/file.txt")
        assert result.success is True
        assert result.action == "moved"
        assert result.message == ""

    def test_move_result_with_message(self):
        """Test MoveResult with error message."""
        result = MoveResult(
            source=Path("/src/file.txt"),
            destination=Path("/dst/file.txt"),
            success=False,
            action="error",
            message="Permission denied",
        )
        assert result.message == "Permission denied"


class TestConflictStrategy:
    """Tests for ConflictStrategy enum."""

    def test_all_strategies_defined(self):
        """Test all conflict strategies are defined."""
        assert ConflictStrategy.SKIP.value == "skip"
        assert ConflictStrategy.OVERWRITE.value == "overwrite"
        assert ConflictStrategy.RENAME.value == "rename"
        assert ConflictStrategy.RENAME_WITH_DATE.value == "rename_with_date"


class TestFileMoverDryRun:
    """Tests for FileMover in dry-run mode."""

    def test_dry_run_move(self, tmp_path: Path):
        """Test dry-run reports what would happen without moving."""
        # Create source file
        source = tmp_path / "source" / "test.txt"
        source.parent.mkdir()
        source.write_text("test content")

        dest_dir = tmp_path / "destination"

        mover = FileMover(dry_run=True)
        result = mover.move(source, dest_dir)

        assert result.success is True
        assert "would be moved" in result.action
        assert source.exists()  # File should still exist
        assert not (dest_dir / "test.txt").exists()

    def test_dry_run_copy(self, tmp_path: Path):
        """Test dry-run copy mode."""
        source = tmp_path / "test.txt"
        source.write_text("content")

        dest_dir = tmp_path / "dest"

        mover = FileMover(dry_run=True, copy_mode=True)
        result = mover.move(source, dest_dir)

        assert "would be copied" in result.action


class TestFileMoverMove:
    """Tests for FileMover actual move operations."""

    def test_move_file(self, tmp_path: Path):
        """Test moving a file to a new location."""
        source = tmp_path / "source" / "document.txt"
        source.parent.mkdir()
        source.write_text("important content")

        dest_dir = tmp_path / "destination"

        mover = FileMover()
        result = mover.move(source, dest_dir)

        assert result.success is True
        assert result.action == "moved"
        assert not source.exists()
        assert (dest_dir / "document.txt").exists()
        assert (dest_dir / "document.txt").read_text() == "important content"

    def test_copy_file(self, tmp_path: Path):
        """Test copying a file preserves the original."""
        source = tmp_path / "original.txt"
        source.write_text("keep this")

        dest_dir = tmp_path / "backup"

        mover = FileMover(copy_mode=True)
        result = mover.move(source, dest_dir)

        assert result.success is True
        assert result.action == "copied"
        assert source.exists()  # Original still exists
        assert (dest_dir / "original.txt").exists()

    def test_move_creates_directory(self, tmp_path: Path):
        """Test move creates destination directory if needed."""
        source = tmp_path / "file.txt"
        source.write_text("data")

        dest_dir = tmp_path / "nested" / "deep" / "dir"

        mover = FileMover()
        result = mover.move(source, dest_dir)

        assert result.success is True
        assert dest_dir.exists()
        assert (dest_dir / "file.txt").exists()


class TestFileMoverErrors:
    """Tests for FileMover error handling."""

    def test_source_not_exists(self, tmp_path: Path):
        """Test error when source file doesn't exist."""
        mover = FileMover()
        result = mover.move(
            tmp_path / "nonexistent.txt",
            tmp_path / "dest",
        )

        assert result.success is False
        assert result.action == "error"
        assert "does not exist" in result.message

    def test_source_is_directory(self, tmp_path: Path):
        """Test error when source is a directory."""
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()

        mover = FileMover()
        result = mover.move(source_dir, tmp_path / "dest")

        assert result.success is False
        assert result.action == "error"
        assert "not a file" in result.message


class TestConflictResolution:
    """Tests for conflict resolution strategies."""

    def test_skip_existing(self, tmp_path: Path):
        """Test SKIP strategy skips existing files."""
        # Create source and existing destination
        source = tmp_path / "new.txt"
        source.write_text("new content")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        existing = dest_dir / "new.txt"
        existing.write_text("old content")

        mover = FileMover(conflict_strategy=ConflictStrategy.SKIP)
        result = mover.move(source, dest_dir)

        assert result.success is True
        assert result.action == "skipped"
        assert source.exists()  # Source unchanged
        assert existing.read_text() == "old content"  # Destination unchanged

    def test_overwrite_existing(self, tmp_path: Path):
        """Test OVERWRITE strategy replaces existing files."""
        source = tmp_path / "new.txt"
        source.write_text("new content")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        existing = dest_dir / "new.txt"
        existing.write_text("old content")

        mover = FileMover(conflict_strategy=ConflictStrategy.OVERWRITE)
        result = mover.move(source, dest_dir)

        assert result.success is True
        assert result.action == "moved"
        assert (dest_dir / "new.txt").read_text() == "new content"

    def test_rename_adds_counter(self, tmp_path: Path):
        """Test RENAME strategy adds counter suffix."""
        source = tmp_path / "file.txt"
        source.write_text("new file")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        (dest_dir / "file.txt").write_text("existing")

        mover = FileMover(conflict_strategy=ConflictStrategy.RENAME)
        result = mover.move(source, dest_dir)

        assert result.success is True
        assert result.destination == dest_dir / "file_1.txt"
        assert (dest_dir / "file.txt").exists()  # Original preserved
        assert (dest_dir / "file_1.txt").exists()

    def test_rename_increments_counter(self, tmp_path: Path):
        """Test RENAME increments counter for multiple conflicts."""
        source = tmp_path / "doc.pdf"
        source.write_text("pdf content")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        (dest_dir / "doc.pdf").write_text("v1")
        (dest_dir / "doc_1.pdf").write_text("v2")
        (dest_dir / "doc_2.pdf").write_text("v3")

        mover = FileMover(conflict_strategy=ConflictStrategy.RENAME)
        result = mover.move(source, dest_dir)

        assert result.destination == dest_dir / "doc_3.pdf"

    def test_rename_with_date_adds_timestamp(self, tmp_path: Path):
        """Test RENAME_WITH_DATE adds timestamp suffix."""
        source = tmp_path / "report.docx"
        source.write_text("report")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        (dest_dir / "report.docx").write_text("existing")

        mover = FileMover(conflict_strategy=ConflictStrategy.RENAME_WITH_DATE)
        result = mover.move(source, dest_dir)

        assert result.success is True
        # Should have timestamp like report_20250125_143022.docx
        assert "report_" in result.destination.name
        assert result.destination.suffix == ".docx"


class TestDatePrefix:
    """Tests for date prefix feature."""

    def test_add_date_prefix(self, tmp_path: Path):
        """Test adding date prefix to filename."""
        source = tmp_path / "photo.jpg"
        source.write_text("image data")

        dest_dir = tmp_path / "dest"

        mover = FileMover(add_date_prefix=True)
        result = mover.move(source, dest_dir)

        assert result.success is True
        # Filename should have date prefix like 2025-01-25_photo.jpg
        assert "_photo.jpg" in result.destination.name
        # Verify date format (YYYY-MM-DD)
        name = result.destination.name
        assert len(name.split("_")[0]) == 10  # YYYY-MM-DD


class TestConvenienceFunction:
    """Tests for move_classified_file helper function."""

    def test_move_classified_file_default(self, tmp_path: Path):
        """Test convenience function with defaults."""
        source = tmp_path / "invoice.pdf"
        source.write_text("invoice content")

        target = tmp_path / "Archives" / "Finance"

        result = move_classified_file(source, target)

        assert result.success is True
        assert (target / "invoice.pdf").exists()

    def test_move_classified_file_dry_run(self, tmp_path: Path):
        """Test convenience function in dry-run mode."""
        source = tmp_path / "doc.txt"
        source.write_text("text")

        result = move_classified_file(
            source,
            tmp_path / "dest",
            dry_run=True,
        )

        assert result.success is True
        assert "would be" in result.action
        assert source.exists()

    def test_move_classified_file_copy_mode(self, tmp_path: Path):
        """Test convenience function in copy mode."""
        source = tmp_path / "important.md"
        source.write_text("notes")

        result = move_classified_file(
            source,
            tmp_path / "backup",
            copy_mode=True,
        )

        assert result.success is True
        assert result.action == "copied"
        assert source.exists()


class TestFileHashing:
    """Tests for file hashing and comparison functions."""

    def test_compute_file_hash(self, tmp_path: Path):
        """Test SHA256 hash computation."""
        file = tmp_path / "test.txt"
        file.write_text("hello world")

        hash1 = _compute_file_hash(file)

        # SHA256 of "hello world" (as bytes with no newline from write_text)
        assert len(hash1) == 64  # SHA256 hex is 64 chars
        assert hash1.isalnum()

    def test_compute_file_hash_same_content(self, tmp_path: Path):
        """Test that same content produces same hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        content = "identical content here"

        file1.write_text(content)
        file2.write_text(content)

        assert _compute_file_hash(file1) == _compute_file_hash(file2)

    def test_compute_file_hash_different_content(self, tmp_path: Path):
        """Test that different content produces different hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("content A")
        file2.write_text("content B")

        assert _compute_file_hash(file1) != _compute_file_hash(file2)

    def test_files_are_identical_same_content(self, tmp_path: Path):
        """Test files_are_identical returns True for identical files."""
        file1 = tmp_path / "a.txt"
        file2 = tmp_path / "b.txt"
        content = "same content"

        file1.write_text(content)
        file2.write_text(content)

        assert files_are_identical(file1, file2) is True

    def test_files_are_identical_different_content(self, tmp_path: Path):
        """Test files_are_identical returns False for different files."""
        file1 = tmp_path / "a.txt"
        file2 = tmp_path / "b.txt"

        file1.write_text("content A")
        file2.write_text("content B")

        assert files_are_identical(file1, file2) is False

    def test_files_are_identical_different_size(self, tmp_path: Path):
        """Test files_are_identical returns False quickly for different sizes."""
        file1 = tmp_path / "short.txt"
        file2 = tmp_path / "long.txt"

        file1.write_text("short")
        file2.write_text("this is a much longer file")

        # Should return False without computing hash (size check)
        assert files_are_identical(file1, file2) is False


class TestDeduplication:
    """Tests for duplicate file detection and handling."""

    def test_duplicate_deletes_source(self, tmp_path: Path):
        """Test that identical file is deleted instead of renamed."""
        content = "identical content for both files"

        # Create source file
        source = tmp_path / "source" / "doc.txt"
        source.parent.mkdir()
        source.write_text(content)

        # Create existing destination with same content
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        existing = dest_dir / "doc.txt"
        existing.write_text(content)

        mover = FileMover(deduplicate=True)
        result = mover.move(source, dest_dir)

        assert result.success is True
        assert result.action == "deleted duplicate"
        assert not source.exists()  # Source should be deleted
        assert existing.exists()  # Destination unchanged
        assert existing.read_text() == content

    def test_duplicate_dry_run(self, tmp_path: Path):
        """Test dry-run mode for duplicate detection."""
        content = "identical content"

        source = tmp_path / "source.txt"
        source.write_text(content)

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        existing = dest_dir / "source.txt"
        existing.write_text(content)

        mover = FileMover(dry_run=True, deduplicate=True)
        result = mover.move(source, dest_dir)

        assert result.success is True
        assert result.action == "would delete duplicate"
        assert source.exists()  # Source should still exist in dry-run

    def test_duplicate_disabled(self, tmp_path: Path):
        """Test that deduplication can be disabled."""
        content = "same content"

        source = tmp_path / "source.txt"
        source.write_text(content)

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        existing = dest_dir / "source.txt"
        existing.write_text(content)

        # Disable deduplication - should rename instead
        mover = FileMover(deduplicate=False, conflict_strategy=ConflictStrategy.RENAME)
        result = mover.move(source, dest_dir)

        assert result.success is True
        assert result.action == "moved"
        assert result.destination == dest_dir / "source_1.txt"
        assert (dest_dir / "source_1.txt").exists()

    def test_different_content_not_duplicate(self, tmp_path: Path):
        """Test that files with different content are not treated as duplicates."""
        source = tmp_path / "new.txt"
        source.write_text("new content")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        existing = dest_dir / "new.txt"
        existing.write_text("old content")

        mover = FileMover(deduplicate=True, conflict_strategy=ConflictStrategy.RENAME)
        result = mover.move(source, dest_dir)

        assert result.success is True
        assert result.action == "moved"
        assert result.destination == dest_dir / "new_1.txt"
        assert existing.read_text() == "old content"

    def test_convenience_function_deduplicate(self, tmp_path: Path):
        """Test move_classified_file with deduplication."""
        content = "duplicate content"

        source = tmp_path / "invoice.pdf"
        source.write_text(content)

        target = tmp_path / "Archives"
        target.mkdir()
        existing = target / "invoice.pdf"
        existing.write_text(content)

        result = move_classified_file(source, target, deduplicate=True)

        assert result.success is True
        assert result.action == "deleted duplicate"
        assert not source.exists()
