"""Tests for the learner module."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from para_files.learner import RoutingLearner


@pytest.fixture
def sample_tree(tmp_path: Path) -> Path:
    """Create a sample reference tree for testing."""
    tree_file = tmp_path / "tree.yaml"
    tree_data = {
        "version": "1.0",
        "projects": {
            "path": "1_Projects",
            "routes": [
                {
                    "name": "project-alpha",
                    "pattern": "1_Projects/alpha",
                    "utterances": ["alpha project", "project alpha"],
                }
            ],
        },
        "areas": {
            "path": "2_Areas",
            "routes": [
                {
                    "name": "finances",
                    "pattern": "2_Areas/finances",
                    "utterances": ["financial", "money"],
                }
            ],
        },
        "resources": {
            "path": "3_Resources",
            "routes": [
                {
                    "name": "documentation",
                    "pattern": "3_Resources/docs",
                }  # No utterances
            ],
        },
        "archives": {
            "path": "4_Archives",
            "routes": [
                {
                    "name": "factures",
                    "pattern": "4_Archives/factures",
                    "utterances": ["invoice", "facture"],
                }
            ],
        },
        "known_issuers": {
            "banques": ["UBS", "Credit Suisse"],
            "assurances": ["Allianz", "AXA"],
        },
    }
    with tree_file.open("w") as f:
        yaml.safe_dump(tree_data, f)
    return tree_file


@pytest.fixture
def empty_tree(tmp_path: Path) -> Path:
    """Create an empty reference tree."""
    tree_file = tmp_path / "empty_tree.yaml"
    tree_data = {"version": "1.0"}
    with tree_file.open("w") as f:
        yaml.safe_dump(tree_data, f)
    return tree_file


class TestRoutingLearnerInit:
    """Tests for RoutingLearner initialization."""

    def test_init_with_path(self, sample_tree: Path):
        """Test initialization with valid path."""
        learner = RoutingLearner(sample_tree)
        assert learner.reference_tree_path == sample_tree
        assert learner._tree is None  # Lazy loading


class TestRoutingLearnerListRoutes:
    """Tests for list_routes method."""

    def test_list_routes(self, sample_tree: Path):
        """Test listing all routes."""
        learner = RoutingLearner(sample_tree)
        routes = learner.list_routes()

        assert "project-alpha" in routes
        assert "finances" in routes
        assert "documentation" in routes
        assert "factures" in routes
        assert len(routes) == 4

    def test_list_routes_empty_tree(self, empty_tree: Path):
        """Test listing routes from empty tree."""
        learner = RoutingLearner(empty_tree)
        routes = learner.list_routes()

        assert routes == []


class TestRoutingLearnerListIssuerCategories:
    """Tests for list_issuer_categories method."""

    def test_list_issuer_categories(self, sample_tree: Path):
        """Test listing issuer categories."""
        learner = RoutingLearner(sample_tree)
        categories = learner.list_issuer_categories()

        assert "banques" in categories
        assert "assurances" in categories
        assert len(categories) == 2

    def test_list_issuer_categories_empty(self, empty_tree: Path):
        """Test listing issuer categories when none exist."""
        learner = RoutingLearner(empty_tree)
        categories = learner.list_issuer_categories()

        assert categories == []


class TestRoutingLearnerAddIssuer:
    """Tests for add_issuer method."""

    def test_add_issuer_existing_category(self, sample_tree: Path):
        """Test adding issuer to existing category."""
        learner = RoutingLearner(sample_tree)

        result = learner.add_issuer("PostFinance", "banques")
        assert result is True

        # Verify saved
        with sample_tree.open() as f:
            tree = yaml.safe_load(f)
        assert "PostFinance" in tree["known_issuers"]["banques"]

    def test_add_issuer_new_category(self, sample_tree: Path):
        """Test adding issuer to new category."""
        learner = RoutingLearner(sample_tree)

        result = learner.add_issuer("CERN", "employers")
        assert result is True

        # Verify saved
        with sample_tree.open() as f:
            tree = yaml.safe_load(f)
        assert "employers" in tree["known_issuers"]
        assert "CERN" in tree["known_issuers"]["employers"]

    def test_add_issuer_already_exists(self, sample_tree: Path):
        """Test adding issuer that already exists."""
        learner = RoutingLearner(sample_tree)

        result = learner.add_issuer("UBS", "banques")
        assert result is False

    def test_add_issuer_creates_known_issuers_section(self, empty_tree: Path):
        """Test adding issuer when known_issuers section doesn't exist."""
        learner = RoutingLearner(empty_tree)

        result = learner.add_issuer("TestIssuer", "test_category")
        assert result is True

        # Verify saved
        with empty_tree.open() as f:
            tree = yaml.safe_load(f)
        assert "known_issuers" in tree
        assert "test_category" in tree["known_issuers"]


