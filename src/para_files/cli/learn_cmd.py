"""Learn command for interactive classification learning.

This module provides the learn command that allows users to interactively
correct classifications and improve the routing model by adding keywords
to routes.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from para_files.cli.app import app
from para_files.cli.shared import (
    ensure_tree_exists,
    load_config_or_exit,
    print_classification_result,
    setup_logging,
)
from para_files.pipeline import ClassificationPipeline
from para_files.utils.validation import validate_file_exists


if TYPE_CHECKING:
    from para_files.learner import RoutingLearner


def _select_route_from_choice(choice: str, routes: list[str]) -> str | None:
    """Parse user route selection choice.

    Handles both numeric selection (1, 2, 3...) and direct route name input.

    Args:
        choice: User's input - either a number or route name.
        routes: List of available route names.

    Returns:
        The selected route name, or None if selection was invalid.
    """
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(routes):
            return routes[idx]
    elif choice in routes:
        return choice
    return None


def _handle_keyword_addition(learner: RoutingLearner, route: str) -> None:
    """Handle optional keyword addition during learning.

    Prompts the user to optionally add a keyword from the document
    content to improve future matching accuracy.

    Args:
        learner: The RoutingLearner instance to add keywords to.
        route: The route to add keywords to.
    """
    if not typer.confirm("Would you like to add a keyword to improve matching?", default=True):
        return

    keyword = typer.prompt("Enter keyword to add (from document content)")
    if keyword.strip():
        if learner.add_utterance(route, keyword.strip()):
            typer.echo(f"Added keyword '{keyword}' to route '{route}'")
        else:
            typer.echo("Keyword already exists or could not be added")


@app.command()
def learn(
    file: Annotated[Path, typer.Argument(help="Path to file to learn from")],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Interactive classification learning from a file.

    Classifies a file using the full pipeline, then asks you to confirm
    or correct the classification. If you correct it, you can optionally
    add keywords to improve future matching.

    This is a key workflow for building up your routing model over time.
    """
    from para_files.learner import RoutingLearner

    setup_logging(verbose=verbose)
    file_path = file.resolve()
    if not validate_file_exists(file_path, exit_on_error=True):
        return

    config = load_config_or_exit()
    if reference_tree:
        config.reference_tree_path = reference_tree

    pipeline = ClassificationPipeline(config)
    result = pipeline.classify_file(file_path)
    target_path = pipeline.get_target_path(result)

    print_classification_result(file_path, result, target_path)

    if typer.confirm("\nIs this classification correct?", default=True):
        typer.echo("Classification confirmed. No changes needed.")
        return

    ensure_tree_exists(config.reference_tree_path)
    learner = RoutingLearner(config.reference_tree_path)
    routes = learner.list_routes()

    typer.echo("\nAvailable routes:")
    for i, route_name in enumerate(routes, 1):
        typer.echo(f"  {i}. {route_name}")

    choice = typer.prompt("\nEnter route number or name (or 'skip' to cancel)", default="skip")
    if choice.lower() == "skip":
        typer.echo("Learning cancelled.")
        return

    correct_route = _select_route_from_choice(choice, routes)
    if correct_route is None:
        typer.echo(f"Invalid selection: {choice}", err=True)
        raise typer.Exit(1)

    typer.echo(f"\nSelected route: {correct_route}")
    _handle_keyword_addition(learner, correct_route)
    typer.echo("\nLearning complete!")
