"""`para-files clean [PATH] [--duplicates] [--apply]`: clutter and duplicates to .trash."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from para_files.cli.app import app
from para_files.cli.common import config_or_exit, fail, relative, settings_or_exit
from para_files.core.clean import CleanPlan, apply_clean, kept_folders, plan_clean
from para_files.core.journal import Journal, new_run_id


def _print_plan(plan: CleanPlan, root: Path) -> None:
    typer.echo(f"junk files ({len(plan.junk)}):")
    for path in plan.junk:
        typer.echo(f"  {relative(path, root)}")
    if plan.duplicates:
        typer.echo(f"duplicates ({len(plan.duplicates)}), the first copy is kept:")
        for copy, kept in plan.duplicates:
            typer.echo(f"  {relative(copy, root)}  (same as {relative(kept, root)})")
    typer.echo(f"empty folders ({len(plan.empty_dirs)}):")
    for path in plan.empty_dirs:
        typer.echo(f"  {relative(path, root)}")


@app.command("clean")
def clean_command(
    path: Annotated[
        Path | None, typer.Argument(help="Folder to clean, inside the PARA root (default: all).")
    ] = None,
    duplicates: Annotated[
        bool, typer.Option("--duplicates", help="Also trash identical copies of a file.")
    ] = False,
    apply_: Annotated[bool, typer.Option("--apply", help="Do it (journaled, undoable).")] = False,
) -> None:
    """Junk files, empty folders and (optionally) duplicates; preview unless --apply."""
    settings = settings_or_exit()
    root = settings.para_root
    base = (path or root).expanduser()
    if not base.is_dir():
        fail(f"no such folder: {base}")
    config = config_or_exit()
    try:
        plan = plan_clean([base], root=root, duplicates=duplicates, keep=kept_folders(root, config))
    except ValueError as exc:
        fail(str(exc))
    _print_plan(plan, root)
    if not apply_:
        typer.echo("preview only; add --apply to move these to .trash")
        return
    run_id = new_run_id(settings.state_dir)
    with Journal(settings.state_dir, run_id) as journal:
        report = apply_clean(plan, root=root, journal=journal)
    typer.echo(
        f"run {run_id}: {len(report.trashed)} to .trash, "
        f"{len(report.removed_dirs)} empty folders removed, {len(report.skipped)} skipped"
    )
    if report.trashed or report.removed_dirs:
        typer.echo(f"undo with: para-files undo {run_id}")