class TestRoutingLearnerAddUtterance:
    """Tests for add_utterance method."""

    def test_add_utterance_success(self, sample_tree: Path):
        """Test adding utterance to route."""
        learner = RoutingLearner(sample_tree)

        result = learner.add_utterance("factures", "bill")
        assert result is True

        # Verify saved
        with sample_tree.open() as f:
            tree = yaml.safe_load(f)
        factures_route = tree["archives"]["routes"][0]
        assert "bill" in factures_route["utterances"]

    def test_add_utterance_route_not_found(self, sample_tree: Path):
        """Test adding utterance to non-existent route."""
        learner = RoutingLearner(sample_tree)

        result = learner.add_utterance("nonexistent", "test")
        assert result is False

    def test_add_utterance_already_exists(self, sample_tree: Path):
        """Test adding utterance that already exists."""
        learner = RoutingLearner(sample_tree)

        result = learner.add_utterance("factures", "invoice")
        assert result is False

    def test_add_utterance_creates_utterances_list(self, sample_tree: Path):
        """Test adding utterance when route has no utterances."""
        learner = RoutingLearner(sample_tree)

        # documentation route has no utterances
        result = learner.add_utterance("documentation", "docs")
        assert result is True

        # Verify saved
        with sample_tree.open() as f:
            tree = yaml.safe_load(f)
        doc_route = tree["resources"]["routes"][0]
        assert "utterances" in doc_route
        assert "docs" in doc_route["utterances"]


class TestRoutingLearnerGetRouteInfo:
    """Tests for get_route_info method."""

    def test_get_route_info_found(self, sample_tree: Path):
        """Test getting route info for existing route."""
        learner = RoutingLearner(sample_tree)

        info = learner.get_route_info("factures")

        assert info is not None
        assert info["name"] == "factures"
        assert info["pattern"] == "4_Archives/factures"
        assert "invoice" in info["utterances"]

    def test_get_route_info_not_found(self, sample_tree: Path):
        """Test getting route info for non-existent route."""
        learner = RoutingLearner(sample_tree)

        info = learner.get_route_info("nonexistent")
        assert info is None


class TestRoutingLearnerGetKnownIssuers:
    """Tests for get_known_issuers method."""

    def test_get_known_issuers(self, sample_tree: Path):
        """Test getting known issuers."""
        learner = RoutingLearner(sample_tree)

        issuers = learner.get_known_issuers()

        assert "banques" in issuers
        assert "UBS" in issuers["banques"]
        assert "assurances" in issuers
        assert "Allianz" in issuers["assurances"]

    def test_get_known_issuers_empty(self, empty_tree: Path):
        """Test getting known issuers when none exist."""
        learner = RoutingLearner(empty_tree)

        issuers = learner.get_known_issuers()
        assert issuers == {}


class TestRoutingLearnerTreeCaching:
    """Tests for tree caching behavior."""

    def test_tree_loaded_once(self, sample_tree: Path):
        """Test that tree is only loaded once."""
        learner = RoutingLearner(sample_tree)

        # First call loads tree
        learner.list_routes()
        tree1 = learner._tree

        # Second call uses cached tree
        learner.list_routes()
        tree2 = learner._tree

        assert tree1 is tree2

    def test_save_tree_none_does_nothing(self, sample_tree: Path):
        """Test that _save_tree does nothing if tree is None."""
        learner = RoutingLearner(sample_tree)
        # Tree not loaded yet
        learner._save_tree()
        # Should not raise
