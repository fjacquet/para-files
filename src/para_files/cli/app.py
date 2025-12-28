"""Typer application instance for para-files CLI.

This module contains the main Typer application instance that is shared
across all command modules. Commands register themselves on this app
instance by importing it and using the @app.command() decorator.
"""

from __future__ import annotations

from typing import Annotated

import typer


# Create the main Typer application
# All command modules will import this app and register their commands on it
app = typer.Typer(
    name="para-files",
    help="Classify files using the PARA method with MLX-powered semantic routing.",
    add_completion=True,
)


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", "-V", help="Show version and exit")] = False,
) -> None:
    """PARA Files - Intelligent file classification with MLX."""
    if version:
        from para_files import __version__

        typer.echo(f"para-files {__version__}")
        raise typer.Exit

    # If no command is provided, show help
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
