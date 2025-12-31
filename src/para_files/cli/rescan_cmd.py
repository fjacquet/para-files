"""Rescan command for para-files CLI.

This module provides the 'rescan' command which re-classifies existing files
in PARA archives and moves them to their correct locations.

WARNING: This is a SLOW operation that processes files one by one.
For folder-level operations (adding retention prefixes), use 'migrate' instead.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from loguru import logger

from para_files.cli.app import app
from para_files.cli.shared import (
    load_config_or_exit,
    setup_logging,
)
from para_files.config import Config


if TYPE_CHECKING:
    from para_files.pipeline import ClassificationPipeline
    from para_files.types import ClassificationResult


def _discover_archive_files(
    base_path: Path,
    *,
    category_filter: str | None = None,
) -> Iterator[Path]:
    """Discover files in 3_Resources and 4_Archives as a generator.

    Yields files one at a time instead of loading all into memory.

    Args:
        base_path: PARA root directory.
        category_filter: Optional category name to filter (e.g., "fiscalite").

    Yields:
        File paths to potentially rescan.
    """
    for para_folder in ["3_Resources", "4_Archives"]:
        folder_path = base_path / para_folder
        if not folder_path.exists():
            continue

        if category_filter:
            # Filter by category patterns
            patterns = [
                f"{category_filter}*/**/*",
                f"*/{category_filter}*/**/*",
            ]
            for pattern in patterns:
                for f in folder_path.glob(pattern):
                    if f.is_file():
                        yield f
        else:
            # All files - use rglob as generator
            for f in folder_path.rglob("*"):
                if f.is_file():
                    yield f


def _needs_migration(current_path: Path, expected_path: Path) -> bool:
    """Check if a file needs to be moved."""
    return str(current_path.resolve()) != str(expected_path.resolve())


def _classify_for_rescan(
    file_path: Path,
    pipeline: ClassificationPipeline,
) -> ClassificationResult | None:
    """Classify a file to determine its expected destination.

    Uses full ClassificationPipeline (including RulesEngineClassifier)
    to get correct category based on all classification signals.

    Args:
        file_path: Path to file to classify.
        pipeline: Reusable pipeline instance.

    Returns:
        Classification result or None if classification failed.
    """
    try:
        return pipeline.classify_file(file_path)
    except (OSError, ValueError, KeyError) as e:
        logger.debug("Classification failed for %s: %s", file_path, e)
        return None


def _build_expected_path(
    file_path: Path,
    result: ClassificationResult,
    base_path: Path,
) -> Path | None:
    """Build the expected destination path from classification result."""
    if not result.category:
        return None
    return base_path / result.category / file_path.name


def _move_file(
    source: Path,
    destination: Path,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Move a single file."""
    result: dict[str, Any] = {
        "source": str(source),
        "destination": str(destination),
        "success": False,
        "action": "would_move" if dry_run else "moved",
    }

    if dry_run:
        result["success"] = True
        return result

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            result["action"] = "skipped"
            result["message"] = "Destination already exists"
            return result

        shutil.move(str(source), str(destination))
        result["success"] = True

    except OSError as e:
        result["action"] = "error"
        result["message"] = str(e)

    return result


def _cleanup_empty_dirs(base_path: Path, *, dry_run: bool = True) -> list[Path]:
    """Remove empty directories after rescan."""
    removed: list[Path] = []

    for para_folder in ["3_Resources", "4_Archives"]:
        folder_path = base_path / para_folder
        if not folder_path.exists():
            continue

        # Bottom-up traversal for empty dir removal
        for d in sorted(folder_path.rglob("*"), key=lambda p: -len(p.parts)):
            if d.is_dir() and not any(d.iterdir()):
                removed.append(d)
                if not dry_run:
                    d.rmdir()

    return removed


_MIN_PATH_DEPTH_FOR_CATEGORY = 2  # Minimum parts: PARA_folder/category/...
_MAX_ERRORS_TO_DISPLAY = 5


