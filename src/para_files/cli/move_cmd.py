"""Move command for para-files CLI.

This module provides the 'move' command which classifies files and moves
(or copies) them to their appropriate PARA destinations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from loguru import logger

from para_files.cli.app import app
from para_files.cli.shared import (
    ConflictChoice,
    expand_paths_to_files,
    load_config_or_exit,
    parse_extensions_filter,
    setup_logging,
)
from para_files.mover import ConflictStrategy, move_classified_file
from para_files.pipeline import ClassificationPipeline
from para_files.utils.validation import validate_file_exists


if TYPE_CHECKING:
    from para_files.mover import MoveResult
    from para_files.types import ClassificationResult


def _format_move_result_json(
    file_path: Path,
    result: ClassificationResult,
    target_dir: Path,
    move_result: MoveResult,
) -> dict[str, Any]:
    """Format move result as JSON dict.

    Converts a move operation result into a dictionary suitable for
    JSON serialization.

    Args:
        file_path: Path to the source file.
        result: The classification result object.
        target_dir: The target directory path.
        move_result: The result of the move operation.

    Returns:
        Dictionary containing the move result data.
    """
    output: dict[str, Any] = {
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
    return output


def _process_single_move(
    file_path: Path,
    pipeline: ClassificationPipeline,
    *,
    dry_run: bool,
    copy: bool,
    conflict_strategy: ConflictStrategy,
    date_prefix: bool,
    smart_rename: bool,
) -> tuple[Any, Any, bool]:
    """Process a single file move.

    Classifies the file and performs the move/copy operation.

    Args:
        file_path: Path to the file to move.
        pipeline: The classification pipeline.
        dry_run: If True, simulate the move without actually moving.
        copy: If True, copy instead of move.
        conflict_strategy: Strategy for handling existing files.
        date_prefix: If True, add date prefix to filename.
        smart_rename: If True, use intelligent naming from metadata.

    Returns:
        Tuple of (classification result, move result, success boolean).
    """
    result = pipeline.classify_file(file_path)
    target_dir = pipeline.get_target_path(result)

    move_result = move_classified_file(
        file_path,
        target_dir,
        dry_run=dry_run,
        copy_mode=copy,
        conflict_strategy=conflict_strategy,
        add_date_prefix=date_prefix,
        smart_rename=smart_rename,
        classification=result,
    )
    return result, move_result, move_result.success


def _print_move_result(
    file_path: Path,
    result: ClassificationResult,
    move_result: MoveResult,
    action_verb: str,
) -> None:
    """Print move result to console.

    Displays the result of a file move operation.

    Args:
        file_path: Path to the source file.
        result: The classification result.
        move_result: The result of the move operation.
        action_verb: Verb to use in output ("Moved", "Copied", etc.)
    """
    if move_result.success:
        typer.echo(f"{action_verb}: {file_path.name}")
        typer.echo(f"  -> {move_result.destination}")
        conf = result.confidence
        typer.echo(f"  Classification: {result.category} ({conf.value:.0%})")
    else:
        typer.echo(f"Failed: {file_path.name} - {move_result.message}", err=True)


def _handle_move_file(
    file_path: Path,
    pipeline: ClassificationPipeline,
    results: list[dict[str, Any]],
    action_verb: str,
    *,
    dry_run: bool,
    copy: bool,
    conflict_strategy: ConflictStrategy,
    date_prefix: bool,
    smart_rename: bool,
    skip_unclassifiable: bool = False,
    output_json: bool,
) -> tuple[bool, bool]:
    """Handle a single file in move command.

    Processes a file through classification and move, handling
    all error cases and output formatting.

    Args:
        file_path: Path to the file to process.
        pipeline: The classification pipeline.
        results: List to append JSON results to.
        action_verb: Verb to use in output.
        dry_run: If True, simulate the move.
        copy: If True, copy instead of move.
        conflict_strategy: Strategy for handling conflicts.
        date_prefix: If True, add date prefix.
        smart_rename: If True, use intelligent naming.
        skip_unclassifiable: If True, skip files that can't be classified.
        output_json: If True, collect results for JSON output.

    Returns:
        Tuple of (success, skipped) - skipped is True if file was skipped
        due to skip_unclassifiable.
    """
    from para_files.types import ClassificationSource

    if not validate_file_exists(file_path):
        if output_json:
            results.append({"source_file": str(file_path), "error": "file validation failed"})
        return False, False

    try:
        # First classify to check if we should skip
        classification = pipeline.classify_file(file_path)

        # Skip unclassifiable files if requested
        if skip_unclassifiable and classification.confidence.source == ClassificationSource.DEFAULT:
            logger.info("Skipping unclassifiable file: %s", file_path)
            if output_json:
                results.append(
                    {
                        "source_file": str(file_path),
                        "skipped": True,
                        "reason": "unclassifiable",
                    }
                )
            else:
                typer.echo(f"  Skipped (unclassifiable): {file_path.name}")
            return True, True  # Success (not an error), but skipped

        result, move_result, success = _process_single_move(
            file_path,
            pipeline,
            dry_run=dry_run,
            copy=copy,
            conflict_strategy=conflict_strategy,
            date_prefix=date_prefix,
            smart_rename=smart_rename,
        )

        if output_json:
            target_dir = pipeline.get_target_path(result)
            results.append(_format_move_result_json(file_path, result, target_dir, move_result))
        else:
            _print_move_result(file_path, result, move_result, action_verb)

    except Exception:  # noqa: BLE001
        logger.exception("Failed to process %s", file_path)
        if output_json:
            results.append({"source_file": str(file_path), "error": "processing failed"})
        return False, False
    else:
        return success, False


def _cleanup_source_dirs(
    source_dirs: set[Path],
    *,
    dry_run: bool,
    output_json: bool,
) -> None:
    """Clean up empty directories in source locations after move.

    Removes empty directories that may have been left behind after
    moving all files from them.

    Args:
        source_dirs: Set of source directory paths to check.
        dry_run: If True, simulate the cleanup.
        output_json: If True, suppress console output.
    """
    from para_files.utils.cleanup import cleanup_empty_dirs

    for source_dir in source_dirs:
        if source_dir.exists():
            deleted = cleanup_empty_dirs(source_dir, dry_run=dry_run)
            if deleted and not output_json:
                typer.echo(f"  Cleaned up {len(deleted)} empty directories")


def _print_move_summary(
    success_count: int,
    skip_count: int,
    fail_count: int,
) -> None:
    """Print summary of move operation.

    Displays a summary of the batch move operation results.

    Args:
        success_count: Number of successfully moved files.
        skip_count: Number of skipped files.
        fail_count: Number of failed operations.
    """
    summary_parts = [f"{success_count} succeeded"]
    if skip_count:
        summary_parts.append(f"{skip_count} skipped")
    if fail_count:
        summary_parts.append(f"{fail_count} failed")
    typer.echo(f"\nSummary: {', '.join(summary_parts)}")


@app.command()
def move(
    files: Annotated[list[Path], typer.Argument(help="Path(s) to file(s) or directory to move")],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", "-R", help="Process directories recursively"),
    ] = False,
    extensions: Annotated[
        str | None,
        typer.Option("--ext", "-e", help="Filter by extensions (comma-separated)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run/--no-dry-run", "-n", help="Preview without moving files"),
    ] = False,
    copy: Annotated[
        bool,
        typer.Option("--copy", "-c", help="Copy file instead of moving"),
    ] = False,
    conflict: Annotated[
        ConflictChoice,
        typer.Option(help="Strategy for handling existing files"),
    ] = ConflictChoice.rename,
    date_prefix: Annotated[
        bool,
        typer.Option("--date-prefix", "-d", help="Add date prefix to filename"),
    ] = False,
    smart_rename: Annotated[
        bool,
        typer.Option("--smart-rename", "-s", help="Use intelligent naming from metadata"),
    ] = False,
    skip_unclassifiable: Annotated[
        bool,
        typer.Option("--skip-unclassifiable", help="Skip unclassifiable files"),
    ] = False,
    cleanup_empty: Annotated[
        bool,
        typer.Option("--cleanup-empty/--no-cleanup-empty", help="Remove empty dirs after move"),
    ] = True,
    output_json: Annotated[
        bool, typer.Option("--json", "-j", help="Output result as JSON")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Classify and move one or more files to their PARA destinations.

    Files are classified using the 5-signal pipeline and then moved
    (or copied) to their appropriate destination directories based
    on the classification result and the reference tree structure.
    """
    setup_logging(verbose=verbose)
    config = load_config_or_exit()

    if reference_tree:
        config.reference_tree_path = reference_tree

    # Expand directories to file lists
    ext_filter = parse_extensions_filter(extensions)
    expanded_files, source_dirs = expand_paths_to_files(
        files, recursive=recursive, ext_filter=ext_filter
    )

    if not expanded_files:
        typer.echo("No files found matching criteria")
        return

    pipeline = ClassificationPipeline(config)
    conflict_strategy = ConflictStrategy(conflict.value)
    results: list[dict[str, Any]] = []
    success_count = 0
    fail_count = 0
    skip_count = 0
    action_verb = (
        ("Would copy" if copy else "Would move") if dry_run else ("Copied" if copy else "Moved")
    )

    for resolved in expanded_files:
        source_dirs.add(resolved.parent)

        success, skipped = _handle_move_file(
            resolved,
            pipeline,
            results,
            action_verb,
            dry_run=dry_run,
            copy=copy,
            conflict_strategy=conflict_strategy,
            date_prefix=date_prefix,
            smart_rename=smart_rename,
            skip_unclassifiable=skip_unclassifiable,
            output_json=output_json,
        )
        if skipped:
            skip_count += 1
        elif success:
            success_count += 1
        else:
            fail_count += 1

    # Cleanup empty directories if requested (only for move, not copy)
    if cleanup_empty and not copy:
        _cleanup_source_dirs(source_dirs, dry_run=dry_run, output_json=output_json)

    if output_json:
        typer.echo(json.dumps(results, indent=2))
    elif len(expanded_files) > 1:
        _print_move_summary(success_count, skip_count, fail_count)
