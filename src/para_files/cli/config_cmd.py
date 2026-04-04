"""Config command for displaying configuration values.

This module provides the config command that shows the current
configuration loaded from the reference tree YAML file and
environment variables.
"""

from __future__ import annotations

from typing import Annotated

import typer
from loguru import logger
from pydantic import ValidationError

from para_files.cli.app import app
from para_files.config import load_config


@app.command()
def config(
    show: Annotated[
        bool,
        typer.Option("--show/--no-show", "-s/-S", help="Show current configuration values"),
    ] = True,
    path: Annotated[
        bool,
        typer.Option("--path", "-p", help="Show reference tree path"),
    ] = False,
) -> None:
    """Show configuration (loaded from reference tree YAML).

    Displays the current configuration values including:
    - PARA root directory
    - Reference tree path
    - MLX model settings
    - LLM fallback settings

    Configuration is loaded from the 'config:' section in your
    reference tree YAML file, with optional overrides via
    PARA_FILES_* environment variables.
    """
    from para_files.config import DEFAULT_REFERENCE_TREE

    if path:
        typer.echo(f"Reference tree: {DEFAULT_REFERENCE_TREE}")
        typer.echo(f"  Exists: {DEFAULT_REFERENCE_TREE.exists()}")
        typer.echo("\nConfig is stored in the 'config:' section of the reference tree YAML.")
        return

    if show:
        # Show current configuration
        try:
            cfg = load_config()
            typer.echo("Current configuration:\n")
            typer.echo(f"  para_root: {cfg.para_root}")
            typer.echo(f"  reference_tree_path: {cfg.reference_tree_path}")
            typer.echo(f"  validated_db_path: {cfg.validated_db_path}")
            typer.echo(f"  content_preview_chars: {cfg.content_preview_chars}")
            typer.echo("\n  [mlx]")
            typer.echo(f"    model_name: {cfg.mlx.model_name}")
            typer.echo(f"    score_threshold: {cfg.mlx.score_threshold}")
            typer.echo("\n  [llm]")
            typer.echo(f"    enabled: {cfg.llm.enabled}")
            typer.echo(f"    model: {cfg.llm.model}")
            typer.echo(f"    confidence_threshold: {cfg.llm.confidence_threshold}")
            typer.echo(f"    api_base: {cfg.llm.api_base}")
            typer.echo(f"\nReference tree: {cfg.reference_tree_path}")
            typer.echo(f"  Exists: {cfg.reference_tree_path.exists()}")
            typer.echo("\nConfig source: 'config:' section in reference tree YAML")
            typer.echo("Override with: PARA_FILES_* environment variables")
        except ValidationError:
            logger.exception("Configuration error")
            raise typer.Exit(1) from None
