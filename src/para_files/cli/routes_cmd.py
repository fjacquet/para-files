"""Routes commands for managing semantic routing configuration.

This module provides commands for working with routes in the reference tree:
- list-routes: List all available routes
- list-issuers: List known issuers by category
- add-issuer: Add a new issuer to a category
- add-utterance: Add a new utterance to a route
- test-route: Test a route's configuration and match files
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer

from para_files.cli.app import app
from para_files.cli.shared import (
    MAX_UTTERANCES_SHOWN,
    ensure_tree_exists,
    get_reference_tree_path,
    load_config_or_exit,
    setup_logging,
)
from para_files.pipeline import ClassificationPipeline
from para_files.utils.validation import validate_file_exists


if TYPE_CHECKING:
    from para_files.learner import RoutingLearner


def _show_available_routes(learner: RoutingLearner) -> None:
    """Show available routes and exit with error.

    Displays a list of all available route names to help the user
    find the correct route when their input didn't match.

    Args:
        learner: The RoutingLearner instance to get routes from.

    Raises:
        typer.Exit: Always exits with code 1 after showing routes.
    """
    typer.echo("Available routes:")
    for r in learner.list_routes():
        typer.echo(f"  - {r}")
    raise typer.Exit(1)


def _print_route_with_utterances(learner: RoutingLearner, route_name: str) -> None:
    """Print route with its utterances.

    Displays a route name followed by its associated utterances,
    limiting output to MAX_UTTERANCES_SHOWN for readability.

    Args:
        learner: The RoutingLearner instance to get route info from.
        route_name: Name of the route to display.
    """
    route_info = learner.get_route_info(route_name)
    utterances = route_info.get("utterances", []) if route_info else []
    typer.echo(f"\n  {route_name}:")
    for utt in utterances[:MAX_UTTERANCES_SHOWN]:
        typer.echo(f"    - {utt}")
    if len(utterances) > MAX_UTTERANCES_SHOWN:
        remaining = len(utterances) - MAX_UTTERANCES_SHOWN
        typer.echo(f"    ... and {remaining} more")


def _print_route_details(route: str, route_info: dict[str, Any]) -> None:
    """Print route details.

    Displays comprehensive information about a route including its
    pattern and all utterances.

    Args:
        route: The route name.
        route_info: Dictionary containing route configuration.
    """
    typer.echo(f"\nRoute: {route}")
    if "pattern" in route_info:
        typer.echo(f"   Pattern: {route_info['pattern']}")
    if "utterances" in route_info:
        typer.echo(f"   Utterances ({len(route_info['utterances'])}):")
        for utterance in route_info["utterances"]:
            typer.echo(f"     - {utterance}")
    else:
        typer.echo("   Utterances: (none)")


def _test_file_against_route(
    file_path: Path,
    expected_route: str,
    reference_tree: Path | None,
) -> None:
    """Test a file against an expected route.

    Classifies the file using the full pipeline and compares the
    result against the expected route.

    Args:
        file_path: Path to the file to classify.
        expected_route: Name of the route expected to match.
        reference_tree: Optional custom reference tree path.
    """
    typer.echo(f"\nTesting file: {file_path.name}")

    config = load_config_or_exit()
    if reference_tree:
        config.reference_tree_path = reference_tree

    pipeline = ClassificationPipeline(config)
    result = pipeline.classify_file(file_path)

    typer.echo(f"   Classification: {result.category}")
    conf = result.confidence
    typer.echo(f"   Confidence: {conf.value:.0%} ({conf.source.value})")

    if not result.route_name:
        typer.echo("\n   No route matched (defaulted to inbox)")
    elif result.route_name == expected_route:
        typer.echo(f"   Matched route: {result.route_name}")
        typer.echo("\n   File matches this route!")
    else:
        typer.echo(f"   Matched route: {result.route_name}")
        typer.echo(f"\n   File matched different route: {result.route_name}")


@app.command("routes")
def list_routes(
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    show_utterances: Annotated[
        bool,
        typer.Option("--utterances", "-u", help="Show utterances for each route"),
    ] = False,
) -> None:
    """List all available routes in the reference tree.

    Routes are semantic categories that files can be classified into.
    Each route has a name, destination pattern, and associated utterances
    that help the semantic router identify matching files.
    """
    from para_files.learner import RoutingLearner

    tree_path = get_reference_tree_path(reference_tree)
    ensure_tree_exists(tree_path)
    learner = RoutingLearner(tree_path)
    routes = learner.list_routes()

    if not routes:
        typer.echo("No routes found")
        return

    typer.echo(f"Available routes ({len(routes)}):")
    for route_name in routes:
        if show_utterances:
            _print_route_with_utterances(learner, route_name)
        else:
            typer.echo(f"  - {route_name}")


@app.command("issuers")
def list_issuers(
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
) -> None:
    """List all known issuers by category.

    Known issuers are document sources (banks, insurance companies,
    utilities, etc.) that are mapped to specific PARA categories
    for high-confidence classification.
    """
    from para_files.learner import RoutingLearner

    tree_path = get_reference_tree_path(reference_tree)
    ensure_tree_exists(tree_path)
    learner = RoutingLearner(tree_path)
    known_issuers = learner.get_known_issuers()

    if not known_issuers:
        typer.echo("No issuers defined")
        return

    typer.echo("Known issuers by category:")
    for category, issuers in known_issuers.items():
        typer.echo(f"\n  {category}:")
        for issuer in issuers:
            typer.echo(f"    - {issuer}")


@app.command("add-issuer")
def add_issuer(
    issuer: Annotated[str, typer.Argument(help="Name of the issuer to add")],
    category: Annotated[
        str,
        typer.Option("--category", "-c", help="Category to add issuer to"),
    ],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
) -> None:
    """Add a new issuer to the reference tree.

    Issuers are document sources that should be routed to a specific
    category. Adding an issuer creates a high-confidence mapping that
    the Domain KB classifier uses.
    """
    from para_files.learner import RoutingLearner

    tree_path = get_reference_tree_path(reference_tree)
    ensure_tree_exists(tree_path)

    learner = RoutingLearner(tree_path)

    if category not in learner.list_issuer_categories():
        typer.echo(f"Creating new category: {category}")

    if learner.add_issuer(issuer, category):
        typer.echo(f"Added issuer '{issuer}' to category '{category}'")
    else:
        typer.echo(f"Issuer '{issuer}' already exists in '{category}'")


@app.command("add-utterance")
def add_utterance(
    route: Annotated[str, typer.Argument(help="Name of the route to update")],
    utterance: Annotated[str, typer.Argument(help="New utterance to add")],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
) -> None:
    """Add a new utterance to a route for better matching.

    Utterances are sample phrases that help the semantic router
    identify files belonging to a route. Adding more utterances
    improves classification accuracy.
    """
    from para_files.learner import RoutingLearner

    tree_path = get_reference_tree_path(reference_tree)
    ensure_tree_exists(tree_path)
    learner = RoutingLearner(tree_path)

    if learner.add_utterance(route, utterance):
        typer.echo(f"Added utterance '{utterance}' to route '{route}'")
    elif learner.get_route_info(route) is None:
        typer.echo(f"Route '{route}' not found", err=True)
        _show_available_routes(learner)
    else:
        typer.echo(f"Utterance '{utterance}' already exists in route '{route}'")


@app.command("test-route")
def test_route(
    route: Annotated[str, typer.Argument(help="Name of the route to test")],
    file: Annotated[
        Path | None,
        typer.Option("--file", "-f", help="Optional file to test against the route"),
    ] = None,  # noqa: PT028
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,  # noqa: PT028
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,  # noqa: PT028
) -> None:
    """Test a route's configuration and optionally match a file against it.

    Shows the route's pattern and utterances. If a file is provided,
    runs classification and shows whether the file would match this route.
    """
    from para_files.learner import RoutingLearner

    setup_logging(verbose=verbose)
    tree_path = get_reference_tree_path(reference_tree)
    ensure_tree_exists(tree_path)

    learner = RoutingLearner(tree_path)
    route_info = learner.get_route_info(route)

    if route_info is None:
        typer.echo(f"Route '{route}' not found", err=True)
        _show_available_routes(learner)
        raise typer.Exit(1)

    _print_route_details(route, route_info)

    if file is not None:
        file_path = file.resolve()
        if not validate_file_exists(file_path, exit_on_error=True):
            return
        _test_file_against_route(file_path, route, reference_tree)
