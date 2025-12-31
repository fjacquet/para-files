"""Init command for creating PARA folder structure.

This module provides the init command that creates the standard PARA
folder structure (Inbox, Projects, Areas, Resources, Archives) based
on the reference tree configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from loguru import logger

from para_files.cli.app import app
from para_files.cli.shared import (
    ensure_tree_exists,
    load_config_or_exit,
    setup_logging,
)


def _create_directory(
    dir_path: Path,
    *,
    dry_run: bool,
    created: list[Path],
    existing: list[Path],
) -> None:
    """Create a directory or track it for dry run.

    Creates the specified directory if it doesn't exist, or tracks its
    status for reporting. In dry-run mode, only reports what would happen.

    Args:
        dir_path: Path to the directory to create.
        dry_run: If True, don't actually create directories, just report.
        created: List to append newly created directory paths to.
        existing: List to append already existing directory paths to.
    """
    if dry_run:
        if dir_path.exists():
            typer.echo(f"  [exists] {dir_path}")
            existing.append(dir_path)
        else:
            typer.echo(f"  [create] {dir_path}")
            created.append(dir_path)
    elif dir_path.exists():
        logger.debug("Directory exists: %s", dir_path)
        existing.append(dir_path)
    else:
        dir_path.mkdir(parents=True, exist_ok=True)
        typer.echo(f"  Created: {dir_path}")
        created.append(dir_path)


def _extract_subfolder_patterns(tree_data: dict[str, Any]) -> list[str]:
    """Extract static subfolder patterns from tree data.

    Parses the reference tree YAML structure to find route patterns
    and extracts the static (non-templated) portion of each path.

    Args:
        tree_data: Parsed YAML data from the reference tree file.

    Returns:
        List of static subfolder path patterns (e.g., "2_Areas/Finance").
    """
    patterns: list[str] = []
    for section in ["projects", "areas", "resources", "archives"]:
        section_data = tree_data.get(section, {})
        routes = section_data.get("routes", [])
        for route in routes:
            pattern = route.get("pattern", "")
            if pattern:
                # Extract static part before any template variable
                static_path = pattern.split("{")[0].rstrip("/")
                if static_path and static_path not in patterns:
                    patterns.append(static_path)
    return patterns


def _print_init_summary(
    para_root: Path,
    created: list[Path],
    existing: list[Path],
    *,
    dry_run: bool,
) -> None:
    """Print init command summary.

    Displays a summary of the initialization operation, showing how many
    folders were created vs. already existed.

    Args:
        para_root: Root directory of the PARA structure.
        created: List of directories that were created (or would be in dry-run).
        existing: List of directories that already existed.
        dry_run: If True, indicate this was a dry run.
    """
    if dry_run:
        msg = f"{len(created)} folders to create, {len(existing)} already exist"
        typer.echo(f"\n\U0001f4c1 Dry run: {msg}")
    else:
        typer.echo(f"\n\u2705 PARA structure initialized at {para_root}")
        typer.echo(f"   Created: {len(created)} folders")
        typer.echo(f"   Existing: {len(existing)} folders")


@app.command()
def init(
    destination: Annotated[
        Path | None,
        typer.Argument(help="Root directory for PARA folders (default: from config)"),
    ] = None,
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    create_subfolders: Annotated[
        bool,
        typer.Option("--subfolders", "-s", help="Create subfolders from route patterns"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run/--no-dry-run", "-n", help="Preview folders without creating them"),
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Initialize PARA folder structure from reference tree.

    Creates the standard PARA folder structure:
    - 0_Inbox: Incoming files to be processed
    - 1_Projects: Active projects with deadlines
    - 2_Areas: Ongoing areas of responsibility
    - 3_Resources: Reference materials and interests
    - 4_Archives: Inactive items from other categories

    Optionally creates subfolders based on route patterns in the reference tree.
    """
    import yaml

    setup_logging(verbose=verbose)

    config = load_config_or_exit()
    para_root = destination or config.para_root
    tree_path = reference_tree or config.reference_tree_path
    ensure_tree_exists(tree_path)

    with tree_path.open() as f:
        tree_data = yaml.safe_load(f)

    main_dirs = ["0_Inbox", "1_Projects", "2_Areas", "3_Resources", "4_Archives"]
    created_dirs: list[Path] = []
    existing_dirs: list[Path] = []

    for dir_name in main_dirs:
        _create_directory(
            para_root / dir_name,
            dry_run=dry_run,
            created=created_dirs,
            existing=existing_dirs,
        )

    if create_subfolders:
        patterns = _extract_subfolder_patterns(tree_data)
        for pattern in sorted(patterns):
            _create_directory(
                para_root / pattern,
                dry_run=dry_run,
                created=created_dirs,
                existing=existing_dirs,
            )

    _print_init_summary(para_root, created_dirs, existing_dirs, dry_run=dry_run)