def _get_category_from_path(path: Path, base_path: Path) -> str:
    """Extract the category folder name from a destination path.

    Args:
        path: Full destination path.
        base_path: PARA root directory.

    Returns:
        Category folder name (e.g., "10y_fiscalite" or "identite").
    """
    try:
        relative = path.relative_to(base_path)
        parts = relative.parts
        # Category is typically the second part: 4_Archives/category/... or 3_Resources/category/...
        if len(parts) >= _MIN_PATH_DEPTH_FOR_CATEGORY:
            return parts[1]
    except ValueError:
        pass
    return "unknown"


def _format_relative_dest(dest_path: Path, base_path: Path) -> str:
    """Format destination path relative to base for display.

    Args:
        dest_path: Full destination path.
        base_path: PARA root directory.

    Returns:
        Shortened relative path for display.
    """
    try:
        relative = dest_path.relative_to(base_path)
        return str(relative.parent)
    except ValueError:
        return str(dest_path.parent)


def _process_file_rescan(
    file_path: Path,
    base_path: Path,
    pipeline: ClassificationPipeline,
    results: dict[str, Any],
    *,
    dry_run: bool,
    verbose: bool,
    output_json: bool,
) -> None:
    """Process rescan for a single file.

    Args:
        file_path: File to process.
        base_path: PARA root directory.
        pipeline: Reusable classification pipeline instance.
        results: Results dict to update.
        dry_run: If True, simulate without moving.
        verbose: If True, show per-file output.
        output_json: If True, suppress console output.
    """
    classification = _classify_for_rescan(file_path, pipeline)
    if not classification or not classification.category:
        return

    expected_path = _build_expected_path(file_path, classification, base_path)
    if not expected_path:
        return

    if not _needs_migration(file_path, expected_path):
        return

    results["files_need_move"] += 1

    # Track category for breakdown
    category = _get_category_from_path(expected_path, base_path)

    move_result = _move_file(file_path, expected_path, dry_run=dry_run)
    move_result["category"] = category
    results["moves"].append(move_result)

    if move_result["success"]:
        results["files_moved"] += 1
        # Track by category
        results["by_category"][category] = results["by_category"].get(category, 0) + 1
    elif move_result["action"] == "skipped":
        results["files_skipped"] += 1
    else:
        results["files_errored"] += 1
        results["errors"].append(move_result)

    # Always show moves (not just in verbose mode) - this is the key info users want
    if not output_json and move_result["success"]:
        action = "→" if not dry_run else "⟶ (dry-run)"
        rel_dest = _format_relative_dest(expected_path, base_path)
        typer.echo(f"  {file_path.name}")
        typer.echo(f"    {action} {rel_dest}/")
    elif verbose and not output_json and not move_result["success"]:
        typer.echo(f"  ✗ {file_path.name}: {move_result.get('message', 'failed')}")


def _print_summary(results: dict[str, Any], *, dry_run: bool) -> None:
    """Print rescan summary with category breakdown."""
    typer.echo("")
    typer.echo("=" * 60)
    typer.echo("Rescan Summary")
    typer.echo("=" * 60)
    typer.echo(f"  Files scanned:      {results['files_scanned']:,}")
    typer.echo(f"  Files need move:    {results['files_need_move']:,}")

    if dry_run:
        typer.echo(f"  Would move:         {results['files_moved']:,}")
        typer.echo(f"  Would skip:         {results['files_skipped']:,}")
    else:
        typer.echo(f"  Moved:              {results['files_moved']:,}")
        typer.echo(f"  Skipped:            {results['files_skipped']:,}")
        typer.echo(f"  Errors:             {results['files_errored']:,}")
        typer.echo(f"  Empty dirs removed: {results['empty_dirs_removed']:,}")

    # Category breakdown
    by_category = results.get("by_category", {})
    if by_category:
        typer.echo("")
        typer.echo("Moves by category:")
        # Sort by count descending
        for category, count in sorted(by_category.items(), key=lambda x: -x[1]):
            typer.echo(f"  {category:30} {count:,}")

    # Show errors if any
    if results.get("errors"):
        typer.echo("")
        typer.echo("Errors:")
        for err in results["errors"][:_MAX_ERRORS_TO_DISPLAY]:
            typer.echo(f"  ✗ {Path(err['source']).name}: {err.get('message', 'unknown')}")
        remaining = len(results["errors"]) - _MAX_ERRORS_TO_DISPLAY
        if remaining > 0:
            typer.echo(f"  ... and {remaining} more errors")

    if dry_run:
        typer.echo("")
        typer.echo("This was a dry run. Use --no-dry-run to execute.")


