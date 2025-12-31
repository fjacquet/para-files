"""Tests for scan command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from para_files.cli.app import app
from para_files.cli.scan_cmd import (
    _classify_file_for_scan,
    _print_scan_summary,
)


class TestClassifyFileForScan:
    """Tests for _classify_file_for_scan function."""

    def test_classify_success_console_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test successful classification with console output."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.category = "invoices"
        mock_result.confidence.value = 0.85
        mock_result.confidence.source.value = "semantic"
        mock_result.route_name = None
        mock_pipeline.classify_file.return_value = mock_result
        mock_pipeline.get_target_path.return_value = Path("/target/invoices")

        stats: dict[str, int] = {}

        result = _classify_file_for_scan(test_file, mock_pipeline, stats, output_json=False)

        assert result is None  # Returns None for console output
        assert stats["semantic"] == 1

    def test_classify_success_json_output(self, tmp_path: Path) -> None:
        """Test successful classification with JSON output."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.category = "invoices"
        mock_result.confidence.value = 0.85
        mock_result.confidence.source.value = "semantic"
        mock_result.route_name = "factures"
        mock_pipeline.classify_file.return_value = mock_result
        mock_pipeline.get_target_path.return_value = Path("/target/invoices")

        stats: dict[str, int] = {}

        result = _classify_file_for_scan(test_file, mock_pipeline, stats, output_json=True)

        assert result is not None
        assert result["category"] == "invoices"
        assert result["confidence"] == 0.85
        assert result["source"] == "semantic"
        assert result["route_name"] == "factures"
        assert stats["semantic"] == 1

    def test_classify_error_json_output(self, tmp_path: Path) -> None:
        """Test classification error with JSON output."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_pipeline = MagicMock()
        mock_pipeline.classify_file.side_effect = Exception("Classification failed")

        stats: dict[str, int] = {}

        result = _classify_file_for_scan(test_file, mock_pipeline, stats, output_json=True)

        assert result is not None
        assert "error" in result
        assert result["error"] == "Classification failed"

    def test_classify_error_console_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test classification error with console output."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_pipeline = MagicMock()
        mock_pipeline.classify_file.side_effect = Exception("Classification failed")

        stats: dict[str, int] = {}

        result = _classify_file_for_scan(test_file, mock_pipeline, stats, output_json=False)

        assert result is None

    def test_classify_without_route_name(self, tmp_path: Path) -> None:
        """Test classification result without route_name."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.category = "documents"
        mock_result.confidence.value = 0.75
        mock_result.confidence.source.value = "rules"
        mock_result.route_name = None  # No route name
        mock_pipeline.classify_file.return_value = mock_result
        mock_pipeline.get_target_path.return_value = Path("/target/documents")

        stats: dict[str, int] = {}

        result = _classify_file_for_scan(test_file, mock_pipeline, stats, output_json=True)

        assert result is not None
        assert "route_name" not in result


