"""Tests for learn command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from para_files.cli.app import app
from para_files.cli.learn_cmd import (
    _handle_keyword_addition,
    _select_route_from_choice,
)


class TestSelectRouteFromChoice:
    """Test _select_route_from_choice function."""

    def test_select_by_number_first(self) -> None:
        """Test selecting route by number (1)."""
        routes = ["invoices", "receipts", "contracts"]
        result = _select_route_from_choice("1", routes)
        assert result == "invoices"

    def test_select_by_number_middle(self) -> None:
        """Test selecting route by number in middle."""
        routes = ["invoices", "receipts", "contracts"]
        result = _select_route_from_choice("2", routes)
        assert result == "receipts"

    def test_select_by_number_last(self) -> None:
        """Test selecting route by last number."""
        routes = ["invoices", "receipts", "contracts"]
        result = _select_route_from_choice("3", routes)
        assert result == "contracts"

    def test_select_by_number_out_of_range(self) -> None:
        """Test selecting by number out of range."""
        routes = ["invoices", "receipts", "contracts"]
        result = _select_route_from_choice("4", routes)
        assert result is None

    def test_select_by_number_zero(self) -> None:
        """Test selecting by zero (invalid)."""
        routes = ["invoices", "receipts", "contracts"]
        result = _select_route_from_choice("0", routes)
        assert result is None

    def test_select_by_name_exact(self) -> None:
        """Test selecting route by exact name."""
        routes = ["invoices", "receipts", "contracts"]
        result = _select_route_from_choice("receipts", routes)
        assert result == "receipts"

    def test_select_by_name_not_found(self) -> None:
        """Test selecting by name not in routes."""
        routes = ["invoices", "receipts", "contracts"]
        result = _select_route_from_choice("unknown", routes)
        assert result is None

    def test_select_by_negative_number(self) -> None:
        """Test selecting by negative number string (not a digit)."""
        routes = ["invoices", "receipts", "contracts"]
        result = _select_route_from_choice("-1", routes)
        # "-1".isdigit() returns False, so it's treated as a name
        assert result is None

    def test_select_empty_routes(self) -> None:
        """Test selecting from empty routes list."""
        routes: list[str] = []
        result = _select_route_from_choice("1", routes)
        assert result is None

    def test_select_by_name_with_spaces(self) -> None:
        """Test selecting route name containing spaces."""
        routes = ["tax invoices", "bank receipts"]
        result = _select_route_from_choice("tax invoices", routes)
        assert result == "tax invoices"


runner = CliRunner()


class TestHandleKeywordAddition:
    """Tests for _handle_keyword_addition function."""

    @patch("para_files.cli.learn_cmd.typer.confirm")
    def test_decline_keyword_addition(self, mock_confirm: MagicMock) -> None:
        """Test declining keyword addition."""
        mock_confirm.return_value = False
        learner = MagicMock()

        _handle_keyword_addition(learner, "fiscalite")

        learner.add_utterance.assert_not_called()

    @patch("para_files.cli.learn_cmd.typer.echo")
    @patch("para_files.cli.learn_cmd.typer.prompt")
    @patch("para_files.cli.learn_cmd.typer.confirm")
    def test_add_keyword_success(
        self, mock_confirm: MagicMock, mock_prompt: MagicMock, mock_echo: MagicMock
    ) -> None:
        """Test successful keyword addition."""
        mock_confirm.return_value = True
        mock_prompt.return_value = "impot"
        learner = MagicMock()
        learner.add_utterance.return_value = True

        _handle_keyword_addition(learner, "fiscalite")

        learner.add_utterance.assert_called_once_with("fiscalite", "impot")
        mock_echo.assert_called()

    @patch("para_files.cli.learn_cmd.typer.echo")
    @patch("para_files.cli.learn_cmd.typer.prompt")
    @patch("para_files.cli.learn_cmd.typer.confirm")
    def test_add_keyword_already_exists(
        self, mock_confirm: MagicMock, mock_prompt: MagicMock, mock_echo: MagicMock
    ) -> None:
        """Test adding duplicate keyword."""
        mock_confirm.return_value = True
        mock_prompt.return_value = "existing"
        learner = MagicMock()
        learner.add_utterance.return_value = False

        _handle_keyword_addition(learner, "fiscalite")

        learner.add_utterance.assert_called_once()
        mock_echo.assert_called()

    @patch("para_files.cli.learn_cmd.typer.prompt")
    @patch("para_files.cli.learn_cmd.typer.confirm")
    def test_empty_keyword(self, mock_confirm: MagicMock, mock_prompt: MagicMock) -> None:
        """Test empty keyword input."""
        mock_confirm.return_value = True
        mock_prompt.return_value = "   "  # Whitespace only
        learner = MagicMock()

        _handle_keyword_addition(learner, "fiscalite")

        learner.add_utterance.assert_not_called()


class TestTrackCorrection:
    """Tests for _track_correction function."""

    @patch("para_files.cli.learn_cmd.FeedbackTracker")
    @patch("para_files.utils.pdf_metadata.extract_pdf_metadata")
    def test_track_correction_with_pdf_metadata(
        self, mock_extract: MagicMock, mock_tracker_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test tracking correction with PDF metadata extraction."""
        from para_files.cli.learn_cmd import _track_correction

        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        mock_metadata = MagicMock()
        mock_metadata.author = "John Doe"
        mock_metadata.title = "Test Document"
        mock_metadata.creator = "Test App"
        mock_extract.return_value = mock_metadata

        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker

        mock_result = MagicMock()
        mock_result.category = "original_category"
        mock_result.confidence.value = 0.85
        mock_result.confidence.source.value = "semantic"

        _track_correction(pdf_file, mock_result, "corrected_route", "preview content")

        mock_tracker.record_correction.assert_called_once()
        call_kwargs = mock_tracker.record_correction.call_args[1]
        assert call_kwargs["original_category"] == "original_category"
        assert call_kwargs["corrected_category"] == "corrected_route"
        assert call_kwargs["metadata"]["author"] == "John Doe"

    @patch("para_files.cli.learn_cmd.FeedbackTracker")
    @patch("para_files.utils.pdf_metadata.extract_pdf_metadata")
    def test_track_correction_no_metadata(
        self, mock_extract: MagicMock, mock_tracker_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test tracking correction when no metadata available."""
        from para_files.cli.learn_cmd import _track_correction

        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        mock_extract.return_value = None

        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker

        mock_result = MagicMock()
        mock_result.category = "original"
        mock_result.confidence.value = 0.75
        mock_result.confidence.source.value = "rules"

        _track_correction(pdf_file, mock_result, "new_route", "preview")

        mock_tracker.record_correction.assert_called_once()

    @patch("para_files.cli.learn_cmd.FeedbackTracker")
    def test_track_correction_non_pdf(
        self, mock_tracker_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test tracking correction for non-PDF file."""
        from para_files.cli.learn_cmd import _track_correction

        txt_file = tmp_path / "document.txt"
        txt_file.write_text("Test content")

        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker

        mock_result = MagicMock()
        mock_result.category = "docs"
        mock_result.confidence.value = 0.6
        mock_result.confidence.source.value = "semantic"

        _track_correction(txt_file, mock_result, "corrected", "preview")

        mock_tracker.record_correction.assert_called_once()
        call_kwargs = mock_tracker.record_correction.call_args[1]
        # No metadata for non-PDF
        assert call_kwargs["metadata"] == {}

    @patch("para_files.cli.learn_cmd.FeedbackTracker")
    def test_track_correction_none_result(
        self, mock_tracker_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test tracking correction when original result is None."""
        from para_files.cli.learn_cmd import _track_correction

        txt_file = tmp_path / "document.txt"
        txt_file.write_text("Test content")

        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker

        _track_correction(txt_file, None, "new_route", "preview")

        mock_tracker.record_correction.assert_called_once()
        call_kwargs = mock_tracker.record_correction.call_args[1]
        assert call_kwargs["original_category"] is None
        assert call_kwargs["original_confidence"] == 0.0
        assert call_kwargs["source"] == "unknown"


class TestLearnCommand:
    """Tests for the learn CLI command."""

    def test_learn_command_help(self) -> None:
        """Test learn command help."""
        result = runner.invoke(app, ["learn", "--help"])
        assert result.exit_code == 0
        assert "Interactive classification learning" in result.output

    @patch("para_files.cli.learn_cmd.validate_file_exists")
    def test_learn_command_file_not_exists(self, mock_validate: MagicMock, tmp_path: Path) -> None:
        """Test learn command with non-existent file."""
        mock_validate.return_value = False

        nonexistent = tmp_path / "missing.pdf"
        runner.invoke(app, ["learn", str(nonexistent)])

        mock_validate.assert_called_once()

    @patch("para_files.cli.learn_cmd.typer.confirm")
    @patch("para_files.cli.learn_cmd.print_classification_result")
    @patch("para_files.cli.learn_cmd.ClassificationPipeline")
    @patch("para_files.cli.learn_cmd.load_config_or_exit")
    @patch("para_files.cli.learn_cmd.validate_file_exists")
    def test_learn_command_confirm_correct(
        self,
        mock_validate: MagicMock,
        mock_config: MagicMock,
        mock_pipeline_class: MagicMock,
        mock_print: MagicMock,
        mock_confirm: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test learn command when user confirms classification."""
        test_file = tmp_path / "document.pdf"
        test_file.touch()

        mock_validate.return_value = True
        mock_config.return_value = MagicMock()

        mock_pipeline = MagicMock()
        mock_pipeline.classify_file.return_value = MagicMock()
        mock_pipeline.get_target_path.return_value = Path("/some/path")
        mock_pipeline_class.return_value = mock_pipeline

        mock_confirm.return_value = True

        result = runner.invoke(app, ["learn", str(test_file)])

        assert "confirmed" in result.output.lower() or result.exit_code == 0

    @patch("para_files.cli.learn_cmd._handle_keyword_addition")
    @patch("para_files.cli.learn_cmd._track_correction")
    @patch("para_files.utils.file_utils.read_content_preview")
    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.learn_cmd.ensure_tree_exists")
    @patch("para_files.cli.learn_cmd.typer.prompt")
    @patch("para_files.cli.learn_cmd.typer.confirm")
    @patch("para_files.cli.learn_cmd.print_classification_result")
    @patch("para_files.cli.learn_cmd.ClassificationPipeline")
    @patch("para_files.cli.learn_cmd.load_config_or_exit")
    @patch("para_files.cli.learn_cmd.validate_file_exists")
    def test_learn_command_user_corrects(  # noqa: PLR0913
        self,
        mock_validate: MagicMock,
        mock_config: MagicMock,
        mock_pipeline_class: MagicMock,
        mock_print: MagicMock,
        mock_confirm: MagicMock,
        mock_prompt: MagicMock,
        mock_ensure_tree: MagicMock,
        mock_learner_class: MagicMock,
        mock_read_preview: MagicMock,
        mock_track: MagicMock,
        mock_keyword: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test learn command when user corrects classification."""
        test_file = tmp_path / "document.pdf"
        test_file.touch()

        mock_validate.return_value = True
        config = MagicMock()
        config.reference_tree_path = tmp_path / "tree.yaml"
        mock_config.return_value = config

        mock_pipeline = MagicMock()
        mock_pipeline.classify_file.return_value = MagicMock()
        mock_pipeline.get_target_path.return_value = Path("/some/path")
        mock_pipeline_class.return_value = mock_pipeline

        mock_confirm.return_value = False  # User disagrees
        mock_prompt.return_value = "1"  # Select first route

        mock_learner = MagicMock()
        mock_learner.list_routes.return_value = ["invoices", "receipts", "contracts"]
        mock_learner_class.return_value = mock_learner

        mock_read_preview.return_value = "file content preview"

        result = runner.invoke(app, ["learn", str(test_file)])

        assert result.exit_code == 0
        mock_track.assert_called_once()
        mock_keyword.assert_called_once()

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.learn_cmd.ensure_tree_exists")
    @patch("para_files.cli.learn_cmd.typer.prompt")
    @patch("para_files.cli.learn_cmd.typer.confirm")
    @patch("para_files.cli.learn_cmd.print_classification_result")
    @patch("para_files.cli.learn_cmd.ClassificationPipeline")
    @patch("para_files.cli.learn_cmd.load_config_or_exit")
    @patch("para_files.cli.learn_cmd.validate_file_exists")
    def test_learn_command_user_skips(  # noqa: PLR0913
        self,
        mock_validate: MagicMock,
        mock_config: MagicMock,
        mock_pipeline_class: MagicMock,
        mock_print: MagicMock,
        mock_confirm: MagicMock,
        mock_prompt: MagicMock,
        mock_ensure_tree: MagicMock,
        mock_learner_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test learn command when user skips correction."""
        test_file = tmp_path / "document.pdf"
        test_file.touch()

        mock_validate.return_value = True
        config = MagicMock()
        config.reference_tree_path = tmp_path / "tree.yaml"
        mock_config.return_value = config

        mock_pipeline = MagicMock()
        mock_pipeline.classify_file.return_value = MagicMock()
        mock_pipeline.get_target_path.return_value = Path("/some/path")
        mock_pipeline_class.return_value = mock_pipeline

        mock_confirm.return_value = False  # User disagrees
        mock_prompt.return_value = "skip"  # User skips

        mock_learner = MagicMock()
        mock_learner.list_routes.return_value = ["invoices", "receipts"]
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["learn", str(test_file)])

        assert "cancelled" in result.output.lower()

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.learn_cmd.ensure_tree_exists")
    @patch("para_files.cli.learn_cmd.typer.prompt")
    @patch("para_files.cli.learn_cmd.typer.confirm")
    @patch("para_files.cli.learn_cmd.print_classification_result")
    @patch("para_files.cli.learn_cmd.ClassificationPipeline")
    @patch("para_files.cli.learn_cmd.load_config_or_exit")
    @patch("para_files.cli.learn_cmd.validate_file_exists")
    def test_learn_command_invalid_selection(  # noqa: PLR0913
        self,
        mock_validate: MagicMock,
        mock_config: MagicMock,
        mock_pipeline_class: MagicMock,
        mock_print: MagicMock,
        mock_confirm: MagicMock,
        mock_prompt: MagicMock,
        mock_ensure_tree: MagicMock,
        mock_learner_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test learn command with invalid route selection."""
        test_file = tmp_path / "document.pdf"
        test_file.touch()

        mock_validate.return_value = True
        config = MagicMock()
        config.reference_tree_path = tmp_path / "tree.yaml"
        mock_config.return_value = config

        mock_pipeline = MagicMock()
        mock_pipeline.classify_file.return_value = MagicMock()
        mock_pipeline.get_target_path.return_value = Path("/some/path")
        mock_pipeline_class.return_value = mock_pipeline

        mock_confirm.return_value = False
        mock_prompt.return_value = "99"  # Invalid selection

        mock_learner = MagicMock()
        mock_learner.list_routes.return_value = ["invoices", "receipts"]
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["learn", str(test_file)])

        assert result.exit_code == 1
        assert "invalid" in result.output.lower()

    @patch("para_files.cli.learn_cmd.typer.confirm")
    @patch("para_files.cli.learn_cmd.print_classification_result")
    @patch("para_files.cli.learn_cmd.ClassificationPipeline")
    @patch("para_files.cli.learn_cmd.load_config_or_exit")
    @patch("para_files.cli.learn_cmd.validate_file_exists")
    def test_learn_with_reference_tree_option(
        self,
        mock_validate: MagicMock,
        mock_config: MagicMock,
        mock_pipeline_class: MagicMock,
        mock_print: MagicMock,
        mock_confirm: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test learn command with custom reference tree."""
        test_file = tmp_path / "document.pdf"
        test_file.touch()
        custom_tree = tmp_path / "custom_tree.yaml"
        custom_tree.write_text("routes: []")

        mock_validate.return_value = True
        config = MagicMock()
        config.reference_tree_path = tmp_path / "default.yaml"
        mock_config.return_value = config

        mock_pipeline = MagicMock()
        mock_pipeline.classify_file.return_value = MagicMock()
        mock_pipeline.get_target_path.return_value = Path("/some/path")
        mock_pipeline_class.return_value = mock_pipeline

        mock_confirm.return_value = True

        result = runner.invoke(
            app, ["learn", str(test_file), "--reference-tree", str(custom_tree)]
        )

        assert result.exit_code == 0
        # Verify config was updated with custom tree path
        assert config.reference_tree_path == custom_tree
