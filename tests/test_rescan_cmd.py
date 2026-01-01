"""Tests for the rescan command."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from para_files.cli.app import app
from para_files.cli.rescan_cmd import (
    _build_expected_path,
    _cleanup_empty_dirs,
    _discover_archive_files,
    _move_file,
    _needs_migration,
    _print_summary,
    _run_rescan,
)
from para_files.config import Config


@pytest.fixture
def mock_config(tmp_path: Path, fixtures_dir: Path) -> Config:
    """Create a test configuration."""
    return Config(
        para_root=tmp_path,
        reference_tree_path=fixtures_dir / "test_reference_tree.yaml",
    )


runner = CliRunner()


class TestDiscoverArchiveFiles:
    """Tests for _discover_archive_files function."""

    def test_discover_files_in_archives(self, tmp_path: Path) -> None:
        """Test discovering files in 4_Archives."""
        archives = tmp_path / "4_Archives" / "fiscalite" / "2024"
        archives.mkdir(parents=True)
        (archives / "tax_return.pdf").touch()
        (archives / "receipt.pdf").touch()

        files = list(_discover_archive_files(tmp_path))
        assert len(files) == 2

    def test_discover_files_in_resources(self, tmp_path: Path) -> None:
        """Test discovering files in 3_Resources."""
        resources = tmp_path / "3_Resources" / "identite"
        resources.mkdir(parents=True)
        (resources / "passport.pdf").touch()

        files = list(_discover_archive_files(tmp_path))
        assert len(files) == 1

    def test_discover_with_category_filter(self, tmp_path: Path) -> None:
        """Test discovering files with category filter."""
        # Create files in different categories
        fiscal = tmp_path / "4_Archives" / "fiscalite" / "2024"
        fiscal.mkdir(parents=True)
        (fiscal / "tax.pdf").touch()

        sante = tmp_path / "4_Archives" / "sante" / "2024"
        sante.mkdir(parents=True)
        (sante / "medical.pdf").touch()

        files = list(_discover_archive_files(tmp_path, category_filter="fiscalite"))
        assert len(files) == 1
        assert files[0].name == "tax.pdf"

    def test_discover_empty_directory(self, tmp_path: Path) -> None:
        """Test discovering in empty directory."""
        (tmp_path / "4_Archives").mkdir()
        files = list(_discover_archive_files(tmp_path))
        assert len(files) == 0

    def test_discover_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test discovering when folders don't exist."""
        files = list(_discover_archive_files(tmp_path))
        assert len(files) == 0


class TestNeedsMigration:
    """Tests for _needs_migration function."""

    def test_needs_migration_different_paths(self, tmp_path: Path) -> None:
        """Test file needing migration."""
        current = tmp_path / "old" / "file.pdf"
        expected = tmp_path / "new" / "file.pdf"
        assert _needs_migration(current, expected) is True

    def test_no_migration_same_path(self, tmp_path: Path) -> None:
        """Test file already in correct location."""
        path = tmp_path / "correct" / "file.pdf"
        assert _needs_migration(path, path) is False


class TestBuildExpectedPath:
    """Tests for _build_expected_path function."""

    def test_build_path_with_category(self, tmp_path: Path) -> None:
        """Test building expected path."""
        file_path = tmp_path / "old" / "document.pdf"
        result = MagicMock()
        result.category = "4_Archives/10y_fiscalite/2024"

        expected = _build_expected_path(file_path, result, tmp_path)
        assert expected == tmp_path / "4_Archives/10y_fiscalite/2024" / "document.pdf"

    def test_build_path_no_category(self, tmp_path: Path) -> None:
        """Test building path with no category."""
        file_path = tmp_path / "old" / "document.pdf"
        result = MagicMock()
        result.category = None

        expected = _build_expected_path(file_path, result, tmp_path)
        assert expected is None