class TestPrintScanSummary:
    """Tests for _print_scan_summary function."""

    def test_print_summary_console(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Test printing scan summary to console."""
        files = [tmp_path / "file1.pdf", tmp_path / "file2.pdf"]
        stats = {"semantic": 1, "rules": 1}
        results: list[dict[str, Any]] = []

        _print_scan_summary(tmp_path, files, stats, results, output_json=False)

        captured = capsys.readouterr()
        assert "Summary" in captured.out
        assert "2 files scanned" in captured.out
        assert "semantic: 1" in captured.out
        assert "rules: 1" in captured.out

    def test_print_summary_json(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Test printing scan summary as JSON."""
        files = [tmp_path / "file1.pdf"]
        stats = {"semantic": 1}
        results = [{"category": "invoices", "confidence": 0.9}]

        _print_scan_summary(tmp_path, files, stats, results, output_json=True)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["total_files"] == 1
        assert output["stats"] == {"semantic": 1}
        assert len(output["results"]) == 1

    def test_print_summary_empty_stats(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Test printing summary with empty stats."""
        files: list[Path] = []
        stats: dict[str, int] = {}
        results: list[dict[str, Any]] = []

        _print_scan_summary(tmp_path, files, stats, results, output_json=False)

        captured = capsys.readouterr()
        assert "0 files scanned" in captured.out


runner = CliRunner()


class TestScanCommand:
    """Tests for the scan CLI command."""

    def test_scan_command_help(self) -> None:
        """Test scan command help."""
        result = runner.invoke(app, ["scan", "--help"])
        assert result.exit_code == 0
        assert "preview file classifications" in result.output.lower()

    @patch("para_files.cli.scan_cmd.ClassificationPipeline")
    @patch("para_files.cli.scan_cmd.load_config_or_exit")
    def test_scan_no_files(
        self, mock_config: MagicMock, mock_pipeline: MagicMock, tmp_path: Path
    ) -> None:
        """Test scan with no matching files."""
        mock_config.return_value = MagicMock()

        result = runner.invoke(app, ["scan", str(tmp_path)])
        assert "No files found" in result.output

    @patch("para_files.cli.scan_cmd.ClassificationPipeline")
    @patch("para_files.cli.scan_cmd.load_config_or_exit")
    def test_scan_with_custom_reference_tree(
        self, mock_config: MagicMock, mock_pipeline_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test scan with custom reference tree option."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        custom_tree = tmp_path / "custom.yaml"
        custom_tree.write_text("routes: []")

        config = MagicMock()
        config.max_workers = 1
        mock_config.return_value = config

        mock_result = MagicMock()
        mock_result.category = "invoices"
        mock_result.confidence.value = 0.85
        mock_result.confidence.source.value = "semantic"
        mock_result.route_name = None

        mock_pipeline = MagicMock()
        mock_pipeline.classify_file.return_value = mock_result
        mock_pipeline.get_target_path.return_value = Path("/target")
        mock_pipeline_class.return_value = mock_pipeline

        result = runner.invoke(app, ["scan", str(tmp_path), "--reference-tree", str(custom_tree)])

        assert result.exit_code == 0
        assert config.reference_tree_path == custom_tree

    @patch("para_files.cli.scan_cmd.ClassificationPipeline")
    @patch("para_files.cli.scan_cmd.load_config_or_exit")
    def test_scan_with_extension_filter(
        self, mock_config: MagicMock, mock_pipeline_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test scan with extension filter."""
        # Create files with different extensions
        (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "image.jpg").write_bytes(b"JFIF")

        config = MagicMock()
        config.max_workers = 1
        mock_config.return_value = config

        mock_result = MagicMock()
        mock_result.category = "invoices"
        mock_result.confidence.value = 0.85
        mock_result.confidence.source.value = "semantic"
        mock_result.route_name = None

        mock_pipeline = MagicMock()
        mock_pipeline.classify_file.return_value = mock_result
        mock_pipeline.get_target_path.return_value = Path("/target")
        mock_pipeline_class.return_value = mock_pipeline

        result = runner.invoke(app, ["scan", str(tmp_path), "--ext", "pdf"])

        assert result.exit_code == 0
        # Should only classify PDF file
        assert mock_pipeline.classify_file.call_count == 1

    @patch("para_files.cli.scan_cmd._classify_single_file")
    @patch("para_files.cli.scan_cmd.ClassificationPipeline")
    @patch("para_files.cli.scan_cmd.load_config_or_exit")
    def test_scan_parallel_processing(
        self,
        mock_config: MagicMock,
        mock_pipeline_class: MagicMock,
        mock_classify: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test scan with parallel processing (max_workers > 1)."""
        # Create multiple files
        for i in range(3):
            (tmp_path / f"doc{i}.pdf").write_bytes(b"%PDF-1.4")

        config = MagicMock()
        config.max_workers = 4  # Enable parallel processing
        mock_config.return_value = config

        mock_pipeline = MagicMock()
        mock_pipeline_class.return_value = mock_pipeline

        # Mock the classify function to return proper dict
        mock_classify.return_value = {
            "source_file": "test.pdf",
            "filename": "test.pdf",
            "category": "invoices",
            "confidence": 0.85,
            "source": "semantic",
        }

        result = runner.invoke(app, ["scan", str(tmp_path)])

        assert result.exit_code == 0

    @patch("para_files.cli.scan_cmd.ClassificationPipeline")
    @patch("para_files.cli.scan_cmd.load_config_or_exit")
    def test_scan_verbose_mode(
        self, mock_config: MagicMock, mock_pipeline_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test scan with verbose output."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        config = MagicMock()
        config.max_workers = 1
        mock_config.return_value = config

        mock_result = MagicMock()
        mock_result.category = "invoices"
        mock_result.confidence.value = 0.85
        mock_result.confidence.source.value = "semantic"
        mock_result.route_name = None

        mock_pipeline = MagicMock()
        mock_pipeline.classify_file.return_value = mock_result
        mock_pipeline.get_target_path.return_value = Path("/target")
        mock_pipeline_class.return_value = mock_pipeline

        result = runner.invoke(app, ["scan", str(tmp_path), "-v"])

        assert result.exit_code == 0
