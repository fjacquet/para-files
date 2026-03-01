"""Inbox command for para-files CLI. One-shot drain of the inbox directory."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from loguru import logger

from para_files.cli.app import app
from para_files.cli.shared import (
    ConflictChoice,
    discover_files,
    load_config_or_exit,
    setup_logging,
    validate_directory_or_exit,
)
from para_files.mover import ConflictStrategy, move_classified_file
from para_files.pipeline import ClassificationPipeline
from para_files.types import ClassificationSource


if TYPE_CHECKING:
    from para_files.mover import MoveResult
    from para_files.types import ClassificationResult


@dataclass
class _InboxStats:
    """Statistics for a single inbox processing run."""

    total: int = 0
    moved: int = 0
    stayed: int = 0
    failed: int = 0
    by_signal: dict[str, int] = field(default_factory=dict)


def _process_inbox_file(
    file_path: Path,
    pipeline: ClassificationPipeline,
    stats: _InboxStats,
    idx: int,
    total: int,
    *,
    dry_run: bool,
    conflict_strategy: ConflictStrategy,
    verbose: bool,
) -> None:
    """Process a single file from the inbox.

    Classifies the file and moves it if confidently classified. Files that
    fall back to ClassificationSource.DEFAULT are left in place.

    Args:
        file_path: Path to the file to process.
        pipeline: Configured classification pipeline.
        stats: Running statistics object (mutated in place).
        idx: 1-based index of this file in the current batch.
        total: Total number of files in the batch.
        dry_run: If True, simulate moves without changing the filesystem.
        conflict_strategy: How to handle destination conflicts.
        verbose: If True, print per-signal breakdown after each file.
    """
    try:
        result: ClassificationResult = pipeline.classify_file(file_path)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to classify {}", file_path)
        stats.failed += 1
        return

    source = result.confidence.source

    if source == ClassificationSource.DEFAULT:
        stats.stayed += 1
        typer.echo(f"[{idx}/{total}] INBOX: {file_path.name}")
        return

    target_dir = pipeline.get_target_path(result)
    move_result: MoveResult = move_classified_file(
        file_path,
        target_dir,
        dry_run=dry_run,
        copy_mode=False,
        conflict_strategy=conflict_strategy,
        add_date_prefix=False,
        smart_rename=False,
        classification=result,
    )

    if move_result.success:
        stats.moved += 1
        signal_key = source.value
        stats.by_signal[signal_key] = stats.by_signal.get(signal_key, 0) + 1
        typer.echo(f"[{idx}/{total}] {file_path.name}")
        typer.echo(f"    -> {move_result.destination}")
        if verbose and result.signals:
            for s in result.signals:
                marker = "[matched]" if s.matched else "[      ]"
                typer.echo(f"    {marker} {s.name}: {s.score:.0%}")
    else:
        stats.failed += 1
        typer.echo(
            f"[{idx}/{total}] ERROR: {file_path.name} - {move_result.message}",
            err=True,
        )


def _print_inbox_summary(stats: _InboxStats, *, dry_run: bool) -> None:
    """Print a summary of the inbox processing run.

    Args:
        stats: Completed statistics for the run.
        dry_run: If True, prefix the summary with "(dry run)".
    """
    typer.echo("")
    prefix = "(dry run) " if dry_run else ""
    typer.echo(f"{prefix}--- Inbox Summary ---")
    typer.echo(f"Total processed : {stats.total}")
    typer.echo(f"Moved           : {stats.moved}")
    typer.echo(f"Stayed in Inbox : {stats.stayed}")
    if stats.failed > 0:
        typer.echo(f"Errors          : {stats.failed}")
    if stats.by_signal:
        typer.echo("")
        typer.echo("By signal source:")
        for sig_source, count in sorted(stats.by_signal.items(), key=lambda kv: -kv[1]):
            typer.echo(f"  {sig_source}: {count}")


@app.command()
def inbox(
    directory: Annotated[
        Path | None,
        typer.Argument(help="Inbox directory to process (default: configured para_root/0_Inbox)"),
    ] = None,
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run/--no-dry-run", "-n", help="Preview without moving files"),
    ] = False,
    conflict: Annotated[
        ConflictChoice,
        typer.Option(help="Strategy for handling existing files"),
    ] = ConflictChoice.rename,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show per-classifier signal breakdown"),
    ] = False,
) -> None:
    """Process all files in the inbox directory.

    Classify and move confidently-matched files in one shot. Files that cannot
    be classified (ClassificationSource.DEFAULT) are left in place and reported
    as INBOX in the per-file output.
    """
    setup_logging(verbose=verbose)
    config = load_config_or_exit()

    if reference_tree:
        config.reference_tree_path = reference_tree

    dir_path = (directory or config.inbox_path).resolve()
    validate_directory_or_exit(dir_path)

    files = discover_files(dir_path, recursive=False, ext_filter=None)

    if not files:
        typer.echo("No files found in inbox")
        return

    typer.echo(f"Processing {len(files)} file(s) from {dir_path}")
    typer.echo("")

    pipeline = ClassificationPipeline(config)
    conflict_strategy = ConflictStrategy(conflict.value)
    stats = _InboxStats(total=len(files))

    for idx, f in enumerate(files, 1):
        _process_inbox_file(
            f,
            pipeline,
            stats,
            idx,
            len(files),
            dry_run=dry_run,
            conflict_strategy=conflict_strategy,
            verbose=verbose,
        )

    _print_inbox_summary(stats, dry_run=dry_run)


__all__ = ["_InboxStats", "_print_inbox_summary", "_process_inbox_file", "inbox"]
