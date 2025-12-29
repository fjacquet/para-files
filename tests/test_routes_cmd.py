"""Tests for routes command."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer

from para_files.cli.routes_cmd import (
    _print_route_details,
    _print_route_with_utterances,
    _show_available_routes,
)


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
