"""Learn command for interactive classification learning.

This module provides the learn command that allows users to interactively
correct classifications and improve the routing model by adding keywords
to routes. Corrections are also tracked for pattern learning.
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
from para_files.learning import FeedbackTracker
from para_files.pipeline import ClassificationPipeline
from para_files.utils.validation import validate_file_exists


if TYPE_CHECKING:
    from para_files.learner import RoutingLearner
    from para_files.types import ClassificationResult


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


def _track_correction(
    file_path: Path,
    original_result: ClassificationResult | None,
    corrected_route: str,
    content_preview: str,
) -> None:
    """Track the correction in FeedbackTracker for pattern learning.

    Args:
        file_path: Path to the file being corrected.
        original_result: The original classification result (may be None).
        corrected_route: The user-selected correct route.
        content_preview: Preview of file content for pattern extraction.
    """
    from para_files.utils.pdf_metadata import extract_pdf_metadata

    tracker = FeedbackTracker()

    # Extract metadata for pattern learning (PDF only for now)
    metadata_dict: dict[str, str | None] = {}
    if file_path.suffix.lower() == ".pdf":
        pdf_meta = extract_pdf_metadata(file_path)
        if pdf_meta:
            metadata_dict = {
                "author": pdf_meta.author,
                "title": pdf_meta.title,
                "creator": pdf_meta.creator,
            }

    original_category = original_result.category if original_result else None
    original_confidence = (
        original_result.confidence.value if original_result and original_result.confidence else 0.0
    )
    source = (
        original_result.confidence.source.value
        if original_result and original_result.confidence
        else "unknown"
    )

    tracker.record_correction(
        file_path=file_path,
        original_category=original_category,
        corrected_category=corrected_route,
        original_confidence=original_confidence,
        content_preview=content_preview,
        metadata=metadata_dict,
        source=source,
    )


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

    Corrections are tracked for pattern learning to improve future
    automatic classification accuracy.

    This is a key workflow for building up your routing model over time.
    """
    from para_files.learner import RoutingLearner
    from para_files.utils.file_utils import read_content_preview

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

    # Track correction for pattern learning
    content_preview = read_content_preview(file_path, max_chars=500)
    _track_correction(file_path, result, correct_route, content_preview)
    typer.echo("Correction tracked for pattern learning.")

    _handle_keyword_addition(learner, correct_route)
    typer.echo("\nLearning complete!")
