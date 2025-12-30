"""Tests for routes command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from para_files.cli.app import app
from para_files.cli.routes_cmd import (
    _print_route_details,
    _print_route_with_utterances,
    _show_available_routes,
    _test_file_against_route,
)


runner = CliRunner()


class TestShowAvailableRoutes:
    """Test _show_available_routes function."""

    def test_shows_routes_and_exits(self, capsys: pytest.CaptureFixture) -> None:
        """Test that routes are shown and SystemExit is raised."""
        mock_learner = MagicMock()
        mock_learner.list_routes.return_value = ["invoices", "receipts", "contracts"]

        with pytest.raises(typer.Exit) as exc_info:
            _show_available_routes(mock_learner)

        assert exc_info.value.exit_code == 1
        captured = capsys.readouterr()
        assert "Available routes" in captured.out
        assert "invoices" in captured.out
        assert "receipts" in captured.out


class TestPrintRouteWithUtterances:
    """Test _print_route_with_utterances function."""

    def test_prints_route_and_utterances(self, capsys: pytest.CaptureFixture) -> None:
        """Test printing route with utterances."""
        mock_learner = MagicMock()
        mock_learner.get_route_info.return_value = {"utterances": ["invoice", "bill", "statement"]}

        _print_route_with_utterances(mock_learner, "invoices")

        captured = capsys.readouterr()
        assert "invoices" in captured.out
        assert "invoice" in captured.out
        assert "bill" in captured.out

    def test_prints_limited_utterances(self, capsys: pytest.CaptureFixture) -> None:
        """Test that utterances are limited to MAX_UTTERANCES_SHOWN."""
        mock_learner = MagicMock()
        # Create more than MAX_UTTERANCES_SHOWN utterances
        many_utterances = [f"utterance_{i}" for i in range(20)]
        mock_learner.get_route_info.return_value = {"utterances": many_utterances}

        _print_route_with_utterances(mock_learner, "invoices")

        captured = capsys.readouterr()
        assert "invoices" in captured.out
        assert "more" in captured.out

    def test_handles_empty_utterances(self, capsys: pytest.CaptureFixture) -> None:
        """Test handling route with no utterances."""
        mock_learner = MagicMock()
        mock_learner.get_route_info.return_value = {"utterances": []}

        _print_route_with_utterances(mock_learner, "invoices")

        captured = capsys.readouterr()
        assert "invoices" in captured.out

    def test_handles_no_route_info(self, capsys: pytest.CaptureFixture) -> None:
        """Test handling when route info is None."""
        mock_learner = MagicMock()
        mock_learner.get_route_info.return_value = None

        _print_route_with_utterances(mock_learner, "unknown")

        captured = capsys.readouterr()
        assert "unknown" in captured.out


class TestPrintRouteDetails:
    """Test _print_route_details function."""

    def test_prints_route_with_pattern(self, capsys: pytest.CaptureFixture) -> None:
        """Test printing route with pattern."""
        route_info = {
            "pattern": "2_Areas/finance/invoices",
            "utterances": ["invoice", "bill"],
        }

        _print_route_details("invoices", route_info)

        captured = capsys.readouterr()
        assert "Route: invoices" in captured.out
        assert "Pattern: 2_Areas/finance/invoices" in captured.out
        assert "Utterances (2)" in captured.out
        assert "invoice" in captured.out

    def test_prints_route_without_pattern(self, capsys: pytest.CaptureFixture) -> None:
        """Test printing route without pattern."""
        route_info = {
            "utterances": ["invoice"],
        }

        _print_route_details("invoices", route_info)

        captured = capsys.readouterr()
        assert "Route: invoices" in captured.out
        assert "Pattern" not in captured.out

    def test_prints_route_without_utterances(self, capsys: pytest.CaptureFixture) -> None:
        """Test printing route without utterances."""
        route_info = {
            "pattern": "2_Areas/finance",
        }

        _print_route_details("finance", route_info)

        captured = capsys.readouterr()
        assert "Route: finance" in captured.out
        assert "Utterances: (none)" in captured.out


class TestTestFileAgainstRoute:
    """Test _test_file_against_route function."""

    @patch("para_files.cli.routes_cmd.ClassificationPipeline")
    @patch("para_files.cli.routes_cmd.load_config_or_exit")
    def test_file_matches_route(
        self,
        mock_config: MagicMock,
        mock_pipeline_class: MagicMock,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
    ) -> None:
        """Test when file matches expected route."""
        test_file = tmp_path / "test.pdf"
        test_file.touch()

        mock_config.return_value = MagicMock()
        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.category = "4_Archives/10y_fiscalite/2024"
        mock_result.route_name = "fiscalite"
        mock_result.confidence.value = 0.95
        mock_result.confidence.source.value = "semantic"
        mock_pipeline.classify_file.return_value = mock_result
        mock_pipeline_class.return_value = mock_pipeline

        _test_file_against_route(test_file, "fiscalite", None)

        captured = capsys.readouterr()
        assert "Testing file" in captured.out
        assert "File matches this route" in captured.out

    @patch("para_files.cli.routes_cmd.ClassificationPipeline")
    @patch("para_files.cli.routes_cmd.load_config_or_exit")
    def test_file_matches_different_route(
        self,
        mock_config: MagicMock,
        mock_pipeline_class: MagicMock,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
    ) -> None:
        """Test when file matches a different route."""
        test_file = tmp_path / "test.pdf"
        test_file.touch()

        mock_config.return_value = MagicMock()
        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.category = "4_Archives/10y_sante/2024"
        mock_result.route_name = "sante"
        mock_result.confidence.value = 0.85
        mock_result.confidence.source.value = "semantic"
        mock_pipeline.classify_file.return_value = mock_result
        mock_pipeline_class.return_value = mock_pipeline

        _test_file_against_route(test_file, "fiscalite", None)

        captured = capsys.readouterr()
        assert "Testing file" in captured.out
        assert "File matched different route" in captured.out

    @patch("para_files.cli.routes_cmd.ClassificationPipeline")
    @patch("para_files.cli.routes_cmd.load_config_or_exit")
    def test_no_route_matched(
        self,
        mock_config: MagicMock,
        mock_pipeline_class: MagicMock,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
    ) -> None:
        """Test when no route matched."""
        test_file = tmp_path / "test.pdf"
        test_file.touch()

        mock_config.return_value = MagicMock()
        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.category = "0_Inbox"
        mock_result.route_name = None
        mock_result.confidence.value = 0.0
        mock_result.confidence.source.value = "default"
        mock_pipeline.classify_file.return_value = mock_result
        mock_pipeline_class.return_value = mock_pipeline

        _test_file_against_route(test_file, "fiscalite", None)

        captured = capsys.readouterr()
        assert "No route matched" in captured.out


class TestListRoutesCommand:
    """Test routes command."""

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    def test_list_routes_basic(
        self,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
    ) -> None:
        """Test basic route listing."""
        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.list_routes.return_value = ["fiscalite", "sante", "factures"]
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["routes"])

        assert result.exit_code == 0
        assert "Available routes (3)" in result.output
        assert "fiscalite" in result.output

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    def test_list_routes_empty(
        self,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
    ) -> None:
        """Test when no routes exist."""
        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.list_routes.return_value = []
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["routes"])

        assert result.exit_code == 0
        assert "No routes found" in result.output

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    def test_list_routes_with_utterances(
        self,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
    ) -> None:
        """Test route listing with utterances."""
        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.list_routes.return_value = ["fiscalite"]
        mock_learner.get_route_info.return_value = {"utterances": ["impot", "taxes"]}
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["routes", "--utterances"])

        assert result.exit_code == 0
        assert "fiscalite" in result.output

    def test_routes_help(self) -> None:
        """Test routes command help."""
        result = runner.invoke(app, ["routes", "--help"])
        assert result.exit_code == 0
        assert "List all available routes" in result.output


class TestListIssuersCommand:
    """Test issuers command."""

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    def test_list_issuers_basic(
        self,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
    ) -> None:
        """Test basic issuer listing."""
        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.get_known_issuers.return_value = {
            "assurances": ["SwissLife", "AXA"],
            "energie": ["Romande-Energie"],
        }
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["issuers"])

        assert result.exit_code == 0
        assert "Known issuers by category" in result.output
        assert "assurances" in result.output
        assert "SwissLife" in result.output

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    def test_list_issuers_empty(
        self,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
    ) -> None:
        """Test when no issuers exist."""
        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.get_known_issuers.return_value = {}
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["issuers"])

        assert result.exit_code == 0
        assert "No issuers defined" in result.output

    def test_issuers_help(self) -> None:
        """Test issuers command help."""
        result = runner.invoke(app, ["issuers", "--help"])
        assert result.exit_code == 0
        assert "List all known issuers" in result.output


class TestAddIssuerCommand:
    """Test add-issuer command."""

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    def test_add_issuer_success(
        self,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
    ) -> None:
        """Test adding a new issuer."""
        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.list_issuer_categories.return_value = ["assurances"]
        mock_learner.add_issuer.return_value = True
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["add-issuer", "Baloise", "--category", "assurances"])

        assert result.exit_code == 0
        assert "Added issuer 'Baloise'" in result.output

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    def test_add_issuer_already_exists(
        self,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
    ) -> None:
        """Test adding an existing issuer."""
        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.list_issuer_categories.return_value = ["assurances"]
        mock_learner.add_issuer.return_value = False
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["add-issuer", "SwissLife", "--category", "assurances"])

        assert result.exit_code == 0
        assert "already exists" in result.output

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    def test_add_issuer_new_category(
        self,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
    ) -> None:
        """Test adding issuer to new category."""
        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.list_issuer_categories.return_value = []
        mock_learner.add_issuer.return_value = True
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["add-issuer", "NewIssuer", "--category", "new_category"])

        assert result.exit_code == 0
        assert "Creating new category" in result.output

    def test_add_issuer_help(self) -> None:
        """Test add-issuer command help."""
        result = runner.invoke(app, ["add-issuer", "--help"])
        assert result.exit_code == 0
        assert "Add a new issuer" in result.output


class TestAddUtteranceCommand:
    """Test add-utterance command."""

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    def test_add_utterance_success(
        self,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
    ) -> None:
        """Test adding a new utterance."""
        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.add_utterance.return_value = True
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["add-utterance", "fiscalite", "déclaration fiscale"])

        assert result.exit_code == 0
        assert "Added utterance" in result.output

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    def test_add_utterance_already_exists(
        self,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
    ) -> None:
        """Test adding existing utterance."""
        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.add_utterance.return_value = False
        mock_learner.get_route_info.return_value = {"utterances": ["impot"]}
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["add-utterance", "fiscalite", "impot"])

        assert result.exit_code == 0
        assert "already exists" in result.output

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    def test_add_utterance_route_not_found(
        self,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
    ) -> None:
        """Test adding utterance to non-existent route."""
        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.add_utterance.return_value = False
        mock_learner.get_route_info.return_value = None
        mock_learner.list_routes.return_value = ["fiscalite", "sante"]
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["add-utterance", "unknown", "test"])

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_add_utterance_help(self) -> None:
        """Test add-utterance command help."""
        result = runner.invoke(app, ["add-utterance", "--help"])
        assert result.exit_code == 0
        assert "Add a new utterance" in result.output


class TestTestRouteCommand:
    """Test test-route command."""

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    @patch("para_files.cli.routes_cmd.setup_logging")
    def test_test_route_basic(
        self,
        mock_logging: MagicMock,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
    ) -> None:
        """Test basic route testing."""
        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.get_route_info.return_value = {
            "pattern": "4_Archives/10y_fiscalite/{year}",
            "utterances": ["impot", "taxes"],
        }
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["test-route", "fiscalite"])

        assert result.exit_code == 0
        assert "Route: fiscalite" in result.output
        assert "Pattern" in result.output

    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    @patch("para_files.cli.routes_cmd.setup_logging")
    def test_test_route_not_found(
        self,
        mock_logging: MagicMock,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
    ) -> None:
        """Test when route not found."""
        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.get_route_info.return_value = None
        mock_learner.list_routes.return_value = ["fiscalite", "sante"]
        mock_learner_class.return_value = mock_learner

        result = runner.invoke(app, ["test-route", "unknown"])

        assert result.exit_code == 1
        assert "not found" in result.output

    @patch("para_files.cli.routes_cmd._test_file_against_route")
    @patch("para_files.cli.routes_cmd.validate_file_exists")
    @patch("para_files.learner.RoutingLearner")
    @patch("para_files.cli.routes_cmd.ensure_tree_exists")
    @patch("para_files.cli.routes_cmd.get_reference_tree_path")
    @patch("para_files.cli.routes_cmd.setup_logging")
    def test_test_route_with_file(
        self,
        mock_logging: MagicMock,
        mock_get_path: MagicMock,
        mock_ensure: MagicMock,
        mock_learner_class: MagicMock,
        mock_validate: MagicMock,
        mock_test_file: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test route testing with file."""
        test_file = tmp_path / "test.pdf"
        test_file.touch()

        mock_get_path.return_value = Path("/fake/tree.yaml")
        mock_learner = MagicMock()
        mock_learner.get_route_info.return_value = {"pattern": "4_Archives/10y_fiscalite/{year}"}
        mock_learner_class.return_value = mock_learner
        mock_validate.return_value = True

        result = runner.invoke(app, ["test-route", "fiscalite", "--file", str(test_file)])

        assert result.exit_code == 0
        mock_test_file.assert_called_once()

    def test_test_route_help(self) -> None:
        """Test test-route command help."""
        result = runner.invoke(app, ["test-route", "--help"])
        assert result.exit_code == 0
        assert "Test a route's configuration" in result.output
