"""The para-files Typer app; each ``*_cmd`` module registers one command on it."""

from __future__ import annotations

from typing import Annotated

import typer


app = typer.Typer(
    name="para-files",
    help="File documents into a PARA tree: preview first, apply on request, undo any run.",
    no_args_is_help=True,
    add_completion=False,
)


def _show_version(value: bool) -> None:  # noqa: FBT001 - Typer option callback signature
    if value:
        from para_files import __version__

        typer.echo(f"para-files {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", "-V", callback=_show_version, is_eager=True, help="Show the version."
        ),
    ] = False,
) -> None:
    """File documents into a PARA tree: preview first, apply on request, undo any run."""