class TestMoveFile:
    """Tests for _move_file function."""

    def test_dry_run_move(self, tmp_path: Path) -> None:
        """Test dry run move."""
        source = tmp_path / "source" / "file.pdf"
        source.parent.mkdir(parents=True)
        source.touch()

        dest = tmp_path / "dest" / "file.pdf"

        result = _move_file(source, dest, dry_run=True)

        assert result["success"] is True
        assert result["action"] == "would_move"
        assert source.exists()  # File should not be moved
        assert not dest.exists()

    def test_actual_move(self, tmp_path: Path) -> None:
        """Test actual file move."""
        source = tmp_path / "source" / "file.pdf"
        source.parent.mkdir(parents=True)
        source.write_text("content")

        dest = tmp_path / "dest" / "file.pdf"

        result = _move_file(source, dest, dry_run=False)

        assert result["success"] is True
        assert result["action"] == "moved"
        assert not source.exists()
        assert dest.exists()
        assert dest.read_text() == "content"

    def test_move_destination_exists(self, tmp_path: Path) -> None:
        """Test move when destination already exists."""
        source = tmp_path / "source" / "file.pdf"
        source.parent.mkdir(parents=True)
        source.touch()

        dest = tmp_path / "dest" / "file.pdf"
        dest.parent.mkdir(parents=True)
        dest.touch()

        result = _move_file(source, dest, dry_run=False)

        assert result["action"] == "skipped"
        assert "Destination already exists" in result["message"]

    def test_move_error_handling(self, tmp_path: Path) -> None:
        """Test move error handling."""
        source = tmp_path / "nonexistent" / "file.pdf"
        dest = tmp_path / "dest" / "file.pdf"

        result = _move_file(source, dest, dry_run=False)

        assert result["success"] is False
        assert result["action"] == "error"


class TestCleanupEmptyDirs:
    """Tests for _cleanup_empty_dirs function."""

    def test_cleanup_empty_dirs_dry_run(self, tmp_path: Path) -> None:
        """Test cleanup in dry run mode."""
        empty_dir = tmp_path / "4_Archives" / "old_category"
        empty_dir.mkdir(parents=True)

        removed = _cleanup_empty_dirs(tmp_path, dry_run=True)

        assert len(removed) == 1
        assert empty_dir.exists()  # Should not actually remove

    def test_cleanup_empty_dirs_actual(self, tmp_path: Path) -> None:
        """Test actual cleanup of empty directories."""
        empty_dir = tmp_path / "4_Archives" / "old_category" / "subdir"
        empty_dir.mkdir(parents=True)

        removed = _cleanup_empty_dirs(tmp_path, dry_run=False)

        assert len(removed) == 2  # Both old_category and subdir
        assert not empty_dir.exists()

    def test_cleanup_preserves_non_empty(self, tmp_path: Path) -> None:
        """Test that non-empty directories are preserved."""
        non_empty = tmp_path / "4_Archives" / "active"
        non_empty.mkdir(parents=True)
        (non_empty / "file.pdf").touch()

        removed = _cleanup_empty_dirs(tmp_path, dry_run=False)

        assert len(removed) == 0
        assert non_empty.exists()


