"""Learning module for extending routing rules.

Provides functions to add issuers and utterances to the reference tree.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from loguru import logger


class RoutingLearner:
    """Manages reference tree modifications for routing extensions."""

    def __init__(self, reference_tree_path: Path) -> None:
        """Initialize the learner.

        Args:
            reference_tree_path: Path to the reference tree YAML file.
        """
        self.reference_tree_path = reference_tree_path
        self._tree: dict[str, Any] | None = None

    def _load_tree(self) -> dict[str, Any]:
        """Load the reference tree from YAML."""
        if self._tree is None:
            with self.reference_tree_path.open("r", encoding="utf-8") as f:
                self._tree = yaml.safe_load(f)
        return self._tree

    def _save_tree(self) -> None:
        """Save the reference tree to YAML."""
        if self._tree is None:
            return
        with self.reference_tree_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                self._tree,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                width=100,
            )

    def list_routes(self) -> list[str]:
        """List all available route names.

        Returns:
            List of route names.
        """
        tree = self._load_tree()
        routes: list[str] = []

        # Collect routes from all sections
        for section in ["projects", "areas", "resources", "archives"]:
            if section in tree and "routes" in tree[section]:
                routes.extend(route["name"] for route in tree[section]["routes"] if "name" in route)

        return routes

    def list_issuer_categories(self) -> list[str]:
        """List all issuer categories.

        Returns:
            List of category names (e.g., 'assurances', 'banques').
        """
        tree = self._load_tree()
        if "known_issuers" in tree:
            return list(tree["known_issuers"].keys())
        return []

    def add_issuer(self, issuer: str, category: str) -> bool:
        """Add a new issuer to a category.

        Args:
            issuer: Name of the issuer to add.
            category: Category to add the issuer to (e.g., 'transport', 'banques').

        Returns:
            True if added successfully, False if already exists.
        """
        tree = self._load_tree()

        if "known_issuers" not in tree:
            tree["known_issuers"] = {}

        if category not in tree["known_issuers"]:
            tree["known_issuers"][category] = []

        # Check if already exists
        issuers = tree["known_issuers"][category]
        if issuer in issuers:
            logger.info("Issuer '{}' already exists in category '{}'", issuer, category)
            return False

        issuers.append(issuer)
        self._save_tree()
        logger.info("Added issuer '{}' to category '{}'", issuer, category)
        return True

    def add_utterance(self, route_name: str, utterance: str) -> bool:
        """Add a new utterance to a route.

        Args:
            route_name: Name of the route to update.
            utterance: New utterance to add.

        Returns:
            True if added successfully, False if already exists or route not found.
        """
        tree = self._load_tree()

        # Search all sections for the route
        for section in ["projects", "areas", "resources", "archives"]:
            if section not in tree or "routes" not in tree[section]:
                continue

            for route in tree[section]["routes"]:
                if route.get("name") == route_name:
                    if "utterances" not in route:
                        route["utterances"] = []

                    if utterance in route["utterances"]:
                        logger.info(
                            "Utterance '%s' already exists in route '%s'",
                            utterance,
                            route_name,
                        )
                        return False

                    route["utterances"].append(utterance)
                    self._save_tree()
                    logger.info(
                        "Added utterance '%s' to route '%s'",
                        utterance,
                        route_name,
                    )
                    return True

        logger.warning("Route '{}' not found", route_name)
        return False

    def get_route_info(self, route_name: str) -> dict[str, Any] | None:
        """Get information about a specific route.

        Args:
            route_name: Name of the route.

        Returns:
            Route configuration dict or None if not found.
        """
        tree = self._load_tree()

        for section in ["projects", "areas", "resources", "archives"]:
            if section not in tree or "routes" not in tree[section]:
                continue

            for route in tree[section]["routes"]:
                if route.get("name") == route_name:
                    result: dict[str, Any] = route
                    return result

        return None

    def get_known_issuers(self) -> dict[str, list[str]]:
        """Get all known issuers by category.

        Returns:
            Dictionary mapping category to list of issuers.
        """
        tree = self._load_tree()
        issuers: dict[str, list[str]] = tree.get("known_issuers", {})
        return issuers
