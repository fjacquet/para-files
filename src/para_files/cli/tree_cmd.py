"""Tree command for viewing and validating reference tree structure.

This module provides the tree command that displays the reference tree
configuration, including routes, utterances, routing rules, and known
issuers. It also supports validation of the tree structure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from para_files.cli.app import app
from para_files.cli.shared import (
    MAX_PATTERNS_SHOWN,
    ensure_tree_exists,
    get_reference_tree_path,
    setup_logging,
)


def _show_tree_sections(
    tree_data: dict[str, Any],
    *,
    validate: bool,
    errors: list[str],
    warnings: list[str],
) -> tuple[int, int]:
    """Show tree sections and return route/utterance counts.

    Iterates through all PARA sections (inbox, projects, areas, resources,
    archives) and displays their routes and utterance counts.

    Args:
        tree_data: Parsed YAML data from the reference tree file.
        validate: If True, check for structural issues.
        errors: List to append validation errors to.
        warnings: List to append validation warnings to.

    Returns:
        Tuple of (total route count, total utterance count).
    """
    sections = ["inbox", "projects", "areas", "resources", "archives"]
    route_count = 0
    utterance_count = 0

    for section in sections:
        section_data = tree_data.get(section, {})
        if not section_data:
            if validate:
                warnings.append(f"Section '{section}' is empty or missing")
            continue

        path = section_data.get("path", section)
        routes = section_data.get("routes", [])
        route_count += len(routes)

        typer.echo(f"\n\U0001f4c2 {path}")

        for route in routes:
            name = route.get("name", "unnamed")
            pattern = route.get("pattern", "")
            utts = route.get("utterances", [])
            utterance_count += len(utts)

            if validate:
                if not pattern:
                    errors.append(f"Route '{name}' has no pattern")
                if not utts:
                    warnings.append(f"Route '{name}' has no utterances")

            typer.echo(f"   \u2514\u2500\u2500 {name}: {pattern} ({len(utts)} utterances)")

    return route_count, utterance_count


def _show_routing_rules(tree_data: dict[str, Any]) -> None:
    """Show routing rules from tree data.

    Displays glob-based routing rules that match files by extension
    or filename pattern.

    Args:
        tree_data: Parsed YAML data from the reference tree file.
    """
    rules = tree_data.get("routing_rules", {})
    if not rules:
        return

    typer.echo("\n\u2699\ufe0f  Routing Rules:")
    max_show = 5
    for rule_name, rule_data in rules.items():
        dest = rule_data.get("destination", "N/A")
        exts = rule_data.get("extensions", [])
        patterns = rule_data.get("patterns", [])
        typer.echo(f"   \u2514\u2500\u2500 {rule_name}:")
        if exts:
            ext_str = ", ".join(exts[:max_show])
            suffix = "..." if len(exts) > max_show else ""
            typer.echo(f"       Extensions: {ext_str}{suffix}")
        if patterns:
            pat_str = ", ".join(patterns[:MAX_PATTERNS_SHOWN])
            suffix = "..." if len(patterns) > MAX_PATTERNS_SHOWN else ""
            typer.echo(f"       Patterns: {pat_str}{suffix}")
        typer.echo(f"       \u2192 {dest}")


def _show_known_issuers(tree_data: dict[str, Any], *, verbose: bool) -> None:
    """Show known issuers from tree data.

    Displays the domain knowledge base of known document issuers
    (banks, insurance companies, utilities, etc.) and their mappings.

    Args:
        tree_data: Parsed YAML data from the reference tree file.
        verbose: If True, list all individual issuers.
    """
    known_issuers = tree_data.get("known_issuers", {})
    if not known_issuers:
        return

    typer.echo("\n\U0001f3e2 Known Issuers:")
    issuer_count = 0
    for category, category_data in known_issuers.items():
        issuers = category_data.get("issuers", [])
        issuer_count += len(issuers)
        pattern = category_data.get("pattern", "")
        typer.echo(f"   \u2514\u2500\u2500 {category}: {len(issuers)} issuers \u2192 {pattern}")
        if verbose:
            for issuer in issuers:
                typer.echo(f"       - {issuer}")
    typer.echo(f"\n   Total: {issuer_count} issuers across {len(known_issuers)} categories")


def _print_validation_results(
    errors: list[str],
    warnings: list[str],
) -> None:
    """Print validation results and exit if errors.

    Displays any validation errors and warnings found during tree analysis.
    Exits with code 1 if errors were found.

    Args:
        errors: List of validation errors (critical issues).
        warnings: List of validation warnings (non-critical issues).

    Raises:
        typer.Exit: If errors were found, exits with code 1.
    """
    if errors:
        typer.echo("\n\u274c Errors:", err=True)
        for error in errors:
            typer.echo(f"   - {error}", err=True)

    if warnings:
        typer.echo("\n\u26a0\ufe0f  Warnings:")
        for warning in warnings:
            typer.echo(f"   - {warning}")

    if not errors and not warnings:
        typer.echo("\n\u2705 Validation passed!")
    elif errors:
        raise typer.Exit(1)


@app.command()
def tree(
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    validate: Annotated[
        bool,
        typer.Option("--validate", help="Validate reference tree structure"),
    ] = False,
    show_issuers: Annotated[
        bool,
        typer.Option("--issuers", "-i", help="Show known issuers"),
    ] = False,
    show_rules: Annotated[
        bool,
        typer.Option("--rules", help="Show routing rules"),
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Show or validate the reference tree structure.

    Displays information about the reference tree YAML file, including:
    - Version and generation date
    - Routes organized by PARA section
    - Utterance counts per route
    - Optional: routing rules and known issuers

    Use --validate to check for structural issues in the tree.
    """
    import yaml

    setup_logging(verbose=verbose)

    tree_path = get_reference_tree_path(reference_tree)
    ensure_tree_exists(tree_path)

    with tree_path.open() as f:
        tree_data = yaml.safe_load(f)

    version = tree_data.get("version", "unknown")
    generated = tree_data.get("generated", "unknown")
    typer.echo(f"\U0001f4da Reference Tree: {tree_path}")
    typer.echo(f"   Version: {version} | Generated: {generated}")

    errors: list[str] = []
    warnings: list[str] = []

    route_count, utterance_count = _show_tree_sections(
        tree_data, validate=validate, errors=errors, warnings=warnings
    )

    if show_rules:
        _show_routing_rules(tree_data)

    if show_issuers:
        _show_known_issuers(tree_data, verbose=verbose)

    typer.echo(f"\n\U0001f4ca Summary: {route_count} routes, {utterance_count} utterances")

    if validate:
        _print_validation_results(errors, warnings)
