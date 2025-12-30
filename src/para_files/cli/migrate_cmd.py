"""Migrate command for para-files CLI.

This module provides the 'migrate' command which reorganizes existing files
to use retention-based folder suffixes in their paths.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer

from para_files.cli.app import app
from para_files.cli.shared import (
    load_config_or_exit,
    setup_logging,
)


if TYPE_CHECKING:
    from para_files.types import ClassificationResult

logger = logging.getLogger(__name__)


def _discover_archive_files(
    base_path: Path,
    *,
    category_filter: str | None = None,
) -> list[Path]:
    """Discover all files in 3_Resources and 4_Archives.

    Args:
        base_path: PARA root directory.
        category_filter: Optional category name to filter (e.g., "fiscalite").

    Returns:
        List of file paths to potentially migrate.
    """
    files: list[Path] = []

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
                matching = [f for f in folder_path.glob(pattern) if f.is_file()]
                files.extend(matching)
        else:
            # All files
            matching = [f for f in folder_path.rglob("*") if f.is_file()]
            files.extend(matching)

    return files


def _needs_migration(current_path: Path, expected_path: Path) -> bool:
    """Check if a file needs to be migrated."""
    return str(current_path.resolve()) != str(expected_path.resolve())


def _classify_for_migration(
    file_path: Path,
) -> ClassificationResult | None:
    """Classify a file to determine its expected destination.

    Uses TaxonomyClassifier with documents.json to get retention-aware path.
    """
    from para_files.classifiers.taxonomy_classifier import TaxonomyClassifier
    from para_files.utils.file_utils import extract_file_metadata, read_content_preview

    try:
        classifier = TaxonomyClassifier()
        metadata = extract_file_metadata(file_path, extract_exif=False)
        content = read_content_preview(file_path, max_chars=2000)

        return classifier.classify(
            content=content,
            metadata=metadata,
        )

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


def _migrate_file(
    source: Path,
    destination: Path,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Migrate a single file."""
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
    """Remove empty directories after migration."""
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


def _process_file_migration(
    file_path: Path,
    base_path: Path,
    results: dict[str, Any],
    *,
    dry_run: bool,
    verbose: bool,
    output_json: bool,
) -> None:
    """Process migration for a single file.

    Args:
        file_path: File to process.
        base_path: PARA root directory.
        results: Results dict to update.
        dry_run: If True, simulate without moving.
        verbose: If True, show per-file output.
        output_json: If True, suppress console output.
    """
    classification = _classify_for_migration(file_path)
    if not classification or not classification.category:
        return

    expected_path = _build_expected_path(file_path, classification, base_path)
    if not expected_path:
        return

    if not _needs_migration(file_path, expected_path):
        return

    results["files_need_migration"] += 1

    migration_result = _migrate_file(file_path, expected_path, dry_run=dry_run)
    results["migrations"].append(migration_result)

    if migration_result["success"]:
        results["files_migrated"] += 1
    elif migration_result["action"] == "skipped":
        results["files_skipped"] += 1
    else:
        results["files_errored"] += 1
        results["errors"].append(migration_result)

    if verbose and not output_json:
        status = "+" if migration_result["success"] else "x"
        typer.echo(f"  {status} {file_path.name} -> {expected_path.parent.name}/")


def _print_summary(results: dict[str, Any], *, dry_run: bool) -> None:
    """Print migration summary."""
    typer.echo("")
    typer.echo("=" * 50)
    typer.echo("Migration Summary:")
    typer.echo(f"  Files scanned:        {results['files_scanned']}")
    typer.echo(f"  Files need migration: {results['files_need_migration']}")

    if dry_run:
        typer.echo(f"  Would migrate:        {results['files_migrated']}")
        typer.echo(f"  Would skip:           {results['files_skipped']}")
        typer.echo("")
        typer.echo("This was a dry run. Use --no-dry-run to execute.")
    else:
        typer.echo(f"  Migrated:             {results['files_migrated']}")
        typer.echo(f"  Skipped:              {results['files_skipped']}")
        typer.echo(f"  Errors:               {results['files_errored']}")
        typer.echo(f"  Empty dirs removed:   {results['empty_dirs_removed']}")


def _run_migration(
    base_path: Path,
    *,
    dry_run: bool,
    category: str | None,
    output_json: bool,
    verbose: bool,
    cleanup: bool,
) -> dict[str, Any]:
    """Execute the migration process.

    Args:
        base_path: PARA root directory.
        dry_run: If True, simulate without moving.
        category: Optional category filter.
        output_json: If True, suppress console output.
        verbose: If True, show detailed output.
        cleanup: If True, remove empty directories.

    Returns:
        Results dictionary.
    """
    results: dict[str, Any] = {
        "base_path": str(base_path),
        "dry_run": dry_run,
        "category_filter": category,
        "files_scanned": 0,
        "files_need_migration": 0,
        "files_migrated": 0,
        "files_skipped": 0,
        "files_errored": 0,
        "empty_dirs_removed": 0,
        "migrations": [],
        "errors": [],
    }

    if not output_json:
        action = "Preview" if dry_run else "Migrate"
        typer.echo(f"{action}ing files in {base_path}...")
        if category:
            typer.echo(f"Category filter: {category}")

    files = _discover_archive_files(base_path, category_filter=category)
    results["files_scanned"] = len(files)

    if not output_json:
        typer.echo(f"Found {len(files)} files to analyze")

    for file_path in files:
        _process_file_migration(
            file_path,
            base_path,
            results,
            dry_run=dry_run,
            verbose=verbose,
            output_json=output_json,
        )

    if cleanup and results["files_migrated"] > 0:
        removed_dirs = _cleanup_empty_dirs(base_path, dry_run=dry_run)
        results["empty_dirs_removed"] = len(removed_dirs)

    return results


@app.command()
def migrate(
    base_path: Annotated[
        Path | None,
        typer.Argument(
            help="PARA root directory to migrate",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview changes without moving files"),
    ] = True,
    category: Annotated[
        str | None,
        typer.Option("--category", "-c", help="Migrate only a specific category"),
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
        typer.Option("--cleanup", help="Remove empty directories after migration"),
    ] = True,
) -> None:
    """Migrate files to retention-aware folder structure.

    Reorganizes existing files in 3_Resources/ and 4_Archives/ to use
    retention-based folder suffixes (e.g., fiscalite_10y, sante_perm).

    \b
    Examples:
        # Preview all migrations (default)
        uv run para-files migrate /path/to/PARA

        # Execute migration
        uv run para-files migrate /path/to/PARA --no-dry-run

        # Migrate only fiscal documents
        uv run para-files migrate --category fiscalite

        # JSON output for scripting
        uv run para-files migrate --json
    """
    setup_logging(verbose=verbose)
    load_config_or_exit()  # Ensure config is loaded for TaxonomyLoader

    # Use current directory if not specified
    effective_path = base_path if base_path else Path.cwd()

    results = _run_migration(
        effective_path,
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
