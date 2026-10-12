"""`para-files tree [--validate]`: leaves, settings, calibration progress, warnings."""

from __future__ import annotations

from collections import Counter
from typing import Annotated

import typer

from para_files.cli.app import app
from para_files.cli.common import config_or_exit, settings_or_exit
from para_files.core.journal import confirmation_stats
from para_files.core.settings import CoreSettings, config_dir_path
from para_files.core.tree import TreeConfig, validation_warnings


def _print_leaves(config: TreeConfig) -> None:
    rules = Counter(rule.leaf for rule in config.rules.rules)
    pinned = Counter(rule.leaf for rule in config.rules.rules if rule.pin)
    issuers = Counter(
        leaf_id for issuer in config.issuers.issuers.values() for leaf_id in issuer.leaves
    )
    typer.echo(f"leaves ({len(config.tree.leaves)}):")
    for leaf_id, leaf in sorted(config.tree.leaves.items(), key=lambda item: item[1].path):
        typer.echo(
            f"  {leaf.path:<40} {leaf_id:<32} {leaf.kind:<9} {leaf.retention or '-':<9} "
            f"rules {rules[leaf_id]:<3} pinned {pinned[leaf_id]:<3} issuers {issuers[leaf_id]}"
        )


def _print_settings(settings: CoreSettings) -> None:
    key = "set" if settings.openrouter_api_key else "not set"
    fallback = (
        f"{settings.fallback_model}, then {settings.fallback_backup_model} (key {key})"
        if settings.fallback_enabled
        else "off"
    )
    typer.echo("settings:")
    typer.echo(f"  para_root      {settings.para_root}")
    typer.echo(f"  fallback       {fallback}")
    typer.echo(
        f"  green at       model {settings.fallback_green} once calibrated; "
        f"model below {settings.fallback_red} is red"
    )
    typer.echo(f"  workers        {settings.max_workers}")
    typer.echo(f"  cache          {settings.cache_path}")
    typer.echo(f"  journal        {settings.state_dir}")


def _print_calibration(settings: CoreSettings, config: TreeConfig) -> None:
    stats = confirmation_stats(settings.state_dir, config.tree)
    typer.echo(
        f"calibration (the model stays yellow until {settings.calibration_min} "
        "confirmed decisions per kind):"
    )
    for kind in ("record", "library", "media", "knowledge"):
        confirmed, right = stats.get(kind, (0, 0))
        share = f"{right / confirmed:.0%}" if confirmed else "-"
        typer.echo(f"  {kind:<10} {confirmed:>4} confirmed, proposed right {right} ({share})")


@app.command("tree")
def tree_command(
    validate: Annotated[
        bool, typer.Option("--validate", help="Also list the config warnings.")
    ] = False,
) -> None:
    """Show the leaves, the effective settings and the calibration progress."""
    settings = settings_or_exit()
    directory = config_dir_path()
    config = config_or_exit(directory)
    typer.echo(f"config: {directory}")
    _print_leaves(config)
    _print_settings(settings)
    _print_calibration(settings, config)
    if validate:
        warnings = validation_warnings(config)
        typer.echo(f"warnings ({len(warnings)}):")
        for warning in warnings:
            typer.echo(f"  {warning}")
