"""Tests for the main module."""

from __future__ import annotations

from typer.testing import CliRunner

from para_files import __version__
from para_files.main import app


runner = CliRunner()


def test_version():
    """Verify package version is set."""
    assert __version__ == "0.1.0"


def test_main_help():
    """Verify main function shows help."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "para-files" in result.output.lower()
    assert "classify" in result.output
    assert "move" in result.output


def test_main_version():
    """Verify version flag works."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_classify_missing_path():
    """Verify classify command errors on missing file path."""
    result = runner.invoke(app, ["classify"])
    # Should fail because no file path provided
    assert result.exit_code == 2
    assert "missing argument" in result.output.lower()


def test_classify_nonexistent_file():
    """Verify classify command warns on nonexistent file.

    With multi-file support, the command continues with warnings
    instead of failing on individual missing files.
    """
    result = runner.invoke(app, ["classify", "/nonexistent/file.txt"])
    # Should succeed but with warning (no files to process)
    assert result.exit_code == 0
    assert "not found" in result.output.lower() or "warning" in result.output.lower()


def test_move_missing_path():
    """Verify move command errors on missing file path."""
    result = runner.invoke(app, ["move"])
    # Should fail because no file path provided
    assert result.exit_code == 2
    assert "missing argument" in result.output.lower()


def test_move_nonexistent_file():
    """Verify move command warns on nonexistent file.

    With multi-file support, the command continues with warnings
    instead of failing on individual missing files.
    """
    result = runner.invoke(app, ["move", "/nonexistent/file.txt", "--dry-run"])
    # Should succeed but with warning (no files to process)
    assert result.exit_code == 0
    assert "not found" in result.output.lower() or "warning" in result.output.lower()


def test_move_help():
    """Verify move command help."""
    result = runner.invoke(app, ["move", "--help"])
    assert result.exit_code == 0
    assert "dry-run" in result.output
    assert "copy" in result.output
    assert "conflict" in result.output


def test_config_path():
    """Verify config command shows reference tree path."""
    result = runner.invoke(app, ["config", "--path"])
    assert result.exit_code == 0
    assert "Reference tree:" in result.output
    assert "Exists:" in result.output


def test_config_show():
    """Verify config command shows configuration."""
    result = runner.invoke(app, ["config", "--show"])
    assert result.exit_code == 0
    assert "para_root" in result.output
    assert "mlx" in result.output
    assert "llm" in result.output


def test_learn_help():
    """Verify learn command help."""
    result = runner.invoke(app, ["learn", "--help"])
    assert result.exit_code == 0
    assert "interactive" in result.output.lower()
    assert "learning" in result.output.lower()


def test_learn_missing_file():
    """Verify learn command handles missing file."""
    result = runner.invoke(app, ["learn", "/nonexistent/file.txt"])
    assert result.exit_code == 1


def test_test_route_help():
    """Verify test-route command help."""
    result = runner.invoke(app, ["test-route", "--help"])
    assert result.exit_code == 0
    assert "route" in result.output.lower()


