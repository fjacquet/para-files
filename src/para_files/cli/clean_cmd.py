"""Clean command for para-files CLI.

This module provides the 'clean' command which removes junk files,
empty directories, and optionally NFO files from a location.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from loguru import logger

from para_files.cli.app import app
from para_files.cli.shared import (
    load_config_or_exit,
    setup_logging,
    validate_directory_or_exit,
)


def _clean_junk_files(
    dir_path: Path,
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
        action = "would_delete" if dry_run else "deleted"
        logger.info("[{}] junk_file: {} ({})", action.upper(), f, f.name)
        results["deleted_files"].append(str(f))

    for d in deleted_dirs:
        action = "would_delete" if dry_run else "deleted"
        logger.info("[{}] junk_dir: {} ({})", action.upper(), d, d.name)
        results["deleted_dirs"].append(str(d))

    if not output_json:
        action = "Would delete" if dry_run else "Deleted"
        if deleted_files:
            typer.echo(f"  {action} {len(deleted_files)} junk files")
        if deleted_dirs:
            typer.echo(f"  {action} {len(deleted_dirs)} junk directories")


def _clean_nfo_files(
    dir_path: Path,
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
        results: Dict to append deleted file paths to.
        recursive: If True, clean subdirectories.
        dry_run: If True, simulate without deleting.
        output_json: If True, suppress console output.
    """
    nfo_files = list(dir_path.rglob("*.nfo")) if recursive else list(dir_path.glob("*.nfo"))
    deleted_count = 0

    for nfo_file in nfo_files:
        if dry_run:
            logger.info("[WOULD_DELETE] nfo: {} (NFO file cleanup)", nfo_file)
            deleted_count += 1
            results["deleted_nfo"].append(str(nfo_file))
        else:
            try:
                nfo_file.unlink()
                logger.info("[DELETED] nfo: {} (NFO file cleanup)", nfo_file)
                deleted_count += 1
                results["deleted_nfo"].append(str(nfo_file))
            except OSError:
                logger.exception("Failed to delete NFO {}", nfo_file)

    if deleted_count and not output_json:
        action = "Would delete" if dry_run else "Deleted"
        typer.echo(f"  {action} {deleted_count} NFO files")


def _clean_empty_directories(
    dir_path: Path,
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
        results: Dict to append deleted directory paths to.
        dry_run: If True, simulate without deleting.
        output_json: If True, suppress console output.
    """
    from para_files.utils.cleanup import cleanup_empty_dirs

    deleted_empty = cleanup_empty_dirs(dir_path, dry_run=dry_run)

    for d in deleted_empty:
        action = "would_delete" if dry_run else "deleted"
        logger.info("[{}] empty_dir: {} (Empty directory)", action.upper(), d)
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
        typer.Option("--dry-run/--no-dry-run", "-n", help="Preview without deleting"),
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

    All deletions are logged via loguru (console + file if configured).
    """
    config = load_config_or_exit()

    # Setup logging with file output (unless dry-run)
    para_root = Path(config.para_root).expanduser() if not dry_run else None
    setup_logging(verbose=verbose, para_root=para_root, config=config.logging)

    dir_path = directory.resolve()
    validate_directory_or_exit(dir_path)

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
            results,
            recursive=recursive,
            dry_run=dry_run,
            output_json=output_json,
        )

    # Clean .nfo files
    if nfo:
        _clean_nfo_files(
            dir_path,
            results,
            recursive=recursive,
            dry_run=dry_run,
            output_json=output_json,
        )

    # Clean empty directories
    if empty_dirs:
        _clean_empty_directories(dir_path, results, dry_run=dry_run, output_json=output_json)

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
