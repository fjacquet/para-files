"""Migrate command for para-files CLI.

This module provides the 'migrate' command which reorganizes existing folders
based on retention rules:
- Permanent folders → 3_Resources/ (no suffix needed)
- Time-limited folders → 4_Archives/ with retention suffix

FAST: Works at folder level, not file level.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Annotated, Any

import typer

from para_files.cli.app import app
from para_files.cli.shared import (
    load_config_or_exit,
    setup_logging,
)


logger = logging.getLogger(__name__)

# Retention types and their target PARA category
# permanent → 3_Resources (no suffix)
# others → 4_Archives (with suffix)
RETENTION_CONFIG: dict[str, dict[str, str | None]] = {
    # Permanent categories → Resources (no suffix)
    "administratif": {"retention": "permanent", "suffix": None},
    "identite": {"retention": "permanent", "suffix": None},
    "sante": {"retention": "permanent", "suffix": None},
    "carriere": {"retention": "permanent", "suffix": None},
    "formation": {"retention": "permanent", "suffix": None},
    "education": {"retention": "permanent", "suffix": None},
    "famille": {"retention": "permanent", "suffix": None},
    "succession": {"retention": "permanent", "suffix": None},
    "vehicules": {"retention": "permanent", "suffix": None},
    "animaux": {"retention": "permanent", "suffix": None},
    "immobilier": {"retention": "permanent", "suffix": None},  # Property docs
    # Time-limited categories → Archives (with suffix)
    "fiscalite": {"retention": "10_years", "suffix": "_10y"},
    "dons": {"retention": "10_years", "suffix": "_10y"},
    "travail": {"retention": "10_years", "suffix": "_10y"},
    "banque": {"retention": "10_years", "suffix": "_10y"},
    "juridique": {"retention": "10_years", "suffix": "_10y"},
    "factures": {"retention": "5_years", "suffix": "_5y"},
    "prevoyance": {"retention": "retirement", "suffix": "_ret"},
    "retraite": {"retention": "retirement", "suffix": "_ret"},
    "assurance-vie": {"retention": "retirement", "suffix": "_ret"},
    "vehicule": {"retention": "contract", "suffix": "_ctr"},
    "abonnement": {"retention": "contract", "suffix": "_ctr"},
}

# Patterns that indicate a folder already has a retention suffix
RETENTION_SUFFIX_PATTERN = re.compile(r"_(perm|10y|5y|2y|ret|ctr)$")


def _build_retention_mapping_from_taxonomy() -> dict[str, dict[str, Any]]:
    """Build folder mapping from documents.json taxonomy.

    Returns mapping of base folder name → {retention, suffix, target_para}.
    """
    try:
        from para_files.taxonomies.loader import TaxonomyLoader

        loader = TaxonomyLoader()
        taxonomy = loader.load_documents()

        mapping: dict[str, dict[str, Any]] = {}

        for category in taxonomy.categories:
            for doc in category.documents:
                para_pattern = doc.para_pattern or ""
                retention = doc.retention or ""
                if not para_pattern:
                    continue

                parts = para_pattern.split("/")
                if len(parts) >= 2:
                    target_para = parts[0]  # "3_Resources" or "4_Archives"
                    folder_with_suffix = parts[1]

                    # Extract base name and suffix
                    match = RETENTION_SUFFIX_PATTERN.search(folder_with_suffix)
                    if match:
                        base_name = folder_with_suffix[: match.start()]
                        suffix = match.group(0)
                    else:
                        base_name = folder_with_suffix
                        suffix = None

                    if base_name and base_name not in mapping:
                        # Determine if permanent based on target or retention
                        is_permanent = (
                            target_para == "3_Resources"
                            or retention == "permanent"
                            or suffix == "_perm"
                        )

                        mapping[base_name] = {
                            "retention": "permanent" if is_permanent else retention,
                            "suffix": None if is_permanent else suffix,
                            "target_para": "3_Resources" if is_permanent else "4_Archives",
                        }

        if mapping:
            logger.debug("Built retention mapping from taxonomy: %d entries", len(mapping))
            return mapping

    except (OSError, ValueError, KeyError) as e:
        logger.debug("Could not load taxonomy, using static mapping: %s", e)

    # Convert static config to full mapping
    return {
        name: {
            "retention": config["retention"],
            "suffix": config["suffix"],
            "target_para": "3_Resources" if config["retention"] == "permanent" else "4_Archives",
        }
        for name, config in RETENTION_CONFIG.items()
    }


def _discover_folders_to_migrate(
    base_path: Path,
    mapping: dict[str, dict[str, Any]],
    *,
    category_filter: str | None = None,
) -> list[tuple[Path, Path, str]]:
    """Discover folders that need migration.

    Args:
        base_path: PARA root directory.
        mapping: Base name → retention config mapping.
        category_filter: Optional category to filter.

    Returns:
        List of (source_folder, destination_folder, action) tuples.
        Action is one of: "rename", "move", "move_rename"
    """
    migrations: list[tuple[Path, Path, str]] = []

    for para_folder in ["3_Resources", "4_Archives"]:
        folder_path = base_path / para_folder
        if not folder_path.exists():
            continue

        for child in folder_path.iterdir():
            if not child.is_dir():
                continue

            folder_name = child.name

            # Strip existing suffix to get base name
            base_name = folder_name
            match = RETENTION_SUFFIX_PATTERN.search(folder_name)
            if match:
                base_name = folder_name[: match.start()]

            # Apply category filter
            if category_filter and not base_name.startswith(category_filter):
                continue

            # Look up in mapping
            if base_name not in mapping:
                continue

            config = mapping[base_name]
            target_para = config["target_para"]
            target_suffix = config["suffix"]

            # Determine new folder name and location
            new_name = base_name + (target_suffix or "")
            new_path = base_path / target_para / new_name

            # Skip if already correct
            if child == new_path:
                continue

            # Skip if destination exists
            if new_path.exists():
                logger.warning("Cannot migrate %s: destination %s already exists", child, new_path)
                continue

            # Determine action type
            same_para = para_folder == target_para
            same_name = folder_name == new_name

            if same_para and not same_name:
                action = "rename"
            elif not same_para and same_name:
                action = "move"
            elif not same_para and not same_name:
                action = "move_rename"
            else:
                continue  # No change needed

            migrations.append((child, new_path, action))

    return migrations


def _migrate_folder(
    source: Path,
    destination: Path,
    action: str,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Migrate a folder by renaming or moving it.

    Args:
        source: Source folder path.
        destination: Destination folder path.
        action: Type of migration (rename, move, move_rename).
        dry_run: If True, don't actually change anything.

    Returns:
        Migration result dict.
    """
    file_count = sum(1 for _ in source.rglob("*") if _.is_file())

    result: dict[str, Any] = {
        "source": str(source),
        "destination": str(destination),
        "action": action,
        "files_in_folder": file_count,
        "success": False,
        "dry_run_action": f"would_{action}" if dry_run else action,
    }

    if dry_run:
        result["success"] = True
        return result

    try:
        # Ensure parent directory exists for cross-PARA moves
        destination.parent.mkdir(parents=True, exist_ok=True)

        if source.parent == destination.parent:
            # Same directory - simple rename
            source.rename(destination)
        else:
            # Different directory - use shutil.move for cross-device support
            shutil.move(str(source), str(destination))

        result["success"] = True

    except OSError as e:
        result["dry_run_action"] = "error"
        result["message"] = str(e)

    return result