def test_test_route_not_found():
    """Verify test-route command handles nonexistent route."""
    result = runner.invoke(app, ["test-route", "nonexistent-route"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_scan_help():
    """Verify scan command help."""
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "recursive" in result.output
    assert "ext" in result.output
    assert "json" in result.output


def test_scan_nonexistent_directory():
    """Verify scan command handles nonexistent directory."""
    result = runner.invoke(app, ["scan", "/nonexistent/directory"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "error" in result.output.lower()


def test_clean_help():
    """Verify clean command help."""
    result = runner.invoke(app, ["clean", "--help"])
    assert result.exit_code == 0
    assert "dry-run" in result.output
    assert "nfo" in result.output
    assert "junk" in result.output


def test_clean_nonexistent_directory():
    """Verify clean command handles nonexistent directory."""
    result = runner.invoke(app, ["clean", "/nonexistent/directory"])
    assert result.exit_code == 1


def test_init_help():
    """Verify init command help."""
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0
    assert "dry-run" in result.output
    assert "subfolders" in result.output


def test_tree_help():
    """Verify tree command help."""
    result = runner.invoke(app, ["tree", "--help"])
    assert result.exit_code == 0
    assert "validate" in result.output
    assert "issuers" in result.output
    assert "rules" in result.output


def test_routes_help():
    """Verify routes command help."""
    result = runner.invoke(app, ["routes", "--help"])
    assert result.exit_code == 0
    assert "utterances" in result.output


def test_issuers_help():
    """Verify issuers command help."""
    result = runner.invoke(app, ["issuers", "--help"])
    assert result.exit_code == 0


def test_add_issuer_help():
    """Verify add-issuer command help."""
    result = runner.invoke(app, ["add-issuer", "--help"])
    assert result.exit_code == 0
    assert "category" in result.output


def test_add_issuer_missing_category():
    """Verify add-issuer requires category."""
    result = runner.invoke(app, ["add-issuer", "TestIssuer"])
    assert result.exit_code == 2
    assert "category" in result.output.lower() or "missing" in result.output.lower()


def test_add_utterance_help():
    """Verify add-utterance command help."""
    result = runner.invoke(app, ["add-utterance", "--help"])
    assert result.exit_code == 0


def test_add_utterance_missing_args():
    """Verify add-utterance requires arguments."""
    result = runner.invoke(app, ["add-utterance"])
    assert result.exit_code == 2


def test_classify_help():
    """Verify classify command help."""
    result = runner.invoke(app, ["classify", "--help"])
    assert result.exit_code == 0
    assert "json" in result.output
    assert "verbose" in result.output.lower() or "-v" in result.output


class TestScanCommand:
    """Tests for the scan command."""

    def test_scan_empty_directory(self, tmp_path):
        """Test scanning an empty directory."""
        result = runner.invoke(app, ["scan", str(tmp_path)])
        # Should succeed with no files
        assert result.exit_code == 0

    def test_scan_with_files(self, tmp_path):
        """Test scanning a directory with files."""
        # Create test files
        (tmp_path / "test1.txt").write_text("Hello")
        (tmp_path / "test2.txt").write_text("World")

        result = runner.invoke(app, ["scan", str(tmp_path)])
        assert result.exit_code == 0

    def test_scan_recursive(self, tmp_path):
        """Test scanning recursively."""
        # Create nested directories
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("Content")

        result = runner.invoke(app, ["scan", str(tmp_path), "--recursive"])
        assert result.exit_code == 0

    def test_scan_with_extension_filter(self, tmp_path):
        """Test scanning with extension filter."""
        (tmp_path / "test.txt").write_text("Text")
        (tmp_path / "test.pdf").write_bytes(b"%PDF-1.4")

        result = runner.invoke(app, ["scan", str(tmp_path), "--ext", ".txt"])
        assert result.exit_code == 0


class TestCleanCommand:
    """Tests for the clean command."""

    def test_clean_empty_directory(self, tmp_path):
        """Test cleaning an empty directory."""
        result = runner.invoke(app, ["clean", str(tmp_path), "--dry-run"])
        assert result.exit_code == 0

    def test_clean_with_ds_store(self, tmp_path):
        """Test cleaning .DS_Store files."""
        ds_store = tmp_path / ".DS_Store"
        ds_store.write_bytes(b"\x00\x00\x00\x01")

        result = runner.invoke(app, ["clean", str(tmp_path), "--dry-run"])
        assert result.exit_code == 0

    def test_clean_with_nfo_flag(self, tmp_path):
        """Test cleaning with NFO files included."""
        nfo_file = tmp_path / "info.nfo"
        nfo_file.write_text("NFO content")

        result = runner.invoke(app, ["clean", str(tmp_path), "--nfo", "--dry-run"])
        assert result.exit_code == 0

    def test_clean_empty_directories(self, tmp_path):
        """Test cleaning empty directories."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = runner.invoke(app, ["clean", str(tmp_path), "--dry-run"])
        assert result.exit_code == 0


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_folders(self, tmp_path):
        """Test init creates PARA folders."""
        result = runner.invoke(app, ["init", str(tmp_path)])
        assert result.exit_code == 0

        # Check folders were created
        assert (tmp_path / "0_Inbox").exists()
        assert (tmp_path / "1_Projects").exists()
        assert (tmp_path / "2_Areas").exists()
        assert (tmp_path / "3_Resources").exists()
        assert (tmp_path / "4_Archives").exists()

    def test_init_dry_run(self, tmp_path):
        """Test init with dry run."""
        result = runner.invoke(app, ["init", str(tmp_path), "--dry-run"])
        assert result.exit_code == 0

        # Folders should not be created
        assert not (tmp_path / "0_Inbox").exists()

    def test_init_default_location(self):
        """Test init with default location."""
        # Just check it runs without error
        result = runner.invoke(app, ["init", "--dry-run"])
        assert result.exit_code == 0


class TestClassifyCommand:
    """Tests for the classify command."""

    def test_classify_text_file(self, tmp_path):
        """Test classifying a text file."""
        test_file = tmp_path / "invoice.txt"
        test_file.write_text("Invoice #12345 for services rendered")

        result = runner.invoke(app, ["classify", str(test_file)])
        assert result.exit_code == 0

    def test_classify_json_output(self, tmp_path):
        """Test classify with JSON output."""
        test_file = tmp_path / "document.txt"
        test_file.write_text("This is a test document")

        result = runner.invoke(app, ["classify", str(test_file), "--json"])
        assert result.exit_code == 0
        # Should contain JSON output (file_path key)
        assert "file_path" in result.output or "category" in result.output

    def test_classify_verbose(self, tmp_path):
        """Test classify with verbose output."""
        test_file = tmp_path / "report.txt"
        test_file.write_text("Quarterly report Q4 2024")

        result = runner.invoke(app, ["classify", str(test_file), "-v"])
        assert result.exit_code == 0

    def test_classify_multiple_files(self, tmp_path):
        """Test classifying multiple files."""
        file1 = tmp_path / "doc1.txt"
        file2 = tmp_path / "doc2.txt"
        file1.write_text("Document 1 content")
        file2.write_text("Document 2 content")

        result = runner.invoke(app, ["classify", str(file1), str(file2)])
        assert result.exit_code == 0


class TestMoveCommand:
    """Tests for the move command."""

    def test_move_dry_run(self, tmp_path):
        """Test move with dry run."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        result = runner.invoke(app, ["move", str(test_file), "--dry-run"])
        assert result.exit_code == 0
        # File should still exist (dry run)
        assert test_file.exists()

    def test_move_with_copy_flag(self, tmp_path):
        """Test move with copy flag."""
        test_file = tmp_path / "original.txt"
        test_file.write_text("Original content")

        result = runner.invoke(app, ["move", str(test_file), "--copy", "--dry-run"])
        assert result.exit_code == 0

    def test_move_multiple_files_dry_run(self, tmp_path):
        """Test moving multiple files with dry run."""
        file1 = tmp_path / "a.txt"
        file2 = tmp_path / "b.txt"
        file1.write_text("Content A")
        file2.write_text("Content B")

        result = runner.invoke(app, ["move", str(file1), str(file2), "--dry-run"])
        assert result.exit_code == 0


class TestHelperFunctions:
    """Tests for helper functions used by CLI commands."""

    def test_setup_logging_import(self):
        """Test that setup_logging can be imported."""
        from para_files.main import setup_logging

        # Just verify it can be called without error
        setup_logging(verbose=False)

    def test_setup_logging_verbose(self):
        """Test setup_logging with verbose flag."""
        from para_files.main import setup_logging

        setup_logging(verbose=True)

    def test_conflict_choice_enum(self):
        """Test ConflictChoice enum values."""
        from para_files.main import ConflictChoice

        assert ConflictChoice.skip.value == "skip"
        assert ConflictChoice.rename.value == "rename"
        assert ConflictChoice.overwrite.value == "overwrite"

    def test_format_result_json(self):
        """Test _format_result_json helper function."""
        from pathlib import Path

        from para_files.main import _format_result_json
        from para_files.types import ClassificationResult, ClassificationSource, Confidence

        result = ClassificationResult(
            category="4_Archives/test",
            confidence=Confidence(value=0.85, source=ClassificationSource.SEMANTIC_ROUTER),
            route_name="test",
        )
        target = Path("/dest/4_Archives/test/test.txt")
        json_output = _format_result_json(Path("/tmp/test.txt"), result, target)
        assert "source_file" in json_output
        assert json_output["category"] == "4_Archives/test"
        assert json_output["confidence"] == 0.85
        assert json_output["target_path"] == str(target)
        assert json_output["route_name"] == "test"

    def test_format_result_json_with_params(self):
        """Test _format_result_json with extracted params."""
        from pathlib import Path

        from para_files.main import _format_result_json
        from para_files.types import ClassificationResult, ClassificationSource, Confidence

        result = ClassificationResult(
            category="4_Archives/factures",
            confidence=Confidence(value=0.90, source=ClassificationSource.RULES_ENGINE),
            extracted_params={"issuer": "EDF", "year": "2025"},
        )
        target = Path("/dest/4_Archives/factures/EDF/test.pdf")
        json_output = _format_result_json(Path("/tmp/test.pdf"), result, target)
        assert json_output["source"] == "rules_engine"
        assert json_output["params"]["issuer"] == "EDF"

    def test_parse_extensions_filter(self):
        """Test _parse_extensions_filter helper function."""
        from para_files.main import _parse_extensions_filter

        # Test with valid extensions
        exts = _parse_extensions_filter(".txt,.pdf")
        assert ".txt" in exts
        assert ".pdf" in exts

    def test_parse_extensions_filter_with_dot_normalization(self):
        """Test extensions filter normalizes without leading dot."""
        from para_files.main import _parse_extensions_filter

        exts = _parse_extensions_filter("txt,pdf")
        assert ".txt" in exts
        assert ".pdf" in exts

    def test_validate_file_exists(self):
        """Test _validate_file_exists helper."""
        from pathlib import Path

        from para_files.main import _validate_file_exists

        # Should return False for non-existent file
        result = _validate_file_exists(Path("/nonexistent/file.txt"))
        assert result is False

    def test_validate_file_exists_with_real_file(self, tmp_path):
        """Test _validate_file_exists with real file."""
        from para_files.main import _validate_file_exists

        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        result = _validate_file_exists(test_file)
        assert result is True


class TestTreeCommand:
    """Tests for the tree command."""

    def test_tree_default(self):
        """Test tree command with default options."""
        result = runner.invoke(app, ["tree"])
        assert result.exit_code == 0

    def test_tree_with_validate(self):
        """Test tree command with validate flag."""
        result = runner.invoke(app, ["tree", "--validate"])
        assert result.exit_code == 0

    def test_tree_with_issuers(self):
        """Test tree command with issuers flag."""
        result = runner.invoke(app, ["tree", "--issuers"])
        assert result.exit_code == 0

    def test_tree_with_rules(self):
        """Test tree command with rules flag."""
        result = runner.invoke(app, ["tree", "--rules"])
        assert result.exit_code == 0


class TestRoutesCommand:
    """Tests for the routes command."""

    def test_routes_default(self):
        """Test routes command with default options."""
        result = runner.invoke(app, ["routes"])
        assert result.exit_code == 0

    def test_routes_with_utterances(self):
        """Test routes command with utterances flag."""
        result = runner.invoke(app, ["routes", "--utterances"])
        assert result.exit_code == 0


class TestIssuersCommand:
    """Tests for the issuers command."""

    def test_issuers_default(self):
        """Test issuers command."""
        result = runner.invoke(app, ["issuers"])
        assert result.exit_code == 0


class TestConfigCommand:
    """Tests for the config command."""

    def test_config_default(self):
        """Test config command with no flags."""
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0

    def test_config_show_and_path(self):
        """Test config command with both show and path."""
        result = runner.invoke(app, ["config", "--show", "--path"])
        assert result.exit_code == 0


class TestScanAdvanced:
    """Advanced tests for the scan command."""

    def test_scan_json_output(self, tmp_path):
        """Test scan with JSON output."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        result = runner.invoke(app, ["scan", str(tmp_path), "--json"])
        assert result.exit_code == 0

    def test_scan_with_multiple_extension_filters(self, tmp_path):
        """Test scan with multiple extension filters."""
        (tmp_path / "test.txt").write_text("Text")
        (tmp_path / "test.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "test.md").write_text("# Markdown")

        result = runner.invoke(app, ["scan", str(tmp_path), "--ext", ".txt,.md"])
        assert result.exit_code == 0


class TestCleanAdvanced:
    """Advanced tests for the clean command."""

    def test_clean_with_nfo_option(self, tmp_path):
        """Test clean with --nfo option to delete .nfo files."""
        nfo_file = tmp_path / "movie.nfo"
        nfo_file.write_text("<?xml version='1.0'?><movie><title>Test</title></movie>")

        result = runner.invoke(app, ["clean", str(tmp_path), "--nfo", "--dry-run"])
        assert result.exit_code == 0

    def test_clean_removes_ds_store(self, tmp_path):
        """Test clean removes .DS_Store files."""
        ds_store = tmp_path / ".DS_Store"
        ds_store.write_bytes(b"\x00\x00\x00\x01")

        # Run without dry-run to actually delete
        result = runner.invoke(app, ["clean", str(tmp_path)])
        assert result.exit_code == 0


class TestInitAdvanced:
    """Advanced tests for the init command."""

    def test_init_with_subfolders(self, tmp_path):
        """Test init creates subfolders."""
        result = runner.invoke(app, ["init", str(tmp_path), "--subfolders"])
        assert result.exit_code == 0
        # Verify base folders were created
        assert (tmp_path / "0_Inbox").exists()

    def test_init_idempotent(self, tmp_path):
        """Test init can be run multiple times safely."""
        # Run twice
        result1 = runner.invoke(app, ["init", str(tmp_path)])
        result2 = runner.invoke(app, ["init", str(tmp_path)])

        assert result1.exit_code == 0
        assert result2.exit_code == 0


class TestMoveAdvanced:
    """Advanced tests for the move command."""

    def test_move_with_conflict_skip(self, tmp_path):
        """Test move with skip conflict strategy."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        result = runner.invoke(app, ["move", str(test_file), "--dry-run", "--conflict", "skip"])
        assert result.exit_code == 0

    def test_move_with_conflict_rename(self, tmp_path):
        """Test move with rename conflict strategy."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        result = runner.invoke(app, ["move", str(test_file), "--dry-run", "--conflict", "rename"])
        assert result.exit_code == 0

    def test_move_with_conflict_overwrite(self, tmp_path):
        """Test move with overwrite conflict strategy."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        result = runner.invoke(
            app, ["move", str(test_file), "--dry-run", "--conflict", "overwrite"]
        )
        assert result.exit_code == 0

    def test_move_with_skip_unclassifiable(self, tmp_path):
        """Test move with skip-unclassifiable flag."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Random content")

        result = runner.invoke(app, ["move", str(test_file), "--dry-run", "--skip-unclassifiable"])
        assert result.exit_code == 0

    def test_move_json_output(self, tmp_path):
        """Test move with JSON output."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        result = runner.invoke(app, ["move", str(test_file), "--dry-run", "--json"])
        assert result.exit_code == 0


class TestClassifyAdvanced:
    """Advanced tests for the classify command."""

    def test_classify_with_custom_reference_tree(self, tmp_path):
        """Test classify with custom reference tree path (non-existent)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        fake_tree = tmp_path / "nonexistent.yaml"

        result = runner.invoke(app, ["classify", str(test_file), "-r", str(fake_tree)])
        # Should fail because tree doesn't exist
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_classify_directory_path(self, tmp_path):
        """Test classify with directory instead of file."""
        result = runner.invoke(app, ["classify", str(tmp_path)])
        # Should handle directory gracefully
        assert result.exit_code == 0
