"""Migrate command for para-files CLI.

This module provides the 'migrate' command which reorganizes existing folders
based on retention rules:
- Permanent folders → 3_Resources/ (no prefix needed)
- Time-limited folders → 4_Archives/ with retention prefix (e.g., 10y_fiscalite)

FAST: Works at folder level, not file level.
"""

from __future__ import annotations

import contextlib
import filecmp
import json
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, TypedDict

import typer
from loguru import logger

from para_files.cli.app import app
from para_files.cli.shared import (
    load_config_or_exit,
    setup_logging,
)


# Retention types and their target PARA category
# permanent → 3_Resources (no suffix)
# others → 4_Archives (with prefix)


class _RetentionEntry(TypedDict):
    """Type for retention config entries."""

    retention: str
    prefix: str | None


RETENTION_CONFIG: dict[str, _RetentionEntry] = {
    # Permanent categories → Resources (no prefix needed)
    "administratif": {"retention": "permanent", "prefix": None},
    "identite": {"retention": "permanent", "prefix": None},
    "sante": {"retention": "permanent", "prefix": None},
    "carriere": {"retention": "permanent", "prefix": None},
    "formation": {"retention": "permanent", "prefix": None},
    "education": {"retention": "permanent", "prefix": None},
    "famille": {"retention": "permanent", "prefix": None},
    "prevoyance": {"retention": "permanent", "prefix": None},
    "retraite": {"retention": "permanent", "prefix": None},
    "assurance-vie": {"retention": "permanent", "prefix": None},
    "succession": {"retention": "permanent", "prefix": None},
    "vehicules": {"retention": "permanent", "prefix": None},
    "animaux": {"retention": "permanent", "prefix": None},
    "immobilier": {"retention": "permanent", "prefix": None},
    "correspondance": {"retention": "permanent", "prefix": None},
    # Time-limited categories → Archives (with prefix)
    "fiscalite": {"retention": "10_years", "prefix": "10y_"},
    "impots-france": {"retention": "10_years", "prefix": "10y_"},
    "impots-suisse": {"retention": "10_years", "prefix": "10y_"},
    "dons": {"retention": "10_years", "prefix": "10y_"},
    "travail": {"retention": "10_years", "prefix": "10y_"},
    "banque": {"retention": "10_years", "prefix": "10y_"},
    "banques": {"retention": "10_years", "prefix": "10y_"},
    "juridique": {"retention": "10_years", "prefix": "10y_"},
    "factures": {"retention": "contract", "prefix": "ctr_"},
    "mobilite": {"retention": "contract", "prefix": "ctr_"},
    "abonnement": {"retention": "contract", "prefix": "ctr_"},
    "agriculture": {"retention": "contract", "prefix": "ctr_"},
    "assurances": {"retention": "contract", "prefix": "ctr_"},
    "comptabilite": {"retention": "10_years", "prefix": "10y_"},
    "voyages": {"retention": "5_years", "prefix": "5y_"},
    "loisirs": {"retention": "2_years", "prefix": "2y_"},
}

# Pattern to detect folder with retention prefix (e.g., "10y_fiscalite")
RETENTION_PREFIX_PATTERN = re.compile(r"^(10y|5y|2y|ret|ctr)_")

# Pattern to detect OLD suffix format (e.g., "fiscalite_10y") for migration
RETENTION_SUFFIX_PATTERN = re.compile(r"_(10y|5y|2y|ret|ctr|perm)$")

# Minimum path parts required for valid PARA pattern (e.g., "4_Archives/fiscalite")
MIN_PARA_PATH_PARTS = 2


def _build_mapping_entry(
    retention: str, prefix: str | None, *, is_permanent: bool
) -> dict[str, Any]:
    """Build a single mapping entry dict."""
    return {
        "retention": "permanent" if is_permanent else retention,
        "prefix": None if is_permanent else prefix,
        "target_para": "3_Resources" if is_permanent else "4_Archives",
    }


def _parse_folder_from_pattern(para_pattern: str) -> tuple[str, str | None, str] | None:
    """Parse a PARA pattern to extract base name, prefix, and target.

    Args:
        para_pattern: Pattern like "4_Archives/10y_fiscalite/{year}"

    Returns:
        Tuple of (base_name, prefix, target_para) or None if invalid.
    """
    parts = para_pattern.split("/")
    if len(parts) < MIN_PARA_PATH_PARTS:
        return None

    target_para = parts[0]  # "3_Resources" or "4_Archives"
    folder_with_prefix = parts[1]

    # Extract base name and prefix (e.g., "10y_fiscalite" → "fiscalite", "10y_")
    match = RETENTION_PREFIX_PATTERN.match(folder_with_prefix)
    if match:
        prefix = match.group(0)
        base_name = folder_with_prefix[match.end() :]
    else:
        base_name = folder_with_prefix
        prefix = None

    if not base_name:
        return None

    return base_name, prefix, target_para