def _print_summary(results: dict[str, Any], *, dry_run: bool) -> None:
    """Print migration summary."""
    typer.echo("")
    typer.echo("=" * 50)
    typer.echo("Migration Summary:")
    typer.echo(f"  Folders found:        {results['folders_scanned']}")
    typer.echo(f"  Folders to migrate:   {results['folders_need_migration']}")
    typer.echo(f"  Total files affected: {results['total_files']}")

    if dry_run:
        typer.echo(f"  Would process:        {results['folders_migrated']}")
        typer.echo("")
        typer.echo("This was a dry run. Use --no-dry-run to execute.")
    else:
        typer.echo(f"  Processed:            {results['folders_migrated']}")
        typer.echo(f"  Errors:               {results['folders_errored']}")

    if results["migrations"]:
        typer.echo("")
        typer.echo("Migrations:")
        for m in results["migrations"]:
            src_parts = Path(m["source"]).parts[-2:]  # e.g., ("4_Archives", "sante")
            dst_parts = Path(m["destination"]).parts[-2:]
            src_display = "/".join(src_parts)
            dst_display = "/".join(dst_parts)
            files = m.get("files_in_folder", 0)
            action = m.get("action", "?")
            status = "→" if m["success"] else "✗"

            # Show action type
            if action == "move":
                action_icon = "📦"  # Move across PARA
            elif action == "rename":
                action_icon = "✏️"  # Rename in place
            else:
                action_icon = "📦✏️"  # Move and rename

            typer.echo(f"  {status} {action_icon} {src_display} → {dst_display} ({files} files)")


