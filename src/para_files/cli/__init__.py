"""Command-line interface: six commands on one Typer app (spec §4.4).

Importing this package registers every command on ``para_files.cli.app.app``.
"""

from __future__ import annotations

from para_files.cli import (
    clean_cmd,  # noqa: F401 - imported to register the command
    explain_cmd,  # noqa: F401 - imported to register the command
    init_cmd,  # noqa: F401 - imported to register the command
    sort_cmd,  # noqa: F401 - imported to register the command
    tree_cmd,  # noqa: F401 - imported to register the command
    undo_cmd,  # noqa: F401 - imported to register the command
)
from para_files.cli.app import app


__all__ = ["app"]
