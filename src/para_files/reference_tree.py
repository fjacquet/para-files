"""Reference tree loader for PARA file structure.

Loads and parses personal_file_tree.yaml to extract:
- PARA folder structure (inbox, projects, areas, resources, archives)
- Semantic routing utterances for each category
- Special routing rules (photos, videos, courses)
- Known issuers database for domain-based classification
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from para_files.types import (
    IssuerCategory,
    KnownIssuers,
    Route,
    RoutingRule,
    RuleIssuer,
)


class RoutingRuleModel(BaseModel):
    """Validation model for a single routing rule in the YAML."""

    extensions: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    destination: str = Field(min_length=1)
    source: str | None = None
    date_source: str | None = None
    fallback_date: str | None = None
    action: str | None = None
    platforms: list[str] | None = None
    issuers: list[dict[str, Any]] = Field(default_factory=list)
    known_technologies: list[str] = Field(default_factory=list)


class ReferenceTreeModel(BaseModel):
    """Validation model for the top-level YAML structure."""

    version: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    routing_rules: dict[str, RoutingRuleModel] = Field(default_factory=dict)
    inbox: dict[str, Any] | None = None
    projects: dict[str, Any] | None = None
    areas: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    archives: dict[str, Any] | None = None

    model_config = {"extra": "allow"}  # Allow unknown top-level keys


class ReferenceTree:
    """Manages the PARA reference tree from YAML configuration.

    The reference tree defines the classification structure for files,
    including semantic utterances for each category and special routing rules.
    """

    def __init__(self, yaml_path: Path) -> None:
        """Initialize with path to YAML configuration.

        Args:
            yaml_path: Path to personal_file_tree.yaml or similar.
        """
        self._yaml_path = yaml_path
        self._data: dict[str, Any] = {}
        self._routes: list[Route] = []
        self._routing_rules: dict[str, RoutingRule] = {}
        self._known_issuers: KnownIssuers = KnownIssuers()
        self._loaded = False

    def load(self) -> None:
        """Load and parse the YAML configuration file.

        Raises:
            FileNotFoundError: If the YAML file doesn't exist.
            yaml.YAMLError: If the YAML is malformed.
            ValueError: If the YAML is empty or fails Pydantic validation.
        """
        with self._yaml_path.open(encoding="utf-8") as f:
            raw_data: Any = yaml.safe_load(f)

        if raw_data is None:
            msg = f"Empty reference tree YAML: {self._yaml_path}"
            raise ValueError(msg)

        self._data = raw_data

        # Validate YAML structure with Pydantic
        try:
            ReferenceTreeModel(**self._data)
        except ValidationError as e:
            msg = f"Invalid reference tree YAML ({self._yaml_path}): {e}"
            raise ValueError(msg) from e

        self._parse_routing_rules()
        self._parse_categories()
        self._parse_known_issuers()
        self._loaded = True

    def _parse_routing_rules(self) -> None:
        """Parse special routing rules (photos, videos, courses, etc.)."""
        rules_data = self._data.get("routing_rules", {})

        for rule_name, rule_config in rules_data.items():
            if not isinstance(rule_config, dict):
                continue

            # Parse issuers if present (list of dicts with name and patterns)
            issuers_data = rule_config.get("issuers", [])
            issuers = [
                RuleIssuer(
                    name=issuer.get("name", ""),
                    patterns=issuer.get("patterns", []),
                )
                for issuer in issuers_data
                if isinstance(issuer, dict)
            ]

            self._routing_rules[rule_name] = RoutingRule(
                source=rule_config.get("source"),
                extensions=rule_config.get("extensions", []),
                patterns=rule_config.get("patterns", []),
                destination=rule_config.get("destination", ""),
                date_source=rule_config.get("date_source"),
                fallback_date=rule_config.get("fallback_date"),
                action=rule_config.get("action"),
                platforms=rule_config.get("platforms"),
                issuers=issuers,
                known_technologies=rule_config.get("known_technologies", []),
            )

    def _parse_categories(self) -> None:
        """Parse all PARA categories and extract routes with utterances."""
        # Parse each PARA section
        for section in ["inbox", "projects", "areas", "resources", "archives"]:
            section_data = self._data.get(section, {})
            if not section_data:
                continue

            self._parse_section_routes(section, section_data)

    def _parse_section_routes(self, section: str, data: dict[str, Any]) -> None:
        """Parse routes from a PARA section.

        Args:
            section: Section name (inbox, projects, etc.).
            data: Section data from YAML.
        """
        base_path = data.get("path", f"{section.title()}")

        # Handle section-level utterances (e.g., inbox)
        if "utterances" in data:
            self._routes.append(
                Route(
                    name=section,
                    pattern=base_path,
                    utterances=data["utterances"],
                    preserve_structure=data.get("preserve_structure", False),
                )
            )

        # Handle nested routes
        routes_data = data.get("routes", [])
        for route_data in routes_data:
            if not isinstance(route_data, dict):
                continue

            route_name = route_data.get("name", "")
            pattern = route_data.get("pattern", "")
            utterances = route_data.get("utterances", [])

            if route_name and utterances:
                self._routes.append(
                    Route(
                        name=route_name,
                        pattern=pattern,
                        utterances=utterances,
                        preserve_structure=route_data.get("preserve_structure", False),
                        date_format=route_data.get("date_format"),
                    )
                )

    def _parse_known_issuers(self) -> None:
        """Parse known issuers database from YAML.

        Dynamically loads all categories - no hardcoded category names.
        Each category in YAML should have 'pattern' and 'issuers' keys.
        """
        issuers_data = self._data.get("known_issuers", {})
        categories: dict[str, IssuerCategory] = {}

        for category_name, category_data in issuers_data.items():
            if isinstance(category_data, dict):
                categories[category_name] = IssuerCategory(
                    pattern=category_data.get("pattern", ""),
                    issuers=category_data.get("issuers", []),
                )

        self._known_issuers = KnownIssuers(categories=categories)

    def get_all_routes(self) -> list[Route]:
        """Return all routes flattened for semantic router.

        Returns:
            List of Route objects with names and utterances.

        Raises:
            RuntimeError: If tree hasn't been loaded yet.
        """
        if not self._loaded:
            msg = "Reference tree not loaded. Call load() first."
            raise RuntimeError(msg)
        return self._routes

    def get_routing_rules(self) -> dict[str, RoutingRule]:
        """Return special routing rules (photos, videos, courses, etc.).

        Returns:
            Dictionary mapping rule name to RoutingRule.

        Raises:
            RuntimeError: If tree hasn't been loaded yet.
        """
        if not self._loaded:
            msg = "Reference tree not loaded. Call load() first."
            raise RuntimeError(msg)
        return self._routing_rules

    def get_known_issuers(self) -> KnownIssuers:
        """Return known issuers database.

        Returns:
            KnownIssuers instance with all issuer categories.

        Raises:
            RuntimeError: If tree hasn't been loaded yet.
        """
        if not self._loaded:
            msg = "Reference tree not loaded. Call load() first."
            raise RuntimeError(msg)
        return self._known_issuers

    def get_route_by_name(self, name: str) -> Route | None:
        """Find a route by its name.

        Args:
            name: Route name to find.

        Returns:
            Route if found, None otherwise.
        """
        for route in self._routes:
            if route.name == name:
                return route
        return None

    def resolve_pattern(
        self,
        pattern: str,
        params: dict[str, str] | None = None,
        date: datetime | None = None,
    ) -> str:
        """Resolve a pattern with parameters and date placeholders.

        Args:
            pattern: Pattern with placeholders like '{year}', '{YYYY}', '{issuer}'.
            params: Parameter values to substitute.
            date: Date for YYYY/MM/DD placeholders.

        Returns:
            Resolved path string.

        Examples:
            >>> tree.resolve_pattern("4_Archives/factures/{year}", {"year": "2025"})
            '4_Archives/factures/2025'
            >>> tree.resolve_pattern("4_Archives/photos/{YYYY}/{MM}/{DD}", date=datetime.now())
            '4_Archives/photos/2025/12/25'
        """
        result = pattern
        params = params or {}

        # Substitute named parameters
        for key, value in params.items():
            result = result.replace(f"{{{key}}}", value)

        # Substitute date placeholders
        if date:
            result = result.replace("{YYYY}", str(date.year))
            result = result.replace("{MM}", f"{date.month:02d}")
            result = result.replace("{DD}", f"{date.day:02d}")

        return result

    def match_routing_rule(
        self,
        filename: str,
        extension: str,
    ) -> tuple[str, RoutingRule] | None:
        """Find a matching routing rule for a file.

        Args:
            filename: Name of the file (without path).
            extension: File extension including dot.

        Returns:
            Tuple of (rule_name, RoutingRule) if matched, None otherwise.
        """
        ext_lower = extension.lower()

        for rule_name, rule in self._routing_rules.items():
            # Check extension match
            if rule.extensions and ext_lower in [e.lower() for e in rule.extensions]:
                return (rule_name, rule)

            # Check pattern match
            if rule.patterns:
                for pattern in rule.patterns:
                    # Convert glob pattern to regex
                    regex_pattern = self._glob_to_regex(pattern)
                    if re.match(regex_pattern, filename, re.IGNORECASE):
                        return (rule_name, rule)

        return None

    @staticmethod
    def _glob_to_regex(pattern: str) -> str:
        """Convert a glob pattern to a regex pattern.

        Args:
            pattern: Glob pattern with * and ? wildcards.

        Returns:
            Regex pattern string.
        """
        # Escape special regex characters except * and ?
        escaped = re.escape(pattern)
        # Convert glob wildcards to regex
        escaped = escaped.replace(r"\*", ".*")
        escaped = escaped.replace(r"\?", ".")
        return f"^{escaped}$"


def load_reference_tree(yaml_path: Path) -> ReferenceTree:
    """Convenience function to load a reference tree from YAML.

    Args:
        yaml_path: Path to the YAML configuration file.

    Returns:
        Loaded ReferenceTree instance.
    """
    tree = ReferenceTree(yaml_path)
    tree.load()
    return tree