def _run_migration(
    base_path: Path,
    *,
    dry_run: bool,
    category: str | None,
    output_json: bool,
    verbose: bool,
) -> dict[str, Any]:
    """Execute the folder-based migration process.

    Args:
        base_path: PARA root directory.
        dry_run: If True, simulate without changes.
        category: Optional category filter.
        output_json: If True, suppress console output.
        verbose: If True, show detailed output.

    Returns:
        Results dictionary.
    """
    results: dict[str, Any] = {
        "base_path": str(base_path),
        "dry_run": dry_run,
        "category_filter": category,
        "folders_scanned": 0,
        "folders_need_migration": 0,
        "folders_migrated": 0,
        "folders_errored": 0,
        "total_files": 0,
        "migrations": [],
        "errors": [],
    }

    if not output_json:
        action = "Preview" if dry_run else "Migrate"
        typer.echo(f"{action}ing folders in {base_path}...")
        if category:
            typer.echo(f"Category filter: {category}")

    mapping = _build_retention_mapping_from_taxonomy()
    if verbose and not output_json:
        typer.echo(f"Loaded {len(mapping)} retention mappings")

    folder_migrations = _discover_folders_to_migrate(base_path, mapping, category_filter=category)

    results["folders_scanned"] = len(folder_migrations)
    results["folders_need_migration"] = len(folder_migrations)

    if not output_json:
        typer.echo(f"Found {len(folder_migrations)} folders to migrate")

    for source, destination, action in folder_migrations:
        migration_result = _migrate_folder(source, destination, action, dry_run=dry_run)
        results["migrations"].append(migration_result)
        results["total_files"] += migration_result.get("files_in_folder", 0)

        if migration_result["success"]:
            results["folders_migrated"] += 1
        else:
            results["folders_errored"] += 1
            results["errors"].append(migration_result)

        if verbose and not output_json:
            status = "+" if migration_result["success"] else "x"
            typer.echo(f"  {status} {source.name} → {destination.name} ({action})")

    return results


@app.command()
def migrate(
    base_path: Annotated[
        Path | None,
        typer.Argument(
            help="PARA root directory (defaults to config para_root)",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview changes without moving/renaming"),
    ] = True,
    category: Annotated[
        str | None,
        typer.Option("--category", "-c", help="Migrate only folders starting with this prefix"),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output results as JSON"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output"),
    ] = False,
) -> None:
    """Migrate folders based on PARA retention rules.

    Reorganizes folders according to retention policy:
    - Permanent docs → 3_Resources/ (no suffix needed)
    - Time-limited docs → 4_Archives/ with retention suffix

    This is a FAST operation that works at folder level.
    For per-file reclassification, use 'rescan' instead.

    \b
    Examples:
        # Preview all migrations (uses config para_root)
        uv run para-files migrate

        # Execute migration
        uv run para-files migrate --no-dry-run

        # Migrate only fiscal folders
        uv run para-files migrate --category fiscalite

        # Override path
        uv run para-files migrate /custom/path

    \b
    Migration types:
        📦 move       - Relocate between Resources/Archives
        ✏️  rename     - Add/change retention suffix
        📦✏️ move_rename - Both move and rename
    """
    setup_logging(verbose=verbose)
    config = load_config_or_exit()

    effective_path = base_path if base_path else config.para_root

    results = _run_migration(
        effective_path,
        dry_run=dry_run,
        category=category,
        output_json=output_json,
        verbose=verbose,
    )

    if output_json:
        typer.echo(json.dumps(results, indent=2))
    else:
        _print_summary(results, dry_run=dry_run)