def _build_retention_mapping_from_taxonomy() -> dict[str, dict[str, Any]]:
    """Build folder mapping from documents.json taxonomy.

    Returns mapping of base folder name → {retention, prefix, target_para}.
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

                parsed = _parse_folder_from_pattern(para_pattern)
                if parsed is None:
                    continue

                base_name, prefix, target_para = parsed
                if base_name in mapping:
                    continue

                is_permanent = target_para == "3_Resources" or retention == "permanent"
                mapping[base_name] = _build_mapping_entry(
                    retention, prefix, is_permanent=is_permanent
                )

        # Merge static config for folder names not in taxonomy
        _merge_static_config(mapping)

        if mapping:
            logger.debug("Built retention mapping from taxonomy: %d entries", len(mapping))
            return mapping

    except (OSError, ValueError, KeyError) as e:
        logger.debug("Could not load taxonomy, using static mapping: %s", e)

    return _build_static_mapping()


def _merge_static_config(mapping: dict[str, dict[str, Any]]) -> None:
    """Merge static RETENTION_CONFIG entries into mapping."""
    for name, config in RETENTION_CONFIG.items():
        if name not in mapping:
            is_permanent = config["retention"] == "permanent"
            mapping[name] = _build_mapping_entry(
                config["retention"], config["prefix"], is_permanent=is_permanent
            )


def _build_static_mapping() -> dict[str, dict[str, Any]]:
    """Build mapping from static RETENTION_CONFIG only."""
    return {
        name: _build_mapping_entry(
            config["retention"],
            config["prefix"],
            is_permanent=config["retention"] == "permanent",
        )
        for name, config in RETENTION_CONFIG.items()
    }


def _extract_base_name(folder_name: str) -> str:
    """Extract base name by stripping retention prefix or suffix.

    Handles both new format (10y_fiscalite) and old format (fiscalite_10y).
    """
    prefix_match = RETENTION_PREFIX_PATTERN.match(folder_name)
    if prefix_match:
        return folder_name[prefix_match.end() :]

    suffix_match = RETENTION_SUFFIX_PATTERN.search(folder_name)
    if suffix_match:
        return folder_name[: suffix_match.start()]

    return folder_name


def _determine_action(
    current_para: str, target_para: str, current_name: str, new_name: str
) -> str | None:
    """Determine migration action based on current vs target state.

    Returns action string or None if no change needed.
    """
    same_para = current_para == target_para
    same_name = current_name == new_name

    if same_para and same_name:
        return None  # No change needed
    if same_para:
        return "rename"
    if same_name:
        return "move"
    return "move_rename"


def _should_skip_folder(
    base_name: str, category_filter: str | None, mapping: dict[str, dict[str, Any]]
) -> bool:
    """Check if folder should be skipped based on filter and mapping."""
    if category_filter and not base_name.startswith(category_filter):
        return True
    return base_name not in mapping


def _handle_existing_destination(
    child: Path, new_path: Path, *, merge: bool
) -> tuple[Path, Path, str] | None:
    """Handle case when destination already exists."""
    if merge:
        return (child, new_path, "merge")
    logger.warning("Cannot migrate %s: destination %s already exists", child, new_path)
    return None


def _process_folder_for_migration(
    child: Path,
    para_folder: str,
    base_path: Path,
    mapping: dict[str, dict[str, Any]],
    category_filter: str | None,
    *,
    merge: bool,
) -> tuple[Path, Path, str] | None:
    """Process a single folder and return migration tuple if needed."""
    folder_name = child.name
    base_name = _extract_base_name(folder_name)

    if _should_skip_folder(base_name, category_filter, mapping):
        return None

    config = mapping[base_name]
    target_para = config["target_para"]
    target_prefix = config["prefix"]

    new_name = (target_prefix or "") + base_name
    new_path = base_path / target_para / new_name

    # Skip if already correct
    if child == new_path:
        return None

    # Handle destination exists case
    if new_path.exists():
        return _handle_existing_destination(child, new_path, merge=merge)

    # Determine action type
    action = _determine_action(para_folder, target_para, folder_name, new_name)
    return (child, new_path, action) if action else None


def _discover_folders_to_migrate(
    base_path: Path,
    mapping: dict[str, dict[str, Any]],
    *,
    category_filter: str | None = None,
    merge: bool = False,
) -> list[tuple[Path, Path, str]]:
    """Discover folders that need migration.

    Args:
        base_path: PARA root directory.
        mapping: Base name → retention config mapping.
        category_filter: Optional category to filter.
        merge: If True, allow merging into existing folders.

    Returns:
        List of (source_folder, destination_folder, action) tuples.
        Action is one of: "rename", "move", "move_rename", "merge"
    """
    migrations: list[tuple[Path, Path, str]] = []

    for para_folder in ["3_Resources", "4_Archives"]:
        folder_path = base_path / para_folder
        if not folder_path.exists():
            continue

        for child in folder_path.iterdir():
            if not child.is_dir():
                continue

            result = _process_folder_for_migration(
                child, para_folder, base_path, mapping, category_filter, merge=merge
            )
            if result:
                migrations.append(result)

    return migrations


def _migrate_folder(
    source: Path,
    destination: Path,
    action: str,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Migrate a folder by renaming, moving, or merging it.

    Args:
        source: Source folder path.
        destination: Destination folder path.
        action: Type of migration (rename, move, move_rename, merge).
        dry_run: If True, don't actually change anything.

    Returns:
        Migration result dict.
    """
    # Handle merge action separately
    if action == "merge":
        return _merge_folder(source, destination, dry_run=dry_run)

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


