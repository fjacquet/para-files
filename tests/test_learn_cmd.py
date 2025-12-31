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
