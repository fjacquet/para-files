"""Tests for learn command."""

from __future__ import annotations

from para_files.cli.learn_cmd import _select_route_from_choice


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