def _get_unique_filename(dst_dir: Path, stem: str, suffix: str) -> str:
    """Get a unique filename by adding counter suffix if needed."""
    new_name = f"{stem}_from_archives{suffix}"
    new_dst = dst_dir / new_name
    counter = 1
    while new_dst.exists():
        new_name = f"{stem}_from_archives_{counter}{suffix}"
        new_dst = dst_dir / new_name
        counter += 1
    return new_name


def _handle_file_merge(
    item: Path,
    dst_item: Path,
    dst_dir: Path,
    result: dict[str, Any],
    *,
    dry_run: bool,
) -> None:
    """Handle merging a single file."""
    if not dst_item.exists():
        # File only in source → move it
        if not dry_run:
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), str(dst_item))
        result["files_moved"] += 1
        result["details"].append({"file": str(item), "action": "moved"})
    elif filecmp.cmp(item, dst_item, shallow=False):
        # Identical files → delete source duplicate
        if not dry_run:
            item.unlink()
        result["files_duplicate"] += 1
        result["details"].append({"file": str(item), "action": "deleted_duplicate"})
    else:
        # Different files → rename and move
        new_name = _get_unique_filename(dst_dir, item.stem, item.suffix)
        new_dst = dst_dir / new_name
        if not dry_run:
            shutil.move(str(item), str(new_dst))
        result["files_renamed"] += 1
        result["details"].append({"file": str(item), "action": "renamed", "new_name": new_name})


def _handle_dir_merge(
    item: Path,
    dst_item: Path,
    dst_dir: Path,
    result: dict[str, Any],
    recurse_fn: Callable[..., None],
    *,
    dry_run: bool,
) -> None:
    """Handle merging a directory."""
    if dst_item.exists() and dst_item.is_dir():
        recurse_fn(item, dst_item, result, dry_run=dry_run)
        result["subdirs_merged"] += 1
    else:
        if not dry_run:
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), str(dst_item))
        moved_files = sum(1 for _ in item.rglob("*") if _.is_file())
        result["files_moved"] += moved_files


def _merge_recursive(
    src_dir: Path, dst_dir: Path, result: dict[str, Any], *, dry_run: bool
) -> None:
    """Recursively merge directories."""
    for item in src_dir.iterdir():
        dst_item = dst_dir / item.name

        if item.is_file():
            _handle_file_merge(item, dst_item, dst_dir, result, dry_run=dry_run)
        elif item.is_dir():
            _handle_dir_merge(item, dst_item, dst_dir, result, _merge_recursive, dry_run=dry_run)


def _init_merge_result(source: Path, destination: Path, *, dry_run: bool) -> dict[str, Any]:
    """Initialize merge result dictionary."""
    return {
        "source": str(source),
        "destination": str(destination),
        "action": "merge",
        "files_moved": 0,
        "files_duplicate": 0,
        "files_renamed": 0,
        "subdirs_merged": 0,
        "success": False,
        "dry_run_action": "would_merge" if dry_run else "merge",
        "details": [],
    }


