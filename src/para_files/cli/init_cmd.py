"""`para-files init [ROOT] [--apply]`: create 0_Inbox and the leaf folders."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from para_files.cli.app import app
from para_files.cli.common import ROOT_HINT, fail
from para_files.core.settings import BUCKET_NAME, INBOX, load_settings
from para_files.core.tree import TreeError, load_tree_config


def _root(given: Path | None) -> Path:
    if given is not None:
        return given.expanduser()
    try:
        return load_settings().para_root
    except ValidationError:
        fail(
            "no usable PARA root in the settings; pass it: "
            f"para-files init /path/to/PARA ({ROOT_HINT})"
        )


@app.command("init")
def init_command(
    root: Annotated[
        Path | None, typer.Argument(help="The PARA root (default: PARA_FILES_PARA_ROOT).")
    ] = None,
    apply_: Annotated[bool, typer.Option("--apply", help="Create the missing folders.")] = False,
) -> None:
    """List the folders tree.yaml expects that do not exist yet; create them with --apply."""
    base = _root(root)
    if BUCKET_NAME.match(base.name):
        fail(f"{base} is a bucket; pass the folder that holds the buckets")
    try:
        config = load_tree_config()
    except TreeError as exc:
        fail(str(exc))
    wanted = [base / INBOX, *sorted({base / leaf.path for leaf in config.tree.leaves.values()})]
    missing = [path for path in wanted if not path.is_dir()]
    if not missing:
        typer.echo(f"{base}: every folder exists")
        return
    for path in missing:
        typer.echo(f"  {'created' if apply_ else 'missing'}  {path.relative_to(base).as_posix()}")
        if apply_:
            path.mkdir(parents=True, exist_ok=True)
    if not apply_:
        typer.echo(f"{len(missing)} folders missing; add --apply to create them")
