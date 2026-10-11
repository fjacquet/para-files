"""`para-files undo [RUN_ID]`: reverse a run from its journal."""

from __future__ import annotations

from typing import Annotated

import typer

from para_files.cli.app import app
from para_files.cli.common import EXIT_FAILURE, fail, settings_or_exit
from para_files.core.undo import UndoError, undo_run


@app.command("undo")
def undo_command(
    run_id: Annotated[
        str | None, typer.Argument(help="The run to undo (default: the last one).")
    ] = None,
) -> None:
    """Put back what a run moved, trashed or removed, checking every step."""
    settings = settings_or_exit()
    try:
        report = undo_run(settings.state_dir, run_id)
    except UndoError as exc:
        fail(str(exc), EXIT_FAILURE)
    typer.echo(
        f"undid run {report.run_id}: {len(report.restored)} restored, "
        f"{len(report.recreated)} folders recreated, {len(report.removed_dirs)} folders removed"
    )
    for path, reason in report.skipped:
        typer.echo(f"  left alone {path}: {reason}")
    for folder in report.kept_dirs:
        typer.echo(f"  kept       {folder}: folder not empty")
