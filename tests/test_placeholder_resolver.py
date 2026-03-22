"""Tests for placeholder resolution with required/optional policy.

Covers the required vs optional placeholder distinction and edge cases
for path normalization after placeholder removal.
"""

from __future__ import annotations

import pytest

from para_files.utils.placeholder_resolver import clean_unreplaced_placeholders, resolve_placeholders


class TestRequiredPlaceholderRejection:
    """Tests that required placeholders cause rejection (return None)."""

    def test_missing_issuer_returns_none(self) -> None:
        """Test that unresolved {issuer} placeholder causes rejection."""
        result = clean_unreplaced_placeholders("2_Areas/{issuer}/docs")
        assert result is None

    def test_missing_technology_returns_none(self) -> None:
        """Test that unresolved {technology} placeholder causes rejection."""
        result = clean_unreplaced_placeholders("2_Areas/{technology}/docs")
        assert result is None

    def test_missing_location_returns_none(self) -> None:
        """Test that unresolved {location} placeholder causes rejection."""
        result = clean_unreplaced_placeholders("2_Areas/{location}/reports")
        assert result is None

    def test_missing_country_returns_none(self) -> None:
        """Test that unresolved {country} placeholder causes rejection."""
        result = clean_unreplaced_placeholders("3_Resources/{country}/docs")
        assert result is None

    def test_required_and_optional_missing_returns_none(self) -> None:
        """Test that required placeholder missing returns None even with optional present."""
        result = clean_unreplaced_placeholders("2_Areas/{issuer}/{year}/docs")
        assert result is None


class TestOptionalPlaceholderRemoval:
    """Tests that optional placeholders are stripped cleanly."""

    def test_missing_year_stripped_cleanly(self) -> None:
        """Test that unresolved {year} placeholder is stripped, not rejected."""
        result = clean_unreplaced_placeholders("4_Archives/{year}/taxes")
        assert result == "4_Archives/taxes"

    def test_missing_yyyy_stripped_cleanly(self) -> None:
        """Test that unresolved {YYYY} placeholder is stripped cleanly."""
        result = clean_unreplaced_placeholders("4_Archives/{YYYY}/docs")
        assert result == "4_Archives/docs"

    def test_missing_mm_stripped_cleanly(self) -> None:
        """Test that unresolved {MM} placeholder is stripped cleanly."""
        result = clean_unreplaced_placeholders("4_Archives/2024/{MM}/docs")
        assert result == "4_Archives/2024/docs"

    def test_missing_month_stripped_cleanly(self) -> None:
        """Test that unresolved {month} placeholder is stripped cleanly."""
        result = clean_unreplaced_placeholders("4_Archives/{month}/reports")
        assert result == "4_Archives/reports"

    def test_missing_day_stripped_cleanly(self) -> None:
        """Test that unresolved {day}/docs is stripped cleanly."""
        result = clean_unreplaced_placeholders("4_Archives/{day}/docs")
        assert result == "4_Archives/docs"

    def test_missing_dd_stripped_cleanly(self) -> None:
        """Test that unresolved {DD} placeholder is stripped cleanly."""
        result = clean_unreplaced_placeholders("4_Archives/{DD}/docs")
        assert result == "4_Archives/docs"

    def test_double_slashes_collapsed_after_optional_removal(self) -> None:
        """Test that double slashes are collapsed after optional placeholder removal."""
        # After removing {year}: "4_Archives//taxes" -> "4_Archives/taxes"
        result = clean_unreplaced_placeholders("4_Archives/{year}/taxes")
        assert "//" not in (result or "")
        assert result == "4_Archives/taxes"


class TestPassThroughCases:
    """Tests for paths that should pass through unchanged."""

    def test_no_placeholders_pass_through(self) -> None:
        """Test that paths without placeholders are returned as-is."""
        result = clean_unreplaced_placeholders("3_Resources/documentation")
        assert result == "3_Resources/documentation"

    def test_all_resolved_pass_through(self) -> None:
        """Test that fully resolved paths pass through."""
        result = clean_unreplaced_placeholders("2_Areas/AXA/docs")
        assert result == "2_Areas/AXA/docs"

    def test_trailing_slash_stripped(self) -> None:
        """Test that trailing slashes are stripped."""
        result = clean_unreplaced_placeholders("2_Areas/AXA/docs/")
        assert result == "2_Areas/AXA/docs"


class TestResolvePlaceholders:
    """Tests for the resolve_placeholders function."""

    def test_resolves_all_params(self) -> None:
        """Test that all provided params are substituted."""
        result = resolve_placeholders("2_Areas/{issuer}/{year}", {"issuer": "AXA", "year": "2024"})
        assert result == "2_Areas/AXA/2024"

    def test_resolve_then_clean_with_missing_year_valid(self) -> None:
        """Test resolve then clean with missing year results in valid path."""
        pattern = "2_Areas/{issuer}/{year}"
        # Only resolve issuer, year remains
        partial = resolve_placeholders(pattern, {"issuer": "AXA"})
        result = clean_unreplaced_placeholders(partial)
        # year is optional, so result should be valid path without year
        assert result == "2_Areas/AXA"

    def test_resolve_then_clean_with_missing_issuer_returns_none(self) -> None:
        """Test resolve then clean with missing issuer returns None."""
        pattern = "2_Areas/{issuer}/{year}"
        # Only resolve year, issuer remains
        partial = resolve_placeholders(pattern, {"year": "2024"})
        result = clean_unreplaced_placeholders(partial)
        # issuer is required, so result should be None
        assert result is None

    def test_resolve_unknown_key_ignored(self) -> None:
        """Test that unknown keys in params don't cause errors."""
        result = resolve_placeholders("2_Areas/{issuer}", {"issuer": "AXA", "unknown": "value"})
        assert result == "2_Areas/AXA"
