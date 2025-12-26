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
        force=True,  # Override any existing configuration
    )


@app.command()
def classify(
    files: Annotated[list[Path], typer.Argument(help="Path(s) to file(s) to classify")],
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
    """Classify one or more files using the PARA method."""
    setup_logging(verbose=verbose)

    # Load configuration
    try:
        config = load_config()
    except ValidationError:
        logger.exception("Configuration error")
        raise typer.Exit(1) from None

    # Override config with CLI args if provided
    if reference_tree:
        config.reference_tree_path = reference_tree

    # Create pipeline once for all files
    pipeline = ClassificationPipeline(config)

    results = []
    for file in files:
        file_path = file.resolve()

        if not file_path.exists():
            logger.warning("File not found: %s", file_path)
            continue

        if not file_path.is_file():
            logger.warning("Not a file: %s", file_path)
            continue

        try:
            result = pipeline.classify_file(file_path)
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
                results.append(output)
            else:
                typer.echo(f"\n📄 {file_path.name}")
                typer.echo(f"   Category: {result.category}")
                typer.echo(
                    f"   Confidence: {result.confidence.value:.0%} ({result.confidence.source.value})"
                )
                typer.echo(f"   Target: {target_path}")
                if result.route_name:
                    typer.echo(f"   Route: {result.route_name}")
        except Exception as e:
            logger.error("Failed to classify %s: %s", file_path, e)
            if output_json:
                results.append({"source_file": str(file_path), "error": str(e)})

    if output_json:
        typer.echo(json.dumps(results, indent=2))


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
    """Add a new issuer to the reference tree."""
    from para_files.learner import RoutingLearner

    # Determine reference tree path
    tree_path = reference_tree
    if tree_path is None:
        try:
            config = load_config()
            tree_path = config.reference_tree_path
        except ValidationError:
            tree_path = Path("personal_file_tree.yaml")

    if not tree_path.exists():
        typer.echo(f"Reference tree not found: {tree_path}", err=True)
        raise typer.Exit(1)

    learner = RoutingLearner(tree_path)

    # Show available categories if needed
    categories = learner.list_issuer_categories()
    if category not in categories:
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
    """Add a new utterance to a route for better matching."""
    from para_files.learner import RoutingLearner

    # Determine reference tree path
    tree_path = reference_tree
    if tree_path is None:
        try:
            config = load_config()
            tree_path = config.reference_tree_path
        except ValidationError:
            tree_path = Path("personal_file_tree.yaml")

    if not tree_path.exists():
        typer.echo(f"Reference tree not found: {tree_path}", err=True)
        raise typer.Exit(1)

    learner = RoutingLearner(tree_path)

    if learner.add_utterance(route, utterance):
        typer.echo(f"Added utterance '{utterance}' to route '{route}'")
    else:
        # Check if route exists
        if learner.get_route_info(route) is None:
            typer.echo(f"Route '{route}' not found", err=True)
            typer.echo("Available routes:")
            for r in learner.list_routes():
                typer.echo(f"  - {r}")
            raise typer.Exit(1)
        typer.echo(f"Utterance '{utterance}' already exists in route '{route}'")


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
    """List all available routes in the reference tree."""
    from para_files.learner import RoutingLearner

    # Determine reference tree path
    tree_path = reference_tree
    if tree_path is None:
        try:
            config = load_config()
            tree_path = config.reference_tree_path
        except ValidationError:
            tree_path = Path("personal_file_tree.yaml")

    if not tree_path.exists():
        typer.echo(f"Reference tree not found: {tree_path}", err=True)
        raise typer.Exit(1)

    learner = RoutingLearner(tree_path)
    routes = learner.list_routes()

    if not routes:
        typer.echo("No routes found")
        return

    max_utterances_shown = 5
    typer.echo(f"Available routes ({len(routes)}):")
    for route_name in routes:
        if show_utterances:
            route_info = learner.get_route_info(route_name)
            utterances = route_info.get("utterances", []) if route_info else []
            typer.echo(f"\n  {route_name}:")
            for utt in utterances[:max_utterances_shown]:
                typer.echo(f"    - {utt}")
            if len(utterances) > max_utterances_shown:
                remaining = len(utterances) - max_utterances_shown
                typer.echo(f"    ... and {remaining} more")
        else:
            typer.echo(f"  - {route_name}")


@app.command("issuers")
def list_issuers(
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
) -> None:
    """List all known issuers by category."""
    from para_files.learner import RoutingLearner

    # Determine reference tree path
    tree_path = reference_tree
    if tree_path is None:
        try:
            config = load_config()
            tree_path = config.reference_tree_path
        except ValidationError:
            tree_path = Path("personal_file_tree.yaml")

    if not tree_path.exists():
        typer.echo(f"Reference tree not found: {tree_path}", err=True)
        raise typer.Exit(1)

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


@app.command()
def scan(
    directory: Annotated[Path, typer.Argument(help="Directory to scan for files")],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", "-R", help="Scan subdirectories recursively"),
    ] = False,
    extensions: Annotated[
        str | None,
        typer.Option("--ext", "-e", help="Filter by extensions (comma-separated, e.g., '.pdf,.docx')"),
    ] = None,
    output_json: Annotated[
        bool, typer.Option("--json", "-j", help="Output results as JSON")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Scan a directory and preview file classifications without moving."""
    setup_logging(verbose=verbose)

    dir_path = directory.resolve()

    if not dir_path.exists():
        logger.error("Directory not found: %s", dir_path)
        raise typer.Exit(1)

    if not dir_path.is_dir():
        logger.error("Not a directory: %s", dir_path)
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

    # Parse extensions filter
    ext_filter: set[str] | None = None
    if extensions:
        ext_filter = {ext.strip().lower() if ext.startswith(".") else f".{ext.strip().lower()}"
                      for ext in extensions.split(",")}

    # Find files
    if recursive:
        files = list(dir_path.rglob("*"))
    else:
        files = list(dir_path.glob("*"))

    # Filter to only files (not directories)
    files = [f for f in files if f.is_file()]

    # Apply extension filter
    if ext_filter:
        files = [f for f in files if f.suffix.lower() in ext_filter]

    if not files:
        typer.echo("No files found matching criteria")
        return

    # Create pipeline once for all files
    pipeline = ClassificationPipeline(config)

    results = []
    stats: dict[str, int] = {}

    for file_path in sorted(files):
        try:
            result = pipeline.classify_file(file_path)
            target_path = pipeline.get_target_path(result)

            # Track stats by source
            source = result.confidence.source.value
            stats[source] = stats.get(source, 0) + 1

            if output_json:
                output = {
                    "source_file": str(file_path),
                    "filename": file_path.name,
                    "category": result.category,
                    "confidence": result.confidence.value,
                    "source": source,
                    "target_path": str(target_path),
                }
                if result.route_name:
                    output["route_name"] = result.route_name
                results.append(output)
            else:
                confidence_pct = f"{result.confidence.value:.0%}"
                typer.echo(f"📄 {file_path.name}")
                typer.echo(f"   → {result.category} ({confidence_pct} {source})")

        except Exception as e:
            logger.warning("Failed to classify %s: %s", file_path.name, e)
            if output_json:
                results.append({
                    "source_file": str(file_path),
                    "filename": file_path.name,
                    "error": str(e),
                })

    if output_json:
        output_data = {
            "directory": str(dir_path),
            "total_files": len(files),
            "stats": stats,
            "results": results,
        }
        typer.echo(json.dumps(output_data, indent=2))
    else:
        typer.echo(f"\n📊 Summary: {len(files)} files scanned")
        for source, count in sorted(stats.items(), key=lambda x: -x[1]):
            typer.echo(f"   {source}: {count}")


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
