"""Main entry point for the PARA Files classification system.

CLI for classifying files using the 5-signal pipeline.
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from para_files.config import load_config
from para_files.mover import ConflictStrategy, move_classified_file
from para_files.pipeline import ClassificationPipeline


logger = logging.getLogger(__name__)

# Create the Typer app
app = typer.Typer(
    name="para-files",
    help="Classify files using the PARA method with MLX-powered semantic routing.",
    add_completion=True,
)


class ConflictChoice(str, Enum):
    """CLI choices for conflict strategy."""

    skip = "skip"
    overwrite = "overwrite"
    rename = "rename"
    rename_with_date = "rename_with_date"


def setup_logging(*, verbose: bool = False) -> None:
    """Configure logging.

    Args:
        verbose: Enable debug logging if True.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


@app.command()
def classify(
    file: Annotated[Path, typer.Argument(help="Path to file to classify")],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    output_json: Annotated[
        bool, typer.Option("--json", "-j", help="Output result as JSON")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Classify a file using the PARA method."""
    setup_logging(verbose=verbose)

    file_path = file.resolve()

    if not file_path.exists():
        logger.error("File not found: %s", file_path)
        raise typer.Exit(1)

    if not file_path.is_file():
        logger.error("Not a file: %s", file_path)
        raise typer.Exit(1)

    # Load configuration
    try:
        config = load_config()
    except ValidationError:
        logger.exception("Configuration error")
        raise typer.Exit(1) from None

    # Override config with CLI args if provided
    if reference_tree:
        config.reference_tree_path = reference_tree

    # Create pipeline and classify
    pipeline = ClassificationPipeline(config)
    result = pipeline.classify_file(file_path)

    # Output result
    target_path = pipeline.get_target_path(result)

    if output_json:
        output = {
            "source_file": str(file_path),
            "category": result.category,
            "confidence": result.confidence.value,
            "source": result.confidence.source.value,
            "target_path": str(target_path),
        }
        if result.route_name:
            output["route_name"] = result.route_name
        if result.extracted_params:
            output["params"] = result.extracted_params
        typer.echo(json.dumps(output, indent=2))
    else:
        typer.echo(f"Category: {result.category}")
        typer.echo(
            f"Confidence: {result.confidence.value:.0%} ({result.confidence.source.value})"
        )
        typer.echo(f"Target: {target_path}")
        if result.route_name:
            typer.echo(f"Route: {result.route_name}")


@app.command()
def move(
    file: Annotated[Path, typer.Argument(help="Path to file to classify and move")],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview the move without actually moving files"),
    ] = False,
    copy: Annotated[
        bool,
        typer.Option("--copy", "-c", help="Copy file instead of moving (preserve original)"),
    ] = False,
    conflict: Annotated[
        ConflictChoice,
        typer.Option(help="Strategy for handling existing files"),
    ] = ConflictChoice.rename,
    date_prefix: Annotated[
        bool,
        typer.Option("--date-prefix", "-d", help="Add date prefix (YYYY-MM-DD) to filename"),
    ] = False,
    output_json: Annotated[
        bool, typer.Option("--json", "-j", help="Output result as JSON")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Classify and move a file to its PARA destination."""
    setup_logging(verbose=verbose)

    file_path = file.resolve()

    if not file_path.exists():
        logger.error("File not found: %s", file_path)
        raise typer.Exit(1)

    if not file_path.is_file():
        logger.error("Not a file: %s", file_path)
        raise typer.Exit(1)

    # Load configuration
    try:
        config = load_config()
    except ValidationError:
        logger.exception("Configuration error")
        raise typer.Exit(1) from None

    # Override config with CLI args if provided
    if reference_tree:
        config.reference_tree_path = reference_tree

    # Create pipeline and classify
    pipeline = ClassificationPipeline(config)
    result = pipeline.classify_file(file_path)
    target_dir = pipeline.get_target_path(result)

    # Convert conflict choice to strategy
    conflict_strategy = ConflictStrategy(conflict.value)

    # Move the file
    move_result = move_classified_file(
        file_path,
        target_dir,
        dry_run=dry_run,
        copy_mode=copy,
        conflict_strategy=conflict_strategy,
        add_date_prefix=date_prefix,
    )

    # Output result
    if output_json:
        output = {
            "source_file": str(file_path),
            "category": result.category,
            "confidence": result.confidence.value,
            "source": result.confidence.source.value,
            "target_path": str(target_dir),
            "destination": str(move_result.destination),
            "action": move_result.action,
            "success": move_result.success,
        }
        if move_result.message:
            output["message"] = move_result.message
        if result.route_name:
            output["route_name"] = result.route_name
        typer.echo(json.dumps(output, indent=2))
    else:
        action_verb = "Would move" if dry_run else "Moved"
        if copy:
            action_verb = "Would copy" if dry_run else "Copied"

        if move_result.success:
            typer.echo(f"{action_verb}: {file_path.name}")
            typer.echo(f"  -> {move_result.destination}")
            typer.echo(
                f"Classification: {result.category} "
                f"({result.confidence.value:.0%} {result.confidence.source.value})"
            )
        else:
            typer.echo(f"Failed: {move_result.message}", err=True)
            raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool, typer.Option("--version", "-V", help="Show version and exit")
    ] = False,
) -> None:
    """PARA Files - Intelligent file classification with MLX."""
    if version:
        from para_files import __version__

        typer.echo(f"para-files {__version__}")
        raise typer.Exit

    # If no command is provided, show help
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


def cli() -> None:
    """CLI entry point for console script."""
    app()


if __name__ == "__main__":
    cli()
