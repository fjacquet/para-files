"""Tests for cleanup logging."""

from __future__ import annotations

import json
from pathlib import Path

from para_files.utils.cleanup_log import (
    CleanupLogEntry,
    CleanupLogger,
    get_default_log_path,
)


class TestCleanupLogEntry:
    """Test CleanupLogEntry dataclass."""

    def test_create_entry(self) -> None:
        """Test creating a log entry with current timestamp."""
        entry = CleanupLogEntry.create(
            action="deleted",
            path=Path("/tmp/test.txt"),
            file_type="junk_file",
            reason="Test deletion",
        )

        assert entry.action == "deleted"
        assert entry.path == "/tmp/test.txt"
        assert entry.file_type == "junk_file"
        assert entry.reason == "Test deletion"
        assert entry.dry_run is False
        assert entry.timestamp  # Should have a timestamp

    def test_create_dry_run_entry(self) -> None:
        """Test creating a dry-run log entry."""
        entry = CleanupLogEntry.create(
            action="would_delete",
            path=Path("/tmp/test.txt"),
            file_type="junk_file",
            reason="Test",
            dry_run=True,
        )

        assert entry.action == "would_delete"
        assert entry.dry_run is True


class TestCleanupLogger:
    """Test CleanupLogger class."""

    def test_init_without_log_path(self) -> None:
        """Test initializing logger without log path."""
        logger = CleanupLogger(log_path=None)

        assert logger.log_path is None
        assert logger.entries == []

    def test_init_with_log_path(self, tmp_path: Path) -> None:
        """Test initializing logger with log path."""
        log_path = tmp_path / "logs" / "cleanup.json"
        logger = CleanupLogger(log_path=log_path)

        assert logger.log_path == log_path
        assert log_path.parent.exists()  # Directory should be created

    def test_log_deleted(self, tmp_path: Path) -> None:
        """Test logging a deleted file."""
        logger = CleanupLogger(log_path=None)

        logger.log_deleted(
            path=tmp_path / "test.txt",
            file_type="junk_file",
            reason="Test",
            dry_run=False,
        )

        assert len(logger.entries) == 1
        assert logger.entries[0].action == "deleted"

    def test_log_would_delete_dry_run(self, tmp_path: Path) -> None:
        """Test logging a dry-run deletion."""
        logger = CleanupLogger(log_path=None)

        logger.log_deleted(
            path=tmp_path / "test.txt",
            file_type="junk_file",
            reason="Test",
            dry_run=True,
        )

        assert len(logger.entries) == 1
        assert logger.entries[0].action == "would_delete"

    def test_log_skipped(self, tmp_path: Path) -> None:
        """Test logging a skipped file."""
        logger = CleanupLogger(log_path=None)

        logger.log_skipped(
            path=tmp_path / "test.txt",
            file_type="normal_file",
            reason="Not a junk file",
        )

        assert len(logger.entries) == 1
        assert logger.entries[0].action == "skipped"

    def test_log_error(self, tmp_path: Path) -> None:
        """Test logging an error."""
        logger = CleanupLogger(log_path=None)

        logger.log_error(
            path=tmp_path / "test.txt",
            file_type="junk_file",
            reason="Permission denied",
        )

        assert len(logger.entries) == 1
        assert logger.entries[0].action == "error"

    def test_get_summary(self, tmp_path: Path) -> None:
        """Test getting summary of actions."""
        logger = CleanupLogger(log_path=None)

        # Add various entries
        logger.log_deleted(tmp_path / "a.txt", "junk", "test", dry_run=False)
        logger.log_deleted(tmp_path / "b.txt", "junk", "test", dry_run=False)
        logger.log_skipped(tmp_path / "c.txt", "normal", "not junk")
        logger.log_error(tmp_path / "d.txt", "junk", "error")

        summary = logger.get_summary()

        assert summary["deleted"] == 2
        assert summary["skipped"] == 1
        assert summary["error"] == 1
        assert summary["would_delete"] == 0

    def test_get_deleted_count(self, tmp_path: Path) -> None:
        """Test getting deleted count."""
        logger = CleanupLogger(log_path=None)

        logger.log_deleted(tmp_path / "a.txt", "junk", "test", dry_run=False)
        logger.log_deleted(tmp_path / "b.txt", "junk", "test", dry_run=True)  # Dry run

        assert logger.get_deleted_count() == 2  # Both count

    def test_write_log_creates_file(self, tmp_path: Path) -> None:
        """Test writing log creates the file."""
        log_path = tmp_path / "cleanup.json"
        logger = CleanupLogger(log_path=log_path)

        logger.log_deleted(tmp_path / "test.txt", "junk", "test", dry_run=False)
        logger.write_log()

        assert log_path.exists()

        # Verify content
        with log_path.open() as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["action"] == "deleted"

    def test_write_log_appends_to_existing(self, tmp_path: Path) -> None:
        """Test writing log appends to existing file."""
        log_path = tmp_path / "cleanup.json"

        # Create initial log
        initial_data = [{"action": "existing", "path": "/old", "timestamp": "2024-01-01"}]
        with log_path.open("w") as f:
            json.dump(initial_data, f)

        # Add new entry
        logger = CleanupLogger(log_path=log_path)
        logger.log_deleted(tmp_path / "new.txt", "junk", "test", dry_run=False)
        logger.write_log()

        # Verify both entries
        with log_path.open() as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]["action"] == "existing"
        assert data[1]["action"] == "deleted"

    def test_write_log_no_entries(self, tmp_path: Path) -> None:
        """Test writing log with no entries does nothing."""
        log_path = tmp_path / "cleanup.json"
        logger = CleanupLogger(log_path=log_path)

        logger.write_log()

        assert not log_path.exists()

    def test_write_log_no_path(self) -> None:
        """Test writing log without path does nothing."""
        logger = CleanupLogger(log_path=None)
        logger.log_deleted(Path("/tmp/test"), "junk", "test", dry_run=False)

        logger.write_log()  # Should not raise


class TestGetDefaultLogPath:
    """Test get_default_log_path function."""

    def test_returns_expected_path(self, tmp_path: Path) -> None:
        """Test returns expected log path structure."""
        log_path = get_default_log_path(tmp_path)

        assert log_path == tmp_path / "logs" / "cleanup-log.json"

    def test_handles_expanduser(self) -> None:
        """Test handles home directory in path."""
        log_path = get_default_log_path(Path("~/PARA"))

        assert "logs" in str(log_path)
        assert "cleanup-log.json" in str(log_path)
