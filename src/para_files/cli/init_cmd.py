"""`para-files init [ROOT] [--apply]`: create 0_Inbox and the leaf folders."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from para_files.cli.app import app
from para_files.cli.common import ROOT_HINT, config_or_exit, fail
from para_files.core.apply import make_dirs
from para_files.core.journal import Journal, new_run_id
from para_files.core.settings import BUCKET_NAME, INBOX, load_path_settings


@app.command("init")
def init_command(
    root: Annotated[
        Path | None, typer.Argument(help="The PARA root (default: PARA_FILES_PARA_ROOT).")
    ] = None,
    apply_: Annotated[bool, typer.Option("--apply", help="Create the missing folders.")] = False,
) -> None:
    """List the folders tree.yaml expects that do not exist yet; create them with --apply."""
    settings = load_path_settings()
    base = root.expanduser() if root is not None else settings.para_root
    if base is None:
        fail(
            "no usable PARA root in the settings; pass it: "
            f"para-files init /path/to/PARA ({ROOT_HINT})"
        )
    if BUCKET_NAME.match(base.name):
        fail(f"{base} is a bucket; pass the folder that holds the buckets")
    if not base.parent.is_dir():
        fail(f"parent folder does not exist: {base.parent}")
    config = config_or_exit()
    wanted = [base / INBOX, *sorted({base / leaf.path for leaf in config.tree.leaves.values()})]
    missing = [path for path in wanted if not path.is_dir()]
    if not missing:
        typer.echo(f"{base}: every folder exists")
        return
    if not apply_:
        for path in missing:
            typer.echo(f"  missing  {path.relative_to(base).as_posix()}")
        typer.echo(f"{len(missing)} folders missing; add --apply to create them")
        return
    state_dir = settings.state_dir
    run_id = new_run_id(state_dir)
    with Journal(state_dir, run_id) as journal:
        for path in missing:
            typer.echo(f"  created  {path.relative_to(base).as_posix()}")
            make_dirs(path, journal)
        created = journal.path.exists()
    if created:
        typer.echo(f"undo with: para-files undo {run_id}")
