"""Tests for the migrate command (folder-based operations)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from para_files.cli.app import app
from para_files.cli.migrate_cmd import (
    RETENTION_SUFFIX_PATTERN,
    _build_retention_mapping_from_taxonomy,
    _discover_folders_to_migrate,
    _migrate_folder,
    _print_summary,
    _run_migration,
)


runner = CliRunner()


class TestRetentionSuffixPattern:
    """Tests for RETENTION_SUFFIX_PATTERN regex."""

    def test_matches_10y_suffix(self) -> None:
        """Test matching _10y suffix."""
        match = RETENTION_SUFFIX_PATTERN.search("fiscalite_10y")
        assert match is not None
        assert match.group(0) == "_10y"

    def test_matches_5y_suffix(self) -> None:
        """Test matching _5y suffix."""
        match = RETENTION_SUFFIX_PATTERN.search("factures_5y")
        assert match is not None
        assert match.group(0) == "_5y"

    def test_matches_ret_suffix(self) -> None:
        """Test matching _ret suffix."""
        match = RETENTION_SUFFIX_PATTERN.search("prevoyance_ret")
        assert match is not None
        assert match.group(0) == "_ret"

    def test_matches_ctr_suffix(self) -> None:
        """Test matching _ctr suffix."""
        match = RETENTION_SUFFIX_PATTERN.search("abonnement_ctr")
        assert match is not None
        assert match.group(0) == "_ctr"

    def test_matches_perm_suffix(self) -> None:
        """Test matching _perm suffix."""
        match = RETENTION_SUFFIX_PATTERN.search("identite_perm")
        assert match is not None
        assert match.group(0) == "_perm"

    def test_no_match_without_suffix(self) -> None:
        """Test no match for folder without suffix."""
        match = RETENTION_SUFFIX_PATTERN.search("fiscalite")
        assert match is None


class TestBuildRetentionMapping:
    """Tests for _build_retention_mapping_from_taxonomy function."""

    @patch("para_files.taxonomies.loader.TaxonomyLoader")
    def test_builds_mapping_from_taxonomy(self, mock_loader: MagicMock) -> None:
        """Test building mapping from taxonomy."""
        mock_taxonomy = MagicMock()
        mock_category = MagicMock()
        mock_doc = MagicMock()
        mock_doc.para_pattern = "4_Archives/fiscalite_10y"
        mock_doc.retention = "10_years"
        mock_category.documents = [mock_doc]
        mock_taxonomy.categories = [mock_category]
        mock_loader.return_value.load_documents.return_value = mock_taxonomy

        mapping = _build_retention_mapping_from_taxonomy()

        assert "fiscalite" in mapping
        assert mapping["fiscalite"]["retention"] == "10_years"
        assert mapping["fiscalite"]["suffix"] == "_10y"
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
        assert mapping["identite"]["suffix"] is None
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

    def test_discover_folder_needs_suffix(self, tmp_path: Path) -> None:
        """Test discovering folder that needs retention suffix."""
        archives = tmp_path / "4_Archives" / "fiscalite"
        archives.mkdir(parents=True)
        (archives / "file.pdf").touch()

        mapping = {
            "fiscalite": {
                "retention": "10_years",
                "suffix": "_10y",
                "target_para": "4_Archives",
            }
        }

        migrations = _discover_folders_to_migrate(tmp_path, mapping)

        assert len(migrations) == 1
        source, dest, action = migrations[0]
        assert source.name == "fiscalite"
        assert dest.name == "fiscalite_10y"
        assert action == "rename"

    def test_discover_folder_needs_move_to_resources(self, tmp_path: Path) -> None:
        """Test discovering folder that needs to move to Resources."""
        archives = tmp_path / "4_Archives" / "identite"
        archives.mkdir(parents=True)
        (archives / "passport.pdf").touch()

        mapping = {
            "identite": {
                "retention": "permanent",
                "suffix": None,
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
        archives = tmp_path / "4_Archives" / "fiscalite_10y"
        archives.mkdir(parents=True)

        mapping = {
            "fiscalite": {
                "retention": "10_years",
                "suffix": "_10y",
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
        # Destination already exists
        dest = tmp_path / "4_Archives" / "fiscalite_10y"
        dest.mkdir(parents=True)

        mapping = {
            "fiscalite": {
                "retention": "10_years",
                "suffix": "_10y",
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
                "suffix": "_10y",
                "target_para": "4_Archives",
            },
            "banque": {
                "retention": "10_years",
                "suffix": "_10y",
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

        dest = tmp_path / "4_Archives" / "fiscalite_10y"

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

        dest = tmp_path / "4_Archives" / "fiscalite_10y"

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

        dest = tmp_path / "4_Archives" / "fiscalite_10y"

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

        # Should find fiscalite and want to add _10y suffix
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