def _merge_folder(
    source: Path,
    destination: Path,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Merge source folder contents into destination folder.

    Smart deduplication:
    - If file only in source → move to destination
    - If file only in destination → keep as-is
    - If same file in both (identical content) → delete source duplicate
    - If different files with same name → rename source and move

    Args:
        source: Source folder to merge from (will be emptied).
        destination: Destination folder to merge into.
        dry_run: If True, don't actually change anything.

    Returns:
        Merge result dict with statistics.
    """
    result = _init_merge_result(source, destination, dry_run=dry_run)

    try:
        _merge_recursive(source, destination, result, dry_run=dry_run)

        if not dry_run:
            _remove_empty_dirs(source)

        result["success"] = True
        result["files_in_folder"] = (
            result["files_moved"] + result["files_duplicate"] + result["files_renamed"]
        )

    except OSError as e:
        result["dry_run_action"] = "error"
        result["message"] = str(e)

    return result


def _remove_empty_dirs(path: Path) -> None:
    """Recursively remove empty directories."""
    if not path.is_dir():
        return

    # First, recurse into subdirectories
    for child in list(path.iterdir()):
        if child.is_dir():
            _remove_empty_dirs(child)

    # Then try to remove this directory if empty
    with contextlib.suppress(OSError):
        path.rmdir()  # Directory not empty, that's fine


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
            src_parts = Path(m["source"]).parts[-2:]
            dst_parts = Path(m["destination"]).parts[-2:]
            src_display = "/".join(src_parts)
            dst_display = "/".join(dst_parts)
            files = m.get("files_in_folder", 0)
            action = m.get("action", "?")
            status = "→" if m["success"] else "✗"

            # Show action type with icons
            if action == "move":
                action_icon = "📦"
            elif action == "rename":
                action_icon = "✏️"
            elif action == "merge":
                action_icon = "🔀"
            else:
                action_icon = "📦✏️"

            # For merge actions, show additional details
            if action == "merge":
                moved = m.get("files_moved", 0)
                dupes = m.get("files_duplicate", 0)
                renamed = m.get("files_renamed", 0)
                typer.echo(
                    f"  {status} {action_icon} {src_display} → {dst_display} "
                    f"(moved:{moved} dupes:{dupes} renamed:{renamed})"
                )
            else:
                typer.echo(
                    f"  {status} {action_icon} {src_display} → {dst_display} ({files} files)"
                )


def _run_migration(
    base_path: Path,
    *,
    dry_run: bool,
    category: str | None,
    output_json: bool,
    verbose: bool,
    merge: bool = False,
) -> dict[str, Any]:
    """Execute the folder-based migration process.

    Args:
        base_path: PARA root directory.
        dry_run: If True, simulate without changes.
        category: Optional category filter.
        output_json: If True, suppress console output.
        verbose: If True, show detailed output.
        merge: If True, merge into existing folders instead of skipping.

    Returns:
        Results dictionary.
    """
    results: dict[str, Any] = {
        "base_path": str(base_path),
        "dry_run": dry_run,
        "category_filter": category,
        "merge_mode": merge,
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
        if merge:
            typer.echo("Merge mode: enabled (will merge into existing folders)")

    mapping = _build_retention_mapping_from_taxonomy()
    if verbose and not output_json:
        typer.echo(f"Loaded {len(mapping)} retention mappings")

    folder_migrations = _discover_folders_to_migrate(
        base_path, mapping, category_filter=category, merge=merge
    )

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
        typer.Option(
            "--dry-run/--no-dry-run", "-n/-N", help="Preview changes without moving/renaming"
        ),
    ] = False,
    merge: Annotated[
        bool,
        typer.Option("--merge", "-m", help="Merge into existing folders instead of skipping"),
    ] = False,
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
    - Permanent docs → 3_Resources/ (no prefix needed)
    - Time-limited docs → 4_Archives/ with retention prefix (e.g., 10y_fiscalite)

    This is a FAST operation that works at folder level.
    For per-file reclassification, use 'rescan' instead.

    \b
    Examples:
        # Migrate all folders (uses config para_root)
        uv run para-files migrate

        # Preview without moving
        uv run para-files migrate --dry-run

        # Merge into existing folders (when destination exists)
        uv run para-files migrate --merge

        # Migrate only fiscal folders
        uv run para-files migrate --category fiscalite

        # Override path
        uv run para-files migrate /custom/path

    \b
    Migration types:
        📦 move       - Relocate between Resources/Archives
        ✏️  rename     - Add/change retention prefix
        📦✏️ move_rename - Both move and rename
        🔀 merge      - Combine contents (with --merge)
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
        merge=merge,
    )

    if output_json:
        typer.echo(json.dumps(results, indent=2))
    else:
        _print_summary(results, dry_run=dry_run)
