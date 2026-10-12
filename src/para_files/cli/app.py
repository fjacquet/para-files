"""The para-files Typer app; each ``*_cmd`` module registers one command on it."""

from __future__ import annotations

import logging
import sys
import warnings
from typing import Annotated

import typer
from loguru import logger


LOG_FORMAT = "{level}: {message}"

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


def configure_logging(verbose: bool) -> None:  # noqa: FBT001 - plain switch
    """WARNING and above on stderr (DEBUG with --verbose); never stdout, so --json stays clean."""
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "WARNING", format=LOG_FORMAT)
    # Library chatter about files that still read fine ("Ignoring wrong pointing object",
    # "Print area cannot be set").
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


@app.callback()
def main(
    version: Annotated[  # noqa: ARG001 - Typer option; its callback does the work
        bool,
        typer.Option(
            "--version", "-V", callback=_show_version, is_eager=True, help="Show the version."
        ),
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show debug logs on stderr.")
    ] = False,
) -> None:
    """File documents into a PARA tree: preview first, apply on request, undo any run."""
    configure_logging(verbose)