def _run_rescan(
    base_path: Path,
    config: Config,
    *,
    dry_run: bool,
    category: str | None,
    output_json: bool,
    verbose: bool,
    cleanup: bool,
) -> dict[str, Any]:
    """Execute the rescan process.

    Uses streaming approach - processes files as they're discovered
    instead of loading all into memory first.

    Args:
        base_path: PARA root directory.
        config: Application configuration.
        dry_run: If True, simulate without moving.
        category: Optional category filter.
        output_json: If True, suppress console output.
        verbose: If True, show detailed output.
        cleanup: If True, remove empty directories.

    Returns:
        Results dictionary.
    """
    from para_files.pipeline import ClassificationPipeline

    results: dict[str, Any] = {
        "base_path": str(base_path),
        "dry_run": dry_run,
        "category_filter": category,
        "files_scanned": 0,
        "files_need_move": 0,
        "files_moved": 0,
        "files_skipped": 0,
        "files_errored": 0,
        "empty_dirs_removed": 0,
        "moves": [],
        "errors": [],
        "by_category": {},  # Track moves per category for summary
    }

    if not output_json:
        action = "Preview" if dry_run else "Rescan"
        typer.echo(f"{action}ning files in {base_path}...")
        typer.echo("Processing files as discovered (streaming mode)...")
        if category:
            typer.echo(f"Category filter: {category}")

    # Create pipeline once and reuse - includes all classifiers in priority order:
    # ValidatedDBClassifier (100%), RulesEngineClassifier (95%), BookDetector (92%),
    # DomainKBClassifier (90%), SemanticClassifier (85%), MLXLLMClassifier (configurable)
    pipeline = ClassificationPipeline(config)

    # Stream-process files as they're discovered
    for file_path in _discover_archive_files(base_path, category_filter=category):
        results["files_scanned"] += 1

        # Show progress every 100 files
        if not output_json and results["files_scanned"] % 100 == 0:
            typer.echo(
                f"  Processed {results['files_scanned']} files ({results['files_moved']} moved)..."
            )

        _process_file_rescan(
            file_path,
            base_path,
            pipeline,
            results,
            dry_run=dry_run,
            verbose=verbose,
            output_json=output_json,
        )

    if cleanup and results["files_moved"] > 0:
        removed_dirs = _cleanup_empty_dirs(base_path, dry_run=dry_run)
        results["empty_dirs_removed"] = len(removed_dirs)

    return results


@app.command()
def rescan(
    base_path: Annotated[
        Path | None,
        typer.Argument(
            help="PARA root directory (defaults to config para_root)",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run/--no-dry-run", "-n", help="Preview changes without moving files"),
    ] = False,
    category: Annotated[
        str | None,
        typer.Option("--category", "-c", help="Rescan only a specific category"),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output results as JSON"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output"),
    ] = False,
    cleanup: Annotated[
        bool,
        typer.Option("--cleanup", help="Remove empty directories after rescan"),
    ] = True,
) -> None:
    """Re-classify files and move them to correct locations.

    SLOW: Processes each file individually with full classification.
    Use 'migrate' for fast folder-level operations.

    Scans existing files in 3_Resources/ and 4_Archives/, re-classifies
    each one, and moves files that are in the wrong location.

    \b
    Use cases:
        - Files classified before retention rules existed
        - Taxonomy changed and files need reclassification
        - Fix misclassified files

    \b
    Examples:
        # Rescan all files (uses config para_root)
        uv run para-files rescan

        # Preview without moving files
        uv run para-files rescan --dry-run

        # Rescan only fiscal documents
        uv run para-files rescan --category fiscalite

        # Override path
        uv run para-files rescan /custom/path
    """
    setup_logging(verbose=verbose)
    config = load_config_or_exit()

    effective_path = base_path if base_path else config.para_root

    results = _run_rescan(
        effective_path,
        config,
        dry_run=dry_run,
        category=category,
        output_json=output_json,
        verbose=verbose,
        cleanup=cleanup,
    )

    if output_json:
        typer.echo(json.dumps(results, indent=2))
    else:
        _print_summary(results, dry_run=dry_run)
