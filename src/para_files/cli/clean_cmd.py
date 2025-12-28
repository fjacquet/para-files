"""Clean command for para-files CLI.

This module provides the 'clean' command which removes junk files,
empty directories, and optionally NFO files from a location.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer

from para_files.cli.app import app
from para_files.cli.shared import (
    load_config_or_exit,
    setup_logging,
    validate_directory_or_exit,
)


if TYPE_CHECKING:
    from para_files.utils.cleanup_log import CleanupLogger

logger = logging.getLogger(__name__)


def _clean_junk_files(
    dir_path: Path,
    cleanup_logger: CleanupLogger,
    results: dict[str, Any],
    *,
    recursive: bool,
    dry_run: bool,
    output_json: bool,
) -> None:
    """Clean junk files from directory.

    Removes common system junk files like .DS_Store, Thumbs.db, etc.

    Args:
        dir_path: Directory to clean.
        cleanup_logger: Logger for audit trail.
        results: Dict to append deleted file paths to.
        recursive: If True, clean subdirectories.
        dry_run: If True, simulate without deleting.
        output_json: If True, suppress console output.
    """
    from para_files.utils.cleanup import cleanup_junk, scan_for_junk

    junk_files, junk_dirs = scan_for_junk(dir_path, recursive=recursive)

    if not junk_files and not junk_dirs:
        return

    deleted_files, deleted_dirs = cleanup_junk(dir_path, recursive=recursive, dry_run=dry_run)

    for f in deleted_files:
        cleanup_logger.log_deleted(f, "junk_file", f.name, dry_run=dry_run)
        results["deleted_files"].append(str(f))

    for d in deleted_dirs:
        cleanup_logger.log_deleted(d, "junk_dir", d.name, dry_run=dry_run)
        results["deleted_dirs"].append(str(d))

    if not output_json:
        action = "Would delete" if dry_run else "Deleted"
        if deleted_files:
            typer.echo(f"  {action} {len(deleted_files)} junk files")
        if deleted_dirs:
            typer.echo(f"  {action} {len(deleted_dirs)} junk directories")


def _clean_nfo_files(
    dir_path: Path,
    cleanup_logger: CleanupLogger,
    results: dict[str, Any],
    *,
    recursive: bool,
    dry_run: bool,
    output_json: bool,
) -> None:
    """Clean .nfo files from directory.

    Removes NFO metadata files, typically used after classification
    has extracted any useful hints from them.

    Args:
        dir_path: Directory to clean.
        cleanup_logger: Logger for audit trail.
        results: Dict to append deleted file paths to.
        recursive: If True, clean subdirectories.
        dry_run: If True, simulate without deleting.
        output_json: If True, suppress console output.
    """
    nfo_files = list(dir_path.rglob("*.nfo")) if recursive else list(dir_path.glob("*.nfo"))
    deleted_count = 0

    for nfo_file in nfo_files:
        if dry_run:
            logger.info("[DRY-RUN] Would delete NFO: %s", nfo_file)
            deleted_count += 1
        else:
            try:
                nfo_file.unlink()
                logger.info("Deleted NFO: %s", nfo_file)
                deleted_count += 1
            except OSError:
                logger.exception("Failed to delete NFO %s", nfo_file)
                continue

        cleanup_logger.log_deleted(nfo_file, "nfo", "NFO file cleanup", dry_run=dry_run)
        results["deleted_nfo"].append(str(nfo_file))

    if deleted_count and not output_json:
        action = "Would delete" if dry_run else "Deleted"
        typer.echo(f"  {action} {deleted_count} NFO files")


def _clean_empty_directories(
    dir_path: Path,
    cleanup_logger: CleanupLogger,
    results: dict[str, Any],
    *,
    dry_run: bool,
    output_json: bool,
) -> None:
    """Clean empty directories from path.

    Removes directories that contain no files (recursively checks
    for truly empty directories).

    Args:
        dir_path: Directory to check for empty subdirectories.
        cleanup_logger: Logger for audit trail.
        results: Dict to append deleted directory paths to.
        dry_run: If True, simulate without deleting.
        output_json: If True, suppress console output.
    """
    from para_files.utils.cleanup import cleanup_empty_dirs

    deleted_empty = cleanup_empty_dirs(dir_path, dry_run=dry_run)

    for d in deleted_empty:
        cleanup_logger.log_deleted(d, "empty_dir", "Empty directory", dry_run=dry_run)
        results["deleted_dirs"].append(str(d))

    if deleted_empty and not output_json:
        action = "Would delete" if dry_run else "Deleted"
        typer.echo(f"  {action} {len(deleted_empty)} empty directories")


@app.command()
def clean(
    directory: Annotated[Path, typer.Argument(help="Directory to clean")],
    recursive: Annotated[
        bool,
        typer.Option("--recursive", "-R", help="Clean subdirectories recursively"),
    ] = True,
    junk: Annotated[
        bool,
        typer.Option("--junk", help="Delete Apple/Windows temp files (.DS_Store, Thumbs.db, etc.)"),
    ] = True,
    nfo: Annotated[
        bool,
        typer.Option("--nfo", help="Delete .nfo files after using them as hints"),
    ] = False,
    empty_dirs: Annotated[
        bool,
        typer.Option("--empty-dirs", help="Delete empty directories"),
    ] = True,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview deletions without actually deleting"),
    ] = False,
    output_json: Annotated[
        bool, typer.Option("--json", "-j", help="Output results as JSON")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Clean junk files and empty directories from a location.

    By default, removes Apple/Windows temp files (.DS_Store, Thumbs.db,
    __MACOSX directories, etc.) and empty directories.

    Use --nfo to also remove .nfo files after classification has
    extracted hints from them.

    All deletions are logged to an audit file for traceability.
    """
    from para_files.utils.cleanup_log import CleanupLogger, get_default_log_path

    setup_logging(verbose=verbose)
    config = load_config_or_exit()

    dir_path = directory.resolve()
    validate_directory_or_exit(dir_path)

    # Setup audit log
    log_path = get_default_log_path(Path(config.para_root).expanduser())
    cleanup_logger = CleanupLogger(log_path if not dry_run else None)

    results: dict[str, Any] = {
        "directory": str(dir_path),
        "dry_run": dry_run,
        "deleted_files": [],
        "deleted_dirs": [],
        "deleted_nfo": [],
    }

    if not output_json:
        mode = "[DRY-RUN] " if dry_run else ""
        typer.echo(f"{mode}Cleaning {dir_path}")

    # Clean junk files
    if junk:
        _clean_junk_files(
            dir_path,
            cleanup_logger,
            results,
            recursive=recursive,
            dry_run=dry_run,
            output_json=output_json,
        )

    # Clean .nfo files
    if nfo:
        _clean_nfo_files(
            dir_path,
            cleanup_logger,
            results,
            recursive=recursive,
            dry_run=dry_run,
            output_json=output_json,
        )

    # Clean empty directories
    if empty_dirs:
        _clean_empty_directories(
            dir_path, cleanup_logger, results, dry_run=dry_run, output_json=output_json
        )

    # Write audit log
    if not dry_run:
        cleanup_logger.write_log()

    # Summary
    total_deleted = (
        len(results["deleted_files"]) + len(results["deleted_dirs"]) + len(results["deleted_nfo"])
    )

    if output_json:
        typer.echo(json.dumps(results, indent=2))
    elif total_deleted == 0:
        typer.echo("  Nothing to clean")
    else:
        action = "would be deleted" if dry_run else "deleted"
        typer.echo(f"\nTotal: {total_deleted} items {action}")
