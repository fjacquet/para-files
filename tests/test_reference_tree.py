"""Tests for the reference_tree module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from para_files.reference_tree import ReferenceTree, load_reference_tree


@pytest.fixture
def test_yaml_path(fixtures_dir: Path) -> Path:
    """Return path to test reference tree YAML."""
    return fixtures_dir / "test_reference_tree.yaml"


@pytest.fixture
def loaded_tree(test_yaml_path: Path) -> ReferenceTree:
    """Return a loaded reference tree."""
    return load_reference_tree(test_yaml_path)


class TestReferenceTree:
    """Tests for ReferenceTree class."""

    def test_init(self, test_yaml_path: Path):
        """Test initialization without loading."""
        tree = ReferenceTree(test_yaml_path)
        assert tree._yaml_path == test_yaml_path
        assert tree._loaded is False

    def test_load(self, test_yaml_path: Path):
        """Test loading the YAML file."""
        tree = ReferenceTree(test_yaml_path)
        tree.load()
        assert tree._loaded is True

    def test_file_not_found(self, tmp_path: Path):
        """Test loading a non-existent file."""
        tree = ReferenceTree(tmp_path / "nonexistent.yaml")
        with pytest.raises(FileNotFoundError):
            tree.load()

    def test_get_all_routes_before_load(self, test_yaml_path: Path):
        """Test that getting routes before loading raises error."""
        tree = ReferenceTree(test_yaml_path)
        with pytest.raises(RuntimeError, match="not loaded"):
            tree.get_all_routes()


class TestReferenceTreeRoutes:
    """Tests for route parsing and retrieval."""

    def test_get_all_routes(self, loaded_tree: ReferenceTree):
        """Test getting all routes."""
        routes = loaded_tree.get_all_routes()
        assert len(routes) >= 3  # inbox + 2 archive routes

    def test_inbox_route(self, loaded_tree: ReferenceTree):
        """Test inbox route is parsed correctly."""
        route = loaded_tree.get_route_by_name("inbox")
        assert route is not None
        assert route.pattern == "0_Inbox"
        assert len(route.utterances) >= 1

    def test_archive_routes(self, loaded_tree: ReferenceTree):
        """Test archive routes are parsed correctly."""
        assurance_route = loaded_tree.get_route_by_name("factures_assurance")
        assert assurance_route is not None
        assert "{issuer}" in assurance_route.pattern
        assert "facture assurance" in assurance_route.utterances

    def test_get_route_not_found(self, loaded_tree: ReferenceTree):
        """Test getting a non-existent route returns None."""
        route = loaded_tree.get_route_by_name("nonexistent")
        assert route is None


class TestReferenceTreeRoutingRules:
    """Tests for routing rules parsing."""

    def test_get_routing_rules(self, loaded_tree: ReferenceTree):
        """Test getting routing rules."""
        rules = loaded_tree.get_routing_rules()
        assert "photos" in rules
        assert "screenshots" in rules

    def test_photos_rule(self, loaded_tree: ReferenceTree):
        """Test photos routing rule is parsed correctly."""
        rules = loaded_tree.get_routing_rules()
        photos = rules["photos"]
        assert ".jpg" in photos.extensions
        assert ".heic" in photos.extensions
        assert photos.date_source == "exif"
        assert photos.fallback_date == "file_modified"

    def test_screenshots_rule(self, loaded_tree: ReferenceTree):
        """Test screenshots routing rule with patterns."""
        rules = loaded_tree.get_routing_rules()
        screenshots = rules["screenshots"]
        assert "Screenshot*" in screenshots.patterns
        assert "Capture*" in screenshots.patterns


class TestReferenceTreeKnownIssuers:
    """Tests for known issuers parsing."""

    def test_get_known_issuers(self, loaded_tree: ReferenceTree):
        """Test getting known issuers."""
        issuers = loaded_tree.get_known_issuers()
        assert "Swica" in issuers.get_issuers("assurances")
        assert "UBS" in issuers.get_issuers("banques")
        assert "SIG" in issuers.get_issuers("energie")
        assert "Swisscom" in issuers.get_issuers("telephonie")
        assert "AWS" in issuers.get_issuers("cloud")

    def test_get_issuer_pattern(self, loaded_tree: ReferenceTree):
        """Test getting patterns from known issuers."""
        issuers = loaded_tree.get_known_issuers()
        pattern = issuers.get_pattern("assurances")
        assert "{year}" in pattern
        assert "{issuer}" in pattern
        assert "Assurances" in pattern

    def test_list_categories(self, loaded_tree: ReferenceTree):
        """Test listing all issuer categories."""
        issuers = loaded_tree.get_known_issuers()
        categories = issuers.list_categories()
        assert "assurances" in categories
        assert "banques" in categories


class TestReferenceTreePatternResolution:
    """Tests for pattern resolution with placeholders."""

    def test_resolve_simple_pattern(self, loaded_tree: ReferenceTree):
        """Test resolving pattern with named parameters."""
        result = loaded_tree.resolve_pattern(
            "4_Archives/factures/{year}/_Assurances/{issuer}",
            {"year": "2025", "issuer": "Swica"},
        )
        assert result == "4_Archives/factures/2025/_Assurances/Swica"

    def test_resolve_date_pattern(self, loaded_tree: ReferenceTree):
        """Test resolving pattern with date placeholders."""
        date = datetime(2025, 12, 25)
        result = loaded_tree.resolve_pattern(
            "4_Archives/photos/{YYYY}/{MM}/{DD}",
            date=date,
        )
        assert result == "4_Archives/photos/2025/12/25"

    def test_resolve_mixed_pattern(self, loaded_tree: ReferenceTree):
        """Test resolving pattern with both named and date placeholders."""
        date = datetime(2025, 6, 15)
        result = loaded_tree.resolve_pattern(
            "{category}/{YYYY}/{MM}/file",
            {"category": "docs"},
            date=date,
        )
        assert result == "docs/2025/06/file"


class TestReferenceTreeRoutingMatch:
    """Tests for routing rule matching."""

    def test_match_by_extension(self, loaded_tree: ReferenceTree):
        """Test matching file by extension."""
        match = loaded_tree.match_routing_rule("photo.jpg", ".jpg")
        assert match is not None
        rule_name, rule = match
        assert rule_name == "photos"

    def test_match_by_pattern(self, loaded_tree: ReferenceTree):
        """Test matching file by glob pattern."""
        # Use .bmp which is not in photos extensions to test pattern matching
        match = loaded_tree.match_routing_rule("Screenshot 2025-01-01.bmp", ".bmp")
        assert match is not None
        rule_name, rule = match
        assert rule_name == "screenshots"

    def test_no_match(self, loaded_tree: ReferenceTree):
        """Test no match returns None."""
        match = loaded_tree.match_routing_rule("document.pdf", ".pdf")
        assert match is None

    def test_extension_case_insensitive(self, loaded_tree: ReferenceTree):
        """Test extension matching is case-insensitive."""
        match = loaded_tree.match_routing_rule("photo.JPG", ".JPG")
        assert match is not None


class TestLoadReferenceTree:
    """Tests for the convenience load function."""

    def test_load_reference_tree(self, test_yaml_path: Path):
        """Test the load_reference_tree convenience function."""
        tree = load_reference_tree(test_yaml_path)
        assert tree._loaded is True
        assert len(tree.get_all_routes()) > 0
