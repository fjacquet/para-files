"""Shared CLI plumbing: settings and run context with readable errors."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NoReturn

import typer
from pydantic import ValidationError

from para_files.core.decide import Context
from para_files.core.settings import CoreSettings, load_settings
from para_files.core.sort import build_context
from para_files.core.tree import TreeConfig, TreeError, load_tree_config


EXIT_FAILURE = 1
EXIT_USAGE = 2
ROOT_HINT = "set PARA_FILES_PARA_ROOT in the environment or in ~/.config/para-files/.env"


def fail(message: str, code: int = EXIT_USAGE) -> NoReturn:
    """Print an error on stderr and exit."""
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(code)


def _describe(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors():
        where = ".".join(str(item) for item in error["loc"]) or "settings"
        hint = f" ({ROOT_HINT})" if where == "para_root" else ""
        parts.append(f"{where}: {error['msg']}{hint}")
    return "; ".join(parts)


def settings_or_exit(**overrides: Any) -> CoreSettings:  # noqa: ANN401 - settings overrides
    """Load settings, or exit with a message naming what is wrong."""
    try:
        return load_settings(**overrides)
    except ValidationError as exc:
        fail(_describe(exc))


def context_or_exit(settings: CoreSettings) -> Context:
    """Load the tree config and open the cache, or exit with the config error."""
    try:
        return build_context(settings)
    except TreeError as exc:
        fail(str(exc))


def config_or_exit(directory: Path | None = None) -> TreeConfig:
    """Load tree.yaml and its companions, or exit with the config error."""
    try:
        return load_tree_config(directory)
    except TreeError as exc:
        fail(str(exc))


def relative(path: Path, root: Path) -> str:
    """path relative to the PARA root when inside it, else as given."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)