class TestPrintSummary:
    """Tests for _print_summary function."""

    def test_print_dry_run_summary(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test printing dry run summary."""
        results: dict[str, Any] = {
            "files_scanned": 100,
            "files_need_move": 25,
            "files_moved": 25,
            "files_skipped": 0,
            "files_errored": 0,
            "empty_dirs_removed": 0,
        }

        _print_summary(results, dry_run=True)
        captured = capsys.readouterr()

        assert "Files scanned" in captured.out
        assert "100" in captured.out
        assert "Would move" in captured.out
        assert "dry run" in captured.out.lower()

    def test_print_actual_summary(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test printing actual rescan summary."""
        results: dict[str, Any] = {
            "files_scanned": 100,
            "files_need_move": 25,
            "files_moved": 20,
            "files_skipped": 3,
            "files_errored": 2,
            "empty_dirs_removed": 5,
        }

        _print_summary(results, dry_run=False)
        captured = capsys.readouterr()

        assert "Moved" in captured.out
        assert "20" in captured.out
        assert "Errors" in captured.out


class TestRunRescan:
    """Tests for _run_rescan function."""

    def test_run_rescan_empty_dir(self, tmp_path: Path, mock_config: Config) -> None:
        """Test running rescan on empty directory."""
        (tmp_path / "4_Archives").mkdir()

        results = _run_rescan(
            tmp_path,
            mock_config,
            dry_run=True,
            category=None,
            output_json=True,
            verbose=False,
            cleanup=False,
        )

        assert results["files_scanned"] == 0
        assert results["files_need_move"] == 0

    @patch("para_files.cli.rescan_cmd._classify_for_rescan")
    def test_run_rescan_with_files(
        self, mock_classify: MagicMock, tmp_path: Path, mock_config: Config
    ) -> None:
        """Test running rescan with files."""
        # Create test file
        archives = tmp_path / "4_Archives" / "old" / "2024"
        archives.mkdir(parents=True)
        test_file = archives / "document.pdf"
        test_file.touch()

        # Mock classification result
        mock_result = MagicMock()
        mock_result.category = "4_Archives/10y_fiscalite/2024"
        mock_classify.return_value = mock_result

        results = _run_rescan(
            tmp_path,
            mock_config,
            dry_run=True,
            category=None,
            output_json=True,
            verbose=False,
            cleanup=False,
        )

        assert results["files_scanned"] == 1
        assert results["files_need_move"] == 1

    @patch("para_files.cli.rescan_cmd._classify_for_rescan")
    def test_run_rescan_no_category(
        self, mock_classify: MagicMock, tmp_path: Path, mock_config: Config
    ) -> None:
        """Test rescan when classification returns no category."""
        archives = tmp_path / "4_Archives" / "misc"
        archives.mkdir(parents=True)
        (archives / "unknown.pdf").touch()

        mock_result = MagicMock()
        mock_result.category = None
        mock_classify.return_value = mock_result

        results = _run_rescan(
            tmp_path,
            mock_config,
            dry_run=True,
            category=None,
            output_json=True,
            verbose=False,
            cleanup=False,
        )

        assert results["files_scanned"] == 1
        assert results["files_need_move"] == 0


class TestRescanCommand:
    """Tests for the rescan CLI command."""

    @patch("para_files.cli.rescan_cmd.load_config_or_exit")
    @patch("para_files.cli.rescan_cmd._run_rescan")
    def test_rescan_command_help(self, mock_run: MagicMock, mock_config: MagicMock) -> None:
        """Test rescan command help."""
        result = runner.invoke(app, ["rescan", "--help"])
        assert result.exit_code == 0
        assert "Re-classify files" in result.output

    @patch("para_files.cli.rescan_cmd.load_config_or_exit")
    @patch("para_files.cli.rescan_cmd._run_rescan")
    def test_rescan_command_dry_run(
        self, mock_run: MagicMock, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test rescan command in dry run mode."""
        mock_run.return_value = {
            "files_scanned": 10,
            "files_need_move": 5,
            "files_moved": 5,
            "files_skipped": 0,
            "files_errored": 0,
            "empty_dirs_removed": 0,
            "dry_run": True,
        }

        result = runner.invoke(app, ["rescan", str(tmp_path)])
        assert result.exit_code == 0

    @patch("para_files.cli.rescan_cmd.load_config_or_exit")
    @patch("para_files.cli.rescan_cmd._run_rescan")
    def test_rescan_command_json_output(
        self, mock_run: MagicMock, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test rescan command with JSON output."""
        mock_run.return_value = {
            "files_scanned": 10,
            "files_need_move": 5,
            "files_moved": 5,
            "files_skipped": 0,
            "files_errored": 0,
            "empty_dirs_removed": 0,
            "dry_run": True,
            "moves": [],
            "errors": [],
        }

        result = runner.invoke(app, ["rescan", str(tmp_path), "--json"])
        assert result.exit_code == 0
        assert "files_scanned" in result.output

    @patch("para_files.cli.rescan_cmd.load_config_or_exit")
    @patch("para_files.cli.rescan_cmd._run_rescan")
    def test_rescan_command_with_category(
        self, mock_run: MagicMock, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test rescan command with category filter."""
        mock_run.return_value = {
            "files_scanned": 5,
            "files_need_move": 3,
            "files_moved": 3,
            "files_skipped": 0,
            "files_errored": 0,
            "empty_dirs_removed": 0,
            "dry_run": True,
        }

        result = runner.invoke(app, ["rescan", str(tmp_path), "--category", "fiscalite"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["category"] == "fiscalite"
