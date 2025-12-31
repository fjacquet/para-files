"""Dedupe command for removing duplicate files with _N suffix.

This module provides the dedupe command that scans for files with a numeric
suffix pattern (e.g., document_1.pdf, file_2.txt) and removes them if they
are identical to their original counterpart.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Any

import typer

from para_files.cli.app import app
from para_files.cli.shared import setup_logging
from para_files.mover import files_are_identical
from para_files.utils.validation import validate_directory_exists


# Pattern to match files with _N suffix (e.g., "document_1.pdf", "file_2.txt")
# Groups: (1) base name, (2) number, (3) extension including dot
_DUPLICATE_SUFFIX_PATTERN = re.compile(r"^(.+)_(\d+)(\.[^.]+)$")


def _find_suffixed_duplicates(
    directory: Path,
    *,
    recursive: bool = True,
) -> list[tuple[Path, Path]]:
    """Find files with _N suffix that have a matching original file.

    Scans the directory for files matching the pattern name_N.ext where N is
    a number, and checks if the corresponding original file (name.ext) exists.

    Args:
        directory: Directory to scan.
        recursive: Whether to scan subdirectories.

    Returns:
        List of (suffixed_file, original_file) tuples where both files exist.
    """
    duplicates: list[tuple[Path, Path]] = []
    files = list(directory.rglob("*") if recursive else directory.glob("*"))

    for file_path in files:
        if not file_path.is_file():
            continue

        match = _DUPLICATE_SUFFIX_PATTERN.match(file_path.name)
        if match:
            base_name = match.group(1)
            extension = match.group(3)
            original_name = f"{base_name}{extension}"
            original_path = file_path.parent / original_name

            if original_path.exists() and original_path.is_file():
                duplicates.append((file_path, original_path))

    return duplicates


def _handle_identical_duplicate(
    suffixed_file: Path,
    original_file: Path,
    results: dict[str, Any],
    *,
    dry_run: bool,
    output_json: bool,
    verbose: bool,
) -> str:
    """Handle deletion of identical duplicate file.

    When the suffixed file is identical to the original (same SHA256 hash),
    this function deletes the suffixed copy (or simulates deletion in dry-run mode).

    Args:
        suffixed_file: The duplicate file with _N suffix to potentially delete.
        original_file: The original file without suffix.
        results: Dictionary to accumulate results for JSON output.
        dry_run: If True, simulate deletion without actually removing files.
        output_json: If True, append to results dict instead of printing.
        verbose: If True, print additional details.

    Returns:
        Status string "deleted" to indicate the file was (or would be) deleted.
    """
    action = "would delete" if dry_run else "deleted"

    if not dry_run:
        suffixed_file.unlink()

    if output_json:
        results["deleted"].append(
            {
                "file": str(suffixed_file),
                "original": str(original_file),
                "action": action,
            }
        )
    else:
        verb = "Would delete" if dry_run else "Deleted"
        typer.echo(f"  {verb}: {suffixed_file.name}")
        if verbose:
            typer.echo(f"    (identical to {original_file.name})")

    return "deleted"


def _handle_different_files(
    suffixed_file: Path,
    original_file: Path,
    results: dict[str, Any],
    *,
    output_json: bool,
    verbose: bool,
) -> str:
    """Handle case where files have different content.

    When the suffixed file differs from the original, we keep both files
    and report the situation to the user.

    Args:
        suffixed_file: The file with _N suffix.
        original_file: The original file without suffix.
        results: Dictionary to accumulate results for JSON output.
        output_json: If True, append to results dict instead of printing.
        verbose: If True, print the kept file information.

    Returns:
        Status string "different" to indicate files were kept.
    """
    if output_json:
        results["different"].append(
            {
                "file": str(suffixed_file),
                "original": str(original_file),
                "action": "kept (different content)",
            }
        )
    elif verbose:
        typer.echo(f"  Kept: {suffixed_file.name} (different from original)")

    return "different"


def _process_duplicate_pair(
    suffixed_file: Path,
    original_file: Path,
    results: dict[str, Any],
    *,
    dry_run: bool,
    output_json: bool,
    verbose: bool,
) -> str:
    """Process a single duplicate pair and return status.

    Compares the suffixed file with its original counterpart and either
    deletes the duplicate (if identical) or keeps it (if different).

    Args:
        suffixed_file: The file with _N suffix to process.
        original_file: The original file without suffix.
        results: Dictionary to accumulate results for JSON output.
        dry_run: If True, simulate deletion without actually removing files.
        output_json: If True, append to results dict instead of printing.
        verbose: If True, print additional details.

    Returns:
        Status string: "deleted", "different", or "error".
    """
    try:
        if files_are_identical(suffixed_file, original_file):
            return _handle_identical_duplicate(
                suffixed_file,
                original_file,
                results,
                dry_run=dry_run,
                output_json=output_json,
                verbose=verbose,
            )
        return _handle_different_files(
            suffixed_file,
            original_file,
            results,
            output_json=output_json,
            verbose=verbose,
        )
    except OSError as e:
        if output_json:
            results["kept"].append({"file": str(suffixed_file), "error": str(e)})
        else:
            typer.echo(f"  Error processing {suffixed_file.name}: {e}", err=True)
        return "error"


@app.command()
def dedupe(
    directory: Annotated[Path, typer.Argument(help="Directory to scan for duplicates")],
    recursive: Annotated[
        bool,
        typer.Option("--recursive", "-R", help="Scan subdirectories recursively"),
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
    """Remove duplicate files with _N suffix (e.g., file_1.pdf, file_2.pdf).

    Scans for files that have a _N suffix (like document_1.pdf) and checks
    if an original file exists (document.pdf). If both files are identical
    (same SHA256 hash), the suffixed duplicate is deleted.

    This is useful for cleaning up after file moves that created duplicates.
    """
    setup_logging(verbose=verbose)

    dir_path = directory.resolve()
    if not validate_directory_exists(dir_path, exit_on_error=True):
        return  # validate_directory_exists already called raise SystemExit

    if not output_json:
        mode = "[DRY-RUN] " if dry_run else ""
        typer.echo(f"{mode}Scanning for duplicates in {dir_path}")

    candidates = _find_suffixed_duplicates(dir_path, recursive=recursive)

    if not output_json and verbose:
        typer.echo(f"Found {len(candidates)} candidate files with _N suffix")

    results: dict[str, Any] = {
        "directory": str(dir_path),
        "dry_run": dry_run,
        "deleted": [],
        "kept": [],
        "different": [],
    }

    counts = {"deleted": 0, "different": 0, "error": 0}

    for suffixed_file, original_file in candidates:
        status = _process_duplicate_pair(
            suffixed_file,
            original_file,
            results,
            dry_run=dry_run,
            output_json=output_json,
            verbose=verbose,
        )
        counts[status] += 1

    if output_json:
        typer.echo(json.dumps(results, indent=2))
    else:
        action = "Would delete" if dry_run else "Deleted"
        typer.echo(f"\n{action}: {counts['deleted']} duplicate(s)")
        if counts["different"] > 0:
            typer.echo(f"Kept (different content): {counts['different']}")
        if counts["error"] > 0:
            typer.echo(f"Errors: {counts['error']}")
