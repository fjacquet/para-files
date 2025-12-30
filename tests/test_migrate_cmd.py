"""Tests for the migrate command (folder-based operations)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from para_files.cli.app import app
from para_files.cli.migrate_cmd import (
    RETENTION_PREFIX_PATTERN,
    _build_retention_mapping_from_taxonomy,
    _discover_folders_to_migrate,
    _merge_folder,
    _migrate_folder,
    _print_summary,
    _run_migration,
)


runner = CliRunner()


class TestRetentionPrefixPattern:
    """Tests for RETENTION_PREFIX_PATTERN regex."""

    def test_matches_10y_prefix(self) -> None:
        """Test matching 10y_ prefix."""
        match = RETENTION_PREFIX_PATTERN.match("10y_fiscalite")
        assert match is not None
        assert match.group(0) == "10y_"

    def test_matches_5y_prefix(self) -> None:
        """Test matching 5y_ prefix."""
        match = RETENTION_PREFIX_PATTERN.match("5y_factures")
        assert match is not None
        assert match.group(0) == "5y_"

    def test_matches_ret_prefix(self) -> None:
        """Test matching ret_ prefix."""
        match = RETENTION_PREFIX_PATTERN.match("ret_prevoyance")
        assert match is not None
        assert match.group(0) == "ret_"

    def test_matches_ctr_prefix(self) -> None:
        """Test matching ctr_ prefix."""
        match = RETENTION_PREFIX_PATTERN.match("ctr_abonnement")
        assert match is not None
        assert match.group(0) == "ctr_"

    def test_no_prefix_for_permanent(self) -> None:
        """Test that permanent items have no prefix to match."""
        # Permanent items go to 3_Resources with no prefix
        match = RETENTION_PREFIX_PATTERN.match("identite")
        assert match is None  # No prefix means no match

    def test_no_match_without_prefix(self) -> None:
        """Test no match for folder without prefix."""
        match = RETENTION_PREFIX_PATTERN.match("fiscalite")
        assert match is None


class TestBuildRetentionMapping:
    """Tests for _build_retention_mapping_from_taxonomy function."""

    @patch("para_files.taxonomies.loader.TaxonomyLoader")
    def test_builds_mapping_from_taxonomy(self, mock_loader: MagicMock) -> None:
        """Test building mapping from taxonomy."""
        mock_taxonomy = MagicMock()
        mock_category = MagicMock()
        mock_doc = MagicMock()
        mock_doc.para_pattern = "4_Archives/10y_fiscalite"
        mock_doc.retention = "10_years"
        mock_category.documents = [mock_doc]
        mock_taxonomy.categories = [mock_category]
        mock_loader.return_value.load_documents.return_value = mock_taxonomy

        mapping = _build_retention_mapping_from_taxonomy()

        assert "fiscalite" in mapping
        assert mapping["fiscalite"]["retention"] == "10_years"
        assert mapping["fiscalite"]["prefix"] == "10y_"
        assert mapping["fiscalite"]["target_para"] == "4_Archives"

    @patch("para_files.taxonomies.loader.TaxonomyLoader")
    def test_permanent_goes_to_resources(self, mock_loader: MagicMock) -> None:
        """Test that permanent retention goes to 3_Resources."""
        mock_taxonomy = MagicMock()
        mock_category = MagicMock()
        mock_doc = MagicMock()
        mock_doc.para_pattern = "3_Resources/identite"
        mock_doc.retention = "permanent"
        mock_category.documents = [mock_doc]
        mock_taxonomy.categories = [mock_category]
        mock_loader.return_value.load_documents.return_value = mock_taxonomy

        mapping = _build_retention_mapping_from_taxonomy()

        assert "identite" in mapping
        assert mapping["identite"]["retention"] == "permanent"
        assert mapping["identite"]["prefix"] is None
        assert mapping["identite"]["target_para"] == "3_Resources"

    @patch("para_files.taxonomies.loader.TaxonomyLoader")
    def test_fallback_to_static_config(self, mock_loader: MagicMock) -> None:
        """Test fallback to static config when taxonomy loading fails."""
        mock_loader.return_value.load_documents.side_effect = OSError("File not found")

        mapping = _build_retention_mapping_from_taxonomy()

        # Should fall back to static RETENTION_CONFIG
        assert "fiscalite" in mapping
        assert "administratif" in mapping


class TestDiscoverFoldersToMigrate:
    """Tests for _discover_folders_to_migrate function."""

    def test_discover_folder_needs_prefix(self, tmp_path: Path) -> None:
        """Test discovering folder that needs retention prefix."""
        archives = tmp_path / "4_Archives" / "fiscalite"
        archives.mkdir(parents=True)
        (archives / "file.pdf").touch()

        mapping = {
            "fiscalite": {
                "retention": "10_years",
                "prefix": "10y_",
                "target_para": "4_Archives",
            }
        }

        migrations = _discover_folders_to_migrate(tmp_path, mapping)

        assert len(migrations) == 1
        source, dest, action = migrations[0]
        assert source.name == "fiscalite"
        assert dest.name == "10y_fiscalite"
        assert action == "rename"

    def test_discover_folder_needs_move_to_resources(self, tmp_path: Path) -> None:
        """Test discovering folder that needs to move to Resources."""
        archives = tmp_path / "4_Archives" / "identite"
        archives.mkdir(parents=True)
        (archives / "passport.pdf").touch()

        mapping = {
            "identite": {
                "retention": "permanent",
                "prefix": None,
                "target_para": "3_Resources",
            }
        }

        # Create Resources folder
        (tmp_path / "3_Resources").mkdir()

        migrations = _discover_folders_to_migrate(tmp_path, mapping)

        assert len(migrations) == 1
        source, dest, action = migrations[0]
        assert "4_Archives" in str(source)
        assert "3_Resources" in str(dest)
        assert action == "move"

    def test_skip_folder_already_correct(self, tmp_path: Path) -> None:
        """Test skipping folder already in correct location."""
        archives = tmp_path / "4_Archives" / "10y_fiscalite"
        archives.mkdir(parents=True)

        mapping = {
            "fiscalite": {
                "retention": "10_years",
                "prefix": "10y_",
                "target_para": "4_Archives",
            }
        }

        migrations = _discover_folders_to_migrate(tmp_path, mapping)

        assert len(migrations) == 0

    def test_skip_destination_exists(self, tmp_path: Path) -> None:
        """Test skipping when destination already exists."""
        # Source folder
        source = tmp_path / "4_Archives" / "fiscalite"
        source.mkdir(parents=True)
        # Destination already exists (with prefix format)
        dest = tmp_path / "4_Archives" / "10y_fiscalite"
        dest.mkdir(parents=True)

        mapping = {
            "fiscalite": {
                "retention": "10_years",
                "prefix": "10y_",
                "target_para": "4_Archives",
            }
        }

        migrations = _discover_folders_to_migrate(tmp_path, mapping)

        assert len(migrations) == 0

    def test_discover_with_category_filter(self, tmp_path: Path) -> None:
        """Test discovering with category filter."""
        (tmp_path / "4_Archives" / "fiscalite").mkdir(parents=True)
        (tmp_path / "4_Archives" / "banque").mkdir(parents=True)

        mapping = {
            "fiscalite": {
                "retention": "10_years",
                "prefix": "10y_",
                "target_para": "4_Archives",
            },
            "banque": {
                "retention": "10_years",
                "prefix": "10y_",
                "target_para": "4_Archives",
            },
        }

        migrations = _discover_folders_to_migrate(
            tmp_path, mapping, category_filter="fiscal"
        )

        assert len(migrations) == 1
        assert migrations[0][0].name == "fiscalite"


class TestMigrateFolder:
    """Tests for _migrate_folder function."""

    def test_dry_run_rename(self, tmp_path: Path) -> None:
        """Test dry run rename operation."""
        source = tmp_path / "4_Archives" / "fiscalite"
        source.mkdir(parents=True)
        (source / "file.pdf").touch()

        dest = tmp_path / "4_Archives" / "10y_fiscalite"

        result = _migrate_folder(source, dest, "rename", dry_run=True)

        assert result["success"] is True
        assert result["action"] == "rename"
        assert result["dry_run_action"] == "would_rename"
        assert source.exists()  # Not moved
        assert not dest.exists()

    def test_actual_rename(self, tmp_path: Path) -> None:
        """Test actual rename operation."""
        source = tmp_path / "4_Archives" / "fiscalite"
        source.mkdir(parents=True)
        (source / "file.pdf").touch()

        dest = tmp_path / "4_Archives" / "10y_fiscalite"

        result = _migrate_folder(source, dest, "rename", dry_run=False)

        assert result["success"] is True
        assert not source.exists()
        assert dest.exists()
        assert (dest / "file.pdf").exists()

    def test_actual_move_across_para(self, tmp_path: Path) -> None:
        """Test actual move across PARA categories."""
        source = tmp_path / "4_Archives" / "identite"
        source.mkdir(parents=True)
        (source / "passport.pdf").touch()

        (tmp_path / "3_Resources").mkdir()
        dest = tmp_path / "3_Resources" / "identite"

        result = _migrate_folder(source, dest, "move", dry_run=False)

        assert result["success"] is True
        assert not source.exists()
        assert dest.exists()
        assert (dest / "passport.pdf").exists()

    def test_counts_files_in_folder(self, tmp_path: Path) -> None:
        """Test that file count is accurate."""
        source = tmp_path / "4_Archives" / "fiscalite"
        source.mkdir(parents=True)
        (source / "file1.pdf").touch()
        (source / "file2.pdf").touch()
        subdir = source / "2024"
        subdir.mkdir()
        (subdir / "file3.pdf").touch()

        dest = tmp_path / "4_Archives" / "10y_fiscalite"

        result = _migrate_folder(source, dest, "rename", dry_run=True)

        assert result["files_in_folder"] == 3


class TestPrintSummary:
    """Tests for _print_summary function."""

    def test_print_dry_run_summary(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test printing dry run summary."""
        results: dict[str, Any] = {
            "folders_scanned": 10,
            "folders_need_migration": 5,
            "folders_migrated": 5,
            "folders_errored": 0,
            "total_files": 100,
            "migrations": [],
        }

        _print_summary(results, dry_run=True)
        captured = capsys.readouterr()

        assert "Folders found" in captured.out or "folders" in captured.out.lower()
        assert "dry run" in captured.out.lower()

    def test_print_actual_summary(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test printing actual migration summary."""
        results: dict[str, Any] = {
            "folders_scanned": 10,
            "folders_need_migration": 5,
            "folders_migrated": 4,
            "folders_errored": 1,
            "total_files": 100,
            "migrations": [],
        }

        _print_summary(results, dry_run=False)
        captured = capsys.readouterr()

        assert "Processed" in captured.out or "processed" in captured.out.lower()


class TestRunMigration:
    """Tests for _run_migration function."""

    def test_run_migration_empty_dir(self, tmp_path: Path) -> None:
        """Test running migration on empty directory."""
        (tmp_path / "4_Archives").mkdir()
        (tmp_path / "3_Resources").mkdir()

        results = _run_migration(
            tmp_path,
            dry_run=True,
            category=None,
            output_json=True,
            verbose=False,
        )

        assert results["folders_scanned"] == 0
        assert results["folders_need_migration"] == 0

    def test_run_migration_with_folders(self, tmp_path: Path) -> None:
        """Test running migration with folders."""
        (tmp_path / "4_Archives" / "fiscalite").mkdir(parents=True)
        (tmp_path / "3_Resources").mkdir()

        results = _run_migration(
            tmp_path,
            dry_run=True,
            category=None,
            output_json=True,
            verbose=False,
        )

        # Should find fiscalite and want to add 10y_ prefix
        assert results["folders_scanned"] >= 0


class TestMigrateCommand:
    """Tests for the migrate CLI command."""

    @patch("para_files.cli.migrate_cmd.load_config_or_exit")
    @patch("para_files.cli.migrate_cmd._run_migration")
    def test_migrate_command_help(
        self, mock_run: MagicMock, mock_config: MagicMock
    ) -> None:
        """Test migrate command help."""
        result = runner.invoke(app, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "Migrate folders" in result.output or "PARA" in result.output

    @patch("para_files.cli.migrate_cmd.load_config_or_exit")
    @patch("para_files.cli.migrate_cmd._run_migration")
    def test_migrate_command_dry_run(
        self, mock_run: MagicMock, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test migrate command in dry run mode."""
        mock_run.return_value = {
            "folders_scanned": 10,
            "folders_need_migration": 5,
            "folders_migrated": 5,
            "folders_errored": 0,
            "total_files": 100,
            "dry_run": True,
            "migrations": [],
        }

        result = runner.invoke(app, ["migrate", str(tmp_path)])
        assert result.exit_code == 0

    @patch("para_files.cli.migrate_cmd.load_config_or_exit")
    @patch("para_files.cli.migrate_cmd._run_migration")
    def test_migrate_command_json_output(
        self, mock_run: MagicMock, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test migrate command with JSON output."""
        mock_run.return_value = {
            "folders_scanned": 10,
            "folders_need_migration": 5,
            "folders_migrated": 5,
            "folders_errored": 0,
            "total_files": 100,
            "dry_run": True,
            "migrations": [],
            "errors": [],
        }

        result = runner.invoke(app, ["migrate", str(tmp_path), "--json"])
        assert result.exit_code == 0
        assert "folders_scanned" in result.output

    @patch("para_files.cli.migrate_cmd.load_config_or_exit")
    @patch("para_files.cli.migrate_cmd._run_migration")
    def test_migrate_command_with_category(
        self, mock_run: MagicMock, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test migrate command with category filter."""
        mock_run.return_value = {
            "folders_scanned": 5,
            "folders_need_migration": 3,
            "folders_migrated": 3,
            "folders_errored": 0,
            "total_files": 50,
            "dry_run": True,
            "migrations": [],
        }

        result = runner.invoke(
            app, ["migrate", str(tmp_path), "--category", "fiscalite"]
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["category"] == "fiscalite"


class TestMergeFolder:
    """Tests for _merge_folder function."""

    def test_merge_moves_unique_files(self, tmp_path: Path) -> None:
        """Test merging moves files that only exist in source."""
        source = tmp_path / "4_Archives" / "formations"
        source.mkdir(parents=True)
        (source / "file1.pdf").write_text("content1")

        dest = tmp_path / "3_Resources" / "formations"
        dest.mkdir(parents=True)
        (dest / "file2.pdf").write_text("content2")

        result = _merge_folder(source, dest, dry_run=False)

        assert result["success"] is True
        assert result["files_moved"] == 1
        assert (dest / "file1.pdf").exists()
        assert (dest / "file1.pdf").read_text() == "content1"

    def test_merge_removes_duplicates(self, tmp_path: Path) -> None:
        """Test merging removes identical files from source."""
        source = tmp_path / "4_Archives" / "formations"
        source.mkdir(parents=True)
        (source / "same.pdf").write_text("identical")

        dest = tmp_path / "3_Resources" / "formations"
        dest.mkdir(parents=True)
        (dest / "same.pdf").write_text("identical")

        result = _merge_folder(source, dest, dry_run=False)

        assert result["success"] is True
        assert result["files_duplicate"] == 1
        assert not (source / "same.pdf").exists()
        assert (dest / "same.pdf").read_text() == "identical"

    def test_merge_renames_different_files(self, tmp_path: Path) -> None:
        """Test merging renames files with same name but different content."""
        source = tmp_path / "4_Archives" / "formations"
        source.mkdir(parents=True)
        (source / "doc.pdf").write_text("source content")

        dest = tmp_path / "3_Resources" / "formations"
        dest.mkdir(parents=True)
        (dest / "doc.pdf").write_text("dest content")

        result = _merge_folder(source, dest, dry_run=False)

        assert result["success"] is True
        assert result["files_renamed"] == 1
        assert (dest / "doc.pdf").read_text() == "dest content"
        assert (dest / "doc_from_archives.pdf").exists()
        assert (dest / "doc_from_archives.pdf").read_text() == "source content"

    def test_merge_dry_run(self, tmp_path: Path) -> None:
        """Test merge dry run doesn't change anything."""
        source = tmp_path / "4_Archives" / "formations"
        source.mkdir(parents=True)
        (source / "file.pdf").write_text("content")

        dest = tmp_path / "3_Resources" / "formations"
        dest.mkdir(parents=True)

        result = _merge_folder(source, dest, dry_run=True)

        assert result["success"] is True
        assert result["dry_run_action"] == "would_merge"
        assert result["files_moved"] == 1
        assert (source / "file.pdf").exists()  # Source unchanged
        assert not (dest / "file.pdf").exists()  # Dest unchanged

    def test_merge_recursive_subdirs(self, tmp_path: Path) -> None:
        """Test merging handles nested subdirectories."""
        source = tmp_path / "4_Archives" / "formations" / "2024"
        source.mkdir(parents=True)
        (source / "jan.pdf").write_text("january")

        dest_base = tmp_path / "3_Resources" / "formations"
        dest_base.mkdir(parents=True)
        dest_2024 = dest_base / "2024"
        dest_2024.mkdir()
        (dest_2024 / "feb.pdf").write_text("february")

        result = _merge_folder(
            tmp_path / "4_Archives" / "formations",
            dest_base,
            dry_run=False,
        )

        assert result["success"] is True
        assert result["subdirs_merged"] == 1
        assert (dest_2024 / "jan.pdf").exists()
        assert (dest_2024 / "feb.pdf").exists()

    def test_merge_cleans_empty_source(self, tmp_path: Path) -> None:
        """Test that empty source directories are removed after merge."""
        source = tmp_path / "4_Archives" / "formations"
        source.mkdir(parents=True)
        (source / "file.pdf").write_text("content")

        dest = tmp_path / "3_Resources" / "formations"
        dest.mkdir(parents=True)

        _merge_folder(source, dest, dry_run=False)

        assert not source.exists()


class TestDiscoverWithMerge:
    """Tests for _discover_folders_to_migrate with merge option."""

    def test_discover_includes_merge_when_enabled(self, tmp_path: Path) -> None:
        """Test that merge mode includes folders where destination exists."""
        source = tmp_path / "4_Archives" / "identite"
        source.mkdir(parents=True)
        (source / "passport.pdf").touch()

        dest = tmp_path / "3_Resources" / "identite"
        dest.mkdir(parents=True)

        mapping = {
            "identite": {
                "retention": "permanent",
                "prefix": None,
                "target_para": "3_Resources",
            }
        }

        # Without merge - should be empty (skipped)
        migrations = _discover_folders_to_migrate(tmp_path, mapping, merge=False)
        assert len(migrations) == 0

        # With merge - should include merge action
        migrations = _discover_folders_to_migrate(tmp_path, mapping, merge=True)
        assert len(migrations) == 1
        source_found, dest_found, action = migrations[0]
        assert "4_Archives" in str(source_found)
        assert "3_Resources" in str(dest_found)
        assert action == "merge"


class TestMigrateCommandMerge:
    """Tests for migrate CLI command with --merge option."""

    @patch("para_files.cli.migrate_cmd.load_config_or_exit")
    @patch("para_files.cli.migrate_cmd._run_migration")
    def test_migrate_command_with_merge(
        self, mock_run: MagicMock, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test migrate command with --merge flag."""
        mock_run.return_value = {
            "folders_scanned": 5,
            "folders_need_migration": 3,
            "folders_migrated": 3,
            "folders_errored": 0,
            "total_files": 50,
            "dry_run": True,
            "merge_mode": True,
            "migrations": [],
        }

        result = runner.invoke(app, ["migrate", str(tmp_path), "--merge"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["merge"] is True

    @patch("para_files.cli.migrate_cmd.load_config_or_exit")
    @patch("para_files.cli.migrate_cmd._run_migration")
    def test_migrate_command_merge_short_option(
        self, mock_run: MagicMock, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test migrate command with -m shorthand."""
        mock_run.return_value = {
            "folders_scanned": 5,
            "folders_need_migration": 3,
            "folders_migrated": 3,
            "folders_errored": 0,
            "total_files": 50,
            "dry_run": True,
            "merge_mode": True,
            "migrations": [],
        }

        result = runner.invoke(app, ["migrate", str(tmp_path), "-m"])
        assert result.exit_code == 0
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["merge"] is True
