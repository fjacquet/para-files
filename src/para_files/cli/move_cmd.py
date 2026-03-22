"""Move command for para-files CLI.

This module provides the 'move' command which classifies files and moves
(or copies) them to their appropriate PARA destinations.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    signal_marker,
    signal_to_dict,
)
from para_files.mover import (
    ConflictStrategy,
    move_classified_file,
    validate_destination_permissions,
)
from para_files.pipeline import ClassificationPipeline
from para_files.utils.validation import validate_file_exists


if TYPE_CHECKING:
    from para_files.mover import MoveResult
    from para_files.types import ClassificationResult


# Skip thread pool for small batches — overhead exceeds benefit below this count
SINGLE_THREAD_THRESHOLD = 5


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
    if result.signals:
        output["signals"] = [signal_to_dict(s) for s in result.signals]
    if result.route_name:
        output["route_name"] = result.route_name
    return output


def _process_single_move(
    file_path: Path,
    pipeline: ClassificationPipeline,
    classification: ClassificationResult,
    *,
    dry_run: bool,
    copy: bool,
    conflict_strategy: ConflictStrategy,
    date_prefix: bool,
    smart_rename: bool,
) -> tuple[Any, Any, bool]:
    """Process a single file move.

    Uses the provided classification and performs the move/copy operation.

    Args:
        file_path: Path to the file to move.
        pipeline: The classification pipeline.
        classification: Pre-computed classification result (avoids double-classify).
        dry_run: If True, simulate the move without actually moving.
        copy: If True, copy instead of move.
        conflict_strategy: Strategy for handling existing files.
        date_prefix: If True, add date prefix to filename.
        smart_rename: If True, use intelligent naming from metadata.

    Returns:
        Tuple of (classification result, move result, success boolean).
    """
    result = classification
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
    *,
    verbose: bool = False,
) -> None:
    """Print move result to console.

    Displays the result of a file move operation.

    Args:
        file_path: Path to the source file.
        result: The classification result.
        move_result: The result of the move operation.
        action_verb: Verb to use in output ("Moved", "Copied", etc.)
        verbose: If True, show per-classifier signal breakdown.
    """
    if move_result.success:
        typer.echo(f"{action_verb}: {file_path.name}")
        typer.echo(f"  -> {move_result.destination}")
        conf = result.confidence
        typer.echo(f"  Classification: {result.category} ({conf.value:.0%})")
        if verbose and result.signals:
            for s in result.signals:
                typer.echo(f"    {signal_marker(s)} {s.name}: {s.score:.0%}")
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
    verbose: bool = False,
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
        verbose: If True, show per-classifier signal breakdown.

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
            logger.info("Skipping unclassifiable file: {}", file_path)
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
            classification,
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
            _print_move_result(file_path, result, move_result, action_verb, verbose=verbose)

    except Exception:  # noqa: BLE001
        logger.exception("Failed to process {}", file_path)
        if output_json:
            results.append({"source_file": str(file_path), "error": "processing failed"})
        return False, False
    else:
        return success, False


def _move_files_sequential(
    expanded_files: list[Path],
    pipeline: ClassificationPipeline,
    source_dirs: set[Path],
    *,
    dry_run: bool,
    copy: bool,
    conflict_strategy: ConflictStrategy,
    date_prefix: bool,
    smart_rename: bool,
    skip_unclassifiable: bool,
    enable_rollback: bool,
    output_json: bool,
    action_verb: str,
    verbose: bool = False,
) -> tuple[list[dict[str, Any]], int, int, int]:
    """Move files sequentially with optional permission pre-check.

    Returns:
        Tuple of (json_results, success_count, skip_count, fail_count).
    """
    results: list[dict[str, Any]] = []
    success_count = 0
    fail_count = 0
    skip_count = 0

    # Pre-flight: validate destination write permissions before moving any file
    if not dry_run and enable_rollback and not _check_destination_permissions(
        expanded_files, pipeline
    ):
        raise typer.Exit(code=1)

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
            verbose=verbose,
        )
        if skipped:
            skip_count += 1
        elif success:
            success_count += 1
        else:
            fail_count += 1

    return results, success_count, skip_count, fail_count


def _check_destination_permissions(
    expanded_files: list[Path],
    pipeline: ClassificationPipeline,
) -> bool:
    """Pre-flight permission check for all destination directories.

    Classifies all files to determine their destination directories, then checks
    that each destination is writable. Prints an error and returns False if any
    destination is unwritable.

    Args:
        expanded_files: List of source file paths to classify.
        pipeline: The classification pipeline to determine destinations.

    Returns:
        True if all destinations are writable, False otherwise.
    """
    dest_dirs: set[Path] = set()
    for resolved in expanded_files:
        try:
            classification = pipeline.classify_file(resolved)
            dest_dirs.add(pipeline.get_target_path(classification))
        except Exception:  # noqa: BLE001
            logger.warning("Failed to classify {} during permission pre-check", resolved)

    unwritable = validate_destination_permissions(dest_dirs)
    if unwritable:
        msg = "Permission denied for destination(s):\n" + "\n".join(
            f"  - {p}" for p in unwritable
        )
        typer.echo(f"Error: {msg}", err=True)
        return False
    return True


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


def _move_single_file(
    file_path: Path,
    pipeline: ClassificationPipeline,
    *,
    dry_run: bool,
    copy: bool,
    conflict_strategy: ConflictStrategy,
    date_prefix: bool,
    smart_rename: bool,
    skip_unclassifiable: bool,
) -> dict[str, Any]:
    """Classify and move a single file (for ThreadPoolExecutor).

    Self-contained worker that handles its own errors.

    Returns:
        Dict with keys: success, skipped, error, source_dir, and optionally
        json_result for JSON output mode.
    """
    from para_files.types import ClassificationSource

    if not validate_file_exists(file_path):
        return {
            "success": False,
            "skipped": False,
            "error": "file validation failed",
            "source_file": str(file_path),
        }

    try:
        classification = pipeline.classify_file(file_path)

        # Skip unclassifiable files if requested
        if skip_unclassifiable and classification.confidence.source == ClassificationSource.DEFAULT:
            logger.info("Skipping unclassifiable file: {}", file_path)
            return {
                "success": True,
                "skipped": True,
                "source_file": str(file_path),
                "reason": "unclassifiable",
            }

        result, move_result, success = _process_single_move(
            file_path,
            pipeline,
            classification,
            dry_run=dry_run,
            copy=copy,
            conflict_strategy=conflict_strategy,
            date_prefix=date_prefix,
            smart_rename=smart_rename,
        )
        target_dir = pipeline.get_target_path(result)
        return {
            "success": success,
            "skipped": False,
            "source_dir": str(file_path.parent),
            "source_file": str(file_path),
            "result": result,
            "move_result": move_result,
            "target_dir": target_dir,
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to process {}", file_path)
        return {"success": False, "skipped": False, "error": str(e), "source_file": str(file_path)}


def _move_files_parallel(
    expanded_files: list[Path],
    pipeline: ClassificationPipeline,
    max_workers: int,
    *,
    dry_run: bool,
    copy: bool,
    conflict_strategy: ConflictStrategy,
    date_prefix: bool,
    smart_rename: bool,
    skip_unclassifiable: bool,
    output_json: bool,
    action_verb: str,
    verbose: bool = False,
) -> tuple[list[dict[str, Any]], set[Path], int, int, int]:
    """Move files in parallel using ThreadPoolExecutor.

    Returns:
        Tuple of (json_results, source_dirs, success_count, skip_count, fail_count).
    """
    results: list[dict[str, Any]] = []
    source_dirs: set[Path] = set()
    success_count = 0
    skip_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _move_single_file,
                f,
                pipeline,
                dry_run=dry_run,
                copy=copy,
                conflict_strategy=conflict_strategy,
                date_prefix=date_prefix,
                smart_rename=smart_rename,
                skip_unclassifiable=skip_unclassifiable,
            ): f
            for f in expanded_files
        }
        for future in as_completed(futures):
            file_path = futures[future]
            source_dirs.add(file_path.parent)
            rd = future.result()

            if rd.get("skipped"):
                skip_count += 1
                if output_json:
                    results.append(
                        {
                            "source_file": rd["source_file"],
                            "skipped": True,
                            "reason": rd.get("reason", "unclassifiable"),
                        }
                    )
                else:
                    typer.echo(f"  Skipped (unclassifiable): {file_path.name}")
            elif rd.get("error"):
                fail_count += 1
                if output_json:
                    results.append({"source_file": rd["source_file"], "error": rd["error"]})
                else:
                    typer.echo(f"Failed: {file_path.name} - {rd['error']}", err=True)
            else:
                # Both success and move-failure have result/move_result
                if rd["success"]:
                    success_count += 1
                else:
                    fail_count += 1
                if output_json:
                    results.append(
                        _format_move_result_json(
                            file_path, rd["result"], rd["target_dir"], rd["move_result"]
                        )
                    )
                else:
                    _print_move_result(
                        file_path, rd["result"], rd["move_result"], action_verb, verbose=verbose
                    )

    return results, source_dirs, success_count, skip_count, fail_count


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
    enable_rollback: Annotated[
        bool,
        typer.Option("--rollback/--no-rollback", help="Enable rollback on batch failure"),
    ] = True,
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
    max_workers = config.max_workers
    action_verb = (
        ("Would copy" if copy else "Would move") if dry_run else ("Copied" if copy else "Moved")
    )

    # Use parallel or sequential processing based on max_workers
    if max_workers > 1 and len(expanded_files) < SINGLE_THREAD_THRESHOLD:
        if verbose:
            typer.echo(
                f"Processing {len(expanded_files)} file(s) in single-threaded mode "
                f"(< {SINGLE_THREAD_THRESHOLD} files)"
            )
        max_workers = 1
    if max_workers > 1 and len(expanded_files) >= SINGLE_THREAD_THRESHOLD:
        results, par_source_dirs, success_count, skip_count, fail_count = _move_files_parallel(
            expanded_files,
            pipeline,
            max_workers,
            dry_run=dry_run,
            copy=copy,
            conflict_strategy=conflict_strategy,
            date_prefix=date_prefix,
            smart_rename=smart_rename,
            skip_unclassifiable=skip_unclassifiable,
            output_json=output_json,
            action_verb=action_verb,
            verbose=verbose,
        )
        source_dirs.update(par_source_dirs)
    else:
        results, success_count, skip_count, fail_count = _move_files_sequential(
            expanded_files,
            pipeline,
            source_dirs,
            dry_run=dry_run,
            copy=copy,
            conflict_strategy=conflict_strategy,
            date_prefix=date_prefix,
            smart_rename=smart_rename,
            skip_unclassifiable=skip_unclassifiable,
            enable_rollback=enable_rollback,
            output_json=output_json,
            action_verb=action_verb,
            verbose=verbose,
        )

    # Cleanup empty directories if requested (only for move, not copy)
    if cleanup_empty and not copy:
        _cleanup_source_dirs(source_dirs, dry_run=dry_run, output_json=output_json)

    if output_json:
        typer.echo(json.dumps(results, indent=2))
    elif len(expanded_files) > 1:
        _print_move_summary(success_count, skip_count, fail_count)
