"""Main entry point for the PARA Files classification system.

CLI for classifying files using the 5-signal pipeline.
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from pydantic import ValidationError

from para_files.config import DEFAULT_REFERENCE_TREE, load_config
from para_files.mover import ConflictStrategy, move_classified_file
from para_files.pipeline import ClassificationPipeline


if TYPE_CHECKING:
    from para_files.config import Config
    from para_files.learner import RoutingLearner
    from para_files.mover import MoveResult
    from para_files.types import ClassificationResult
    from para_files.utils.cleanup_log import CleanupLogger


logger = logging.getLogger(__name__)

# Create the Typer app
app = typer.Typer(
    name="para-files",
    help="Classify files using the PARA method with MLX-powered semantic routing.",
    add_completion=True,
)

# Constants
MAX_PATTERNS_SHOWN = 3
MAX_UTTERANCES_SHOWN = 5


def _load_config_or_exit() -> Config:
    """Load configuration, exit on error."""
    try:
        return load_config()
    except ValidationError:
        logger.exception("Configuration error")
        raise typer.Exit(1) from None


def _get_reference_tree_path(
    reference_tree: Path | None,
    config: Config | None = None,
) -> Path:
    """Get reference tree path from CLI or config."""
    if reference_tree:
        return reference_tree
    if config:
        return config.reference_tree_path
    try:
        cfg = load_config()
    except ValidationError:
        return DEFAULT_REFERENCE_TREE
    else:
        return cfg.reference_tree_path


def _validate_file_exists(file_path: Path) -> bool:
    """Validate file exists and is a file, log warnings if not."""
    if not file_path.exists():
        logger.warning("File not found: %s", file_path)
        return False
    if not file_path.is_file():
        logger.warning("Not a file: %s", file_path)
        return False
    return True


def _format_result_json(
    file_path: Path,
    result: ClassificationResult,
    target_path: Path,
) -> dict[str, Any]:
    """Format classification result as JSON dict."""
    output: dict[str, Any] = {
        "source_file": str(file_path),
        "category": result.category,
        "confidence": result.confidence.value,
        "source": result.confidence.source.value,
        "target_path": str(target_path),
    }
    if result.route_name:
        output["route_name"] = result.route_name
    if result.extracted_params:
        output["params"] = result.extracted_params
    return output


def _print_classification_result(
    file_path: Path,
    result: ClassificationResult,
    target_path: Path,
) -> None:
    """Print classification result to console."""
    typer.echo(f"\n📄 {file_path.name}")
    typer.echo(f"   Category: {result.category}")
    conf = result.confidence
    typer.echo(f"   Confidence: {conf.value:.0%} ({conf.source.value})")
    typer.echo(f"   Target: {target_path}")
    if result.route_name:
        typer.echo(f"   Route: {result.route_name}")


def _format_move_result_json(
    file_path: Path,
    result: ClassificationResult,
    target_dir: Path,
    move_result: MoveResult,
) -> dict[str, Any]:
    """Format move result as JSON dict."""
    output: dict[str, Any] = {
        "source_file": str(file_path),
        "category": result.category,
        "confidence": result.confidence.value,
        "source": result.confidence.source.value,
        "target_path": str(target_dir),
        "destination": str(move_result.destination),
        "action": move_result.action,
        "success": move_result.success,
    }
    if move_result.message:
        output["message"] = move_result.message
    if result.route_name:
        output["route_name"] = result.route_name
    return output


def _ensure_tree_exists(tree_path: Path) -> None:
    """Ensure reference tree file exists, exit if not."""
    if not tree_path.exists():
        typer.echo(f"Reference tree not found: {tree_path}", err=True)
        raise typer.Exit(1)


# --- Scan command helpers ---


def _validate_directory_or_exit(dir_path: Path) -> None:
    """Validate directory exists, exit on error."""
    if not dir_path.exists():
        logger.error("Directory not found: %s", dir_path)
        raise typer.Exit(1)
    if not dir_path.is_dir():
        logger.error("Not a directory: %s", dir_path)
        raise typer.Exit(1)


def _parse_extensions_filter(extensions: str | None) -> set[str] | None:
    """Parse comma-separated extensions into a set."""
    if not extensions:
        return None
    return {
        ext.strip().lower() if ext.startswith(".") else f".{ext.strip().lower()}"
        for ext in extensions.split(",")
    }


def _discover_files(
    dir_path: Path,
    *,
    recursive: bool,
    ext_filter: set[str] | None,
    skip_junk: bool = True,
) -> list[Path]:
    """Discover files in directory with optional filtering.

    Args:
        dir_path: Directory to scan
        recursive: Whether to scan subdirectories
        ext_filter: Set of extensions to include (None = all)
        skip_junk: Whether to skip junk files (DS_Store, etc.)

    Returns:
        Sorted list of file paths
    """
    from para_files.utils.cleanup import is_junk_file

    files = list(dir_path.rglob("*")) if recursive else list(dir_path.glob("*"))
    files = [f for f in files if f.is_file()]

    if skip_junk:
        files = [f for f in files if not is_junk_file(f)]

    if ext_filter:
        files = [f for f in files if f.suffix.lower() in ext_filter]

    return sorted(files)


def _classify_file_for_scan(
    file_path: Path,
    pipeline: ClassificationPipeline,
    stats: dict[str, int],
    *,
    output_json: bool,
) -> dict[str, Any] | None:
    """Classify a single file for scan command."""
    try:
        result = pipeline.classify_file(file_path)
        target_path = pipeline.get_target_path(result)
        source = result.confidence.source.value
        stats[source] = stats.get(source, 0) + 1

        if output_json:
            output: dict[str, Any] = {
                "source_file": str(file_path),
                "filename": file_path.name,
                "category": result.category,
                "confidence": result.confidence.value,
                "source": source,
                "target_path": str(target_path),
            }
            if result.route_name:
                output["route_name"] = result.route_name
            return output

        confidence_pct = f"{result.confidence.value:.0%}"
        typer.echo(f"\u0001F4C4 {file_path.name}")
        typer.echo(f"   \u2192 {result.category} ({confidence_pct} {source})")
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to classify %s: %s", file_path.name, e)
        if output_json:
            return {
                "source_file": str(file_path),
                "filename": file_path.name,
                "error": str(e),
            }
    return None


def _print_scan_summary(
    dir_path: Path,
    files: list[Path],
    stats: dict[str, int],
    results: list[dict[str, Any]],
    *,
    output_json: bool,
) -> None:
    """Print scan summary."""
    if output_json:
        output_data = {
            "directory": str(dir_path),
            "total_files": len(files),
            "stats": stats,
            "results": results,
        }
        typer.echo(json.dumps(output_data, indent=2))
    else:
        typer.echo(f"\n\U0001f4ca Summary: {len(files)} files scanned")
        for source, count in sorted(stats.items(), key=lambda x: -x[1]):
            typer.echo(f"   {source}: {count}")


# --- Init command helpers ---


def _create_directory(
    dir_path: Path,
    *,
    dry_run: bool,
    created: list[Path],
    existing: list[Path],
) -> None:
    """Create a directory or track it for dry run."""
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
    """Extract static subfolder patterns from tree data."""
    patterns: list[str] = []
    for section in ["projects", "areas", "resources", "archives"]:
        section_data = tree_data.get(section, {})
        routes = section_data.get("routes", [])
        for route in routes:
            pattern = route.get("pattern", "")
            if pattern:
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
    """Print init command summary."""
    if dry_run:
        msg = f"{len(created)} folders to create, {len(existing)} already exist"
        typer.echo(f"\n\U0001f4c1 Dry run: {msg}")
    else:
        typer.echo(f"\n\u2705 PARA structure initialized at {para_root}")
        typer.echo(f"   Created: {len(created)} folders")
        typer.echo(f"   Existing: {len(existing)} folders")


# --- Tree command helpers ---


def _show_tree_sections(
    tree_data: dict[str, Any],
    *,
    validate: bool,
    errors: list[str],
    warnings: list[str],
) -> tuple[int, int]:
    """Show tree sections and return route/utterance counts."""
    sections = ["inbox", "projects", "areas", "resources", "archives"]
    route_count = 0
    utterance_count = 0

    for section in sections:
        section_data = tree_data.get(section, {})
        if not section_data:
            if validate:
                warnings.append(f"Section '{section}' is empty or missing")
            continue

        path = section_data.get("path", section)
        routes = section_data.get("routes", [])
        route_count += len(routes)

        typer.echo(f"\n\U0001f4c2 {path}")

        for route in routes:
            name = route.get("name", "unnamed")
            pattern = route.get("pattern", "")
            utts = route.get("utterances", [])
            utterance_count += len(utts)

            if validate:
                if not pattern:
                    errors.append(f"Route '{name}' has no pattern")
                if not utts:
                    warnings.append(f"Route '{name}' has no utterances")

            typer.echo(f"   \u2514\u2500\u2500 {name}: {pattern} ({len(utts)} utterances)")

    return route_count, utterance_count


def _show_routing_rules(tree_data: dict[str, Any]) -> None:
    """Show routing rules from tree data."""
    rules = tree_data.get("routing_rules", {})
    if not rules:
        return

    typer.echo("\n\u2699\ufe0f  Routing Rules:")
    max_show = 5
    for rule_name, rule_data in rules.items():
        dest = rule_data.get("destination", "N/A")
        exts = rule_data.get("extensions", [])
        patterns = rule_data.get("patterns", [])
        typer.echo(f"   \u2514\u2500\u2500 {rule_name}:")
        if exts:
            ext_str = ", ".join(exts[:max_show])
            suffix = "..." if len(exts) > max_show else ""
            typer.echo(f"       Extensions: {ext_str}{suffix}")
        if patterns:
            pat_str = ", ".join(patterns[:MAX_PATTERNS_SHOWN])
            suffix = "..." if len(patterns) > MAX_PATTERNS_SHOWN else ""
            typer.echo(f"       Patterns: {pat_str}{suffix}")
        typer.echo(f"       \u2192 {dest}")


def _show_known_issuers(tree_data: dict[str, Any], *, verbose: bool) -> None:
    """Show known issuers from tree data."""
    known_issuers = tree_data.get("known_issuers", {})
    if not known_issuers:
        return

    typer.echo("\n\U0001f3e2 Known Issuers:")
    issuer_count = 0
    for category, category_data in known_issuers.items():
        issuers = category_data.get("issuers", [])
        issuer_count += len(issuers)
        pattern = category_data.get("pattern", "")
        typer.echo(f"   \u2514\u2500\u2500 {category}: {len(issuers)} issuers \u2192 {pattern}")
        if verbose:
            for issuer in issuers:
                typer.echo(f"       - {issuer}")
    typer.echo(f"\n   Total: {issuer_count} issuers across {len(known_issuers)} categories")


def _print_validation_results(
    errors: list[str],
    warnings: list[str],
) -> None:
    """Print validation results and exit if errors."""
    if errors:
        typer.echo("\n\u274c Errors:", err=True)
        for error in errors:
            typer.echo(f"   - {error}", err=True)

    if warnings:
        typer.echo("\n\u26a0\ufe0f  Warnings:")
        for warning in warnings:
            typer.echo(f"   - {warning}")

    if not errors and not warnings:
        typer.echo("\n\u2705 Validation passed!")
    elif errors:
        raise typer.Exit(1)


class ConflictChoice(str, Enum):
    """CLI choices for conflict strategy."""

    skip = "skip"
    overwrite = "overwrite"
    rename = "rename"
    rename_with_date = "rename_with_date"


def setup_logging(*, verbose: bool = False) -> None:
    """Configure logging.

    Args:
        verbose: Enable debug logging if True.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        force=True,  # Override any existing configuration
    )


@app.command()
def classify(
    files: Annotated[list[Path], typer.Argument(help="Path(s) to file(s) to classify")],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    output_json: Annotated[
        bool, typer.Option("--json", "-j", help="Output result as JSON")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Classify one or more files using the PARA method."""
    setup_logging(verbose=verbose)
    config = _load_config_or_exit()

    if reference_tree:
        config.reference_tree_path = reference_tree

    pipeline = ClassificationPipeline(config)
    results: list[dict[str, Any]] = []

    for file in files:
        file_path = file.resolve()
        if not _validate_file_exists(file_path):
            continue

        try:
            result = pipeline.classify_file(file_path)
            target_path = pipeline.get_target_path(result)

            if output_json:
                results.append(_format_result_json(file_path, result, target_path))
            else:
                _print_classification_result(file_path, result, target_path)
        except Exception:
            logger.exception("Failed to classify %s", file_path)
            if output_json:
                results.append({"source_file": str(file_path), "error": "classification failed"})

    if output_json:
        typer.echo(json.dumps(results, indent=2))


def _process_single_move(
    file_path: Path,
    pipeline: ClassificationPipeline,
    *,
    dry_run: bool,
    copy: bool,
    conflict_strategy: ConflictStrategy,
    date_prefix: bool,
    smart_rename: bool,
) -> tuple[Any, Any, bool]:
    """Process a single file move. Returns (result, move_result, success)."""
    result = pipeline.classify_file(file_path)
    target_dir = pipeline.get_target_path(result)

    move_result = move_classified_file(
        file_path,
        target_dir,
        dry_run=dry_run,
        copy_mode=copy,
        conflict_strategy=conflict_strategy,
        add_date_prefix=date_prefix,
        smart_rename=smart_rename,
        classification=result,
    )
    return result, move_result, move_result.success


def _print_move_result(
    file_path: Path,
    result: ClassificationResult,
    move_result: MoveResult,
    action_verb: str,
) -> None:
    """Print move result to console."""
    if move_result.success:
        typer.echo(f"{action_verb}: {file_path.name}")
        typer.echo(f"  -> {move_result.destination}")
        conf = result.confidence
        typer.echo(f"  Classification: {result.category} ({conf.value:.0%})")
    else:
        typer.echo(f"Failed: {file_path.name} - {move_result.message}", err=True)


def _handle_move_file(
    file_path: Path,
    pipeline: ClassificationPipeline,
    results: list[dict[str, Any]],
    action_verb: str,
    *,
    dry_run: bool,
    copy: bool,
    conflict_strategy: ConflictStrategy,
    date_prefix: bool,
    smart_rename: bool,
    skip_unclassifiable: bool = False,
    output_json: bool,
) -> tuple[bool, bool]:
    """Handle a single file in move command.

    Returns:
        Tuple of (success, skipped) - skipped is True if file was skipped due to skip_unclassifiable
    """
    from para_files.types import ClassificationSource

    if not _validate_file_exists(file_path):
        if output_json:
            results.append({"source_file": str(file_path), "error": "file validation failed"})
        return False, False

    try:
        # First classify to check if we should skip
        classification = pipeline.classify_file(file_path)

        # Skip unclassifiable files if requested
        if skip_unclassifiable and classification.confidence.source == ClassificationSource.DEFAULT:
            logger.info("Skipping unclassifiable file: %s", file_path)
            if output_json:
                results.append(
                    {
                        "source_file": str(file_path),
                        "skipped": True,
                        "reason": "unclassifiable",
                    }
                )
            else:
                typer.echo(f"  Skipped (unclassifiable): {file_path.name}")
            return True, True  # Success (not an error), but skipped

        result, move_result, success = _process_single_move(
            file_path,
            pipeline,
            dry_run=dry_run,
            copy=copy,
            conflict_strategy=conflict_strategy,
            date_prefix=date_prefix,
            smart_rename=smart_rename,
        )

        if output_json:
            target_dir = pipeline.get_target_path(result)
            results.append(_format_move_result_json(file_path, result, target_dir, move_result))
        else:
            _print_move_result(file_path, result, move_result, action_verb)

    except Exception:
        logger.exception("Failed to process %s", file_path)
        if output_json:
            results.append({"source_file": str(file_path), "error": "processing failed"})
        return False, False
    else:
        return success, False


def _cleanup_source_dirs(
    source_dirs: set[Path],
    *,
    dry_run: bool,
    output_json: bool,
) -> None:
    """Clean up empty directories in source locations after move."""
    from para_files.utils.cleanup import cleanup_empty_dirs

    for source_dir in source_dirs:
        if source_dir.exists():
            deleted = cleanup_empty_dirs(source_dir, dry_run=dry_run)
            if deleted and not output_json:
                typer.echo(f"  Cleaned up {len(deleted)} empty directories")


def _print_move_summary(
    success_count: int,
    skip_count: int,
    fail_count: int,
) -> None:
    """Print summary of move operation."""
    summary_parts = [f"{success_count} succeeded"]
    if skip_count:
        summary_parts.append(f"{skip_count} skipped")
    if fail_count:
        summary_parts.append(f"{fail_count} failed")
    typer.echo(f"\nSummary: {', '.join(summary_parts)}")


@app.command()
def move(
    files: Annotated[list[Path], typer.Argument(help="Path(s) to file(s) to classify and move")],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview the move without actually moving files"),
    ] = False,
    copy: Annotated[
        bool,
        typer.Option("--copy", "-c", help="Copy file instead of moving (preserve original)"),
    ] = False,
    conflict: Annotated[
        ConflictChoice,
        typer.Option(help="Strategy for handling existing files"),
    ] = ConflictChoice.rename,
    date_prefix: Annotated[
        bool,
        typer.Option("--date-prefix", "-d", help="Add date prefix (YYYY-MM-DD) to filename"),
    ] = False,
    smart_rename: Annotated[
        bool,
        typer.Option(
            "--smart-rename",
            "-s",
            help="Use intelligent naming from metadata (e.g., book titles from ISBN)",
        ),
    ] = False,
    skip_unclassifiable: Annotated[
        bool,
        typer.Option(
            "--skip-unclassifiable",
            help="Skip files that cannot be classified (default: move to 0_Inbox)",
        ),
    ] = False,
    cleanup_empty: Annotated[
        bool,
        typer.Option(
            "--cleanup-empty",
            help="Remove empty directories after moving files",
        ),
    ] = False,
    output_json: Annotated[
        bool, typer.Option("--json", "-j", help="Output result as JSON")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Classify and move one or more files to their PARA destinations."""
    setup_logging(verbose=verbose)
    config = _load_config_or_exit()

    if reference_tree:
        config.reference_tree_path = reference_tree

    pipeline = ClassificationPipeline(config)
    conflict_strategy = ConflictStrategy(conflict.value)
    results: list[dict[str, Any]] = []
    success_count = 0
    fail_count = 0
    skip_count = 0
    action_verb = (
        ("Would copy" if copy else "Would move") if dry_run else ("Copied" if copy else "Moved")
    )

    # Collect source directories for empty cleanup
    source_dirs: set[Path] = set()

    for file in files:
        resolved = file.resolve()
        source_dirs.add(resolved.parent)

        success, skipped = _handle_move_file(
            resolved,
            pipeline,
            results,
            action_verb,
            dry_run=dry_run,
            copy=copy,
            conflict_strategy=conflict_strategy,
            date_prefix=date_prefix,
            smart_rename=smart_rename,
            skip_unclassifiable=skip_unclassifiable,
            output_json=output_json,
        )
        if skipped:
            skip_count += 1
        elif success:
            success_count += 1
        else:
            fail_count += 1

    # Cleanup empty directories if requested (only for move, not copy)
    if cleanup_empty and not copy:
        _cleanup_source_dirs(source_dirs, dry_run=dry_run, output_json=output_json)

    if output_json:
        typer.echo(json.dumps(results, indent=2))
    elif len(files) > 1:
        _print_move_summary(success_count, skip_count, fail_count)


@app.command("add-issuer")
def add_issuer(
    issuer: Annotated[str, typer.Argument(help="Name of the issuer to add")],
    category: Annotated[
        str,
        typer.Option("--category", "-c", help="Category to add issuer to"),
    ],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
) -> None:
    """Add a new issuer to the reference tree."""
    from para_files.learner import RoutingLearner

    tree_path = _get_reference_tree_path(reference_tree)
    _ensure_tree_exists(tree_path)

    learner = RoutingLearner(tree_path)

    if category not in learner.list_issuer_categories():
        typer.echo(f"Creating new category: {category}")

    if learner.add_issuer(issuer, category):
        typer.echo(f"Added issuer '{issuer}' to category '{category}'")
    else:
        typer.echo(f"Issuer '{issuer}' already exists in '{category}'")


def _show_available_routes(learner: RoutingLearner) -> None:
    """Show available routes and exit."""
    typer.echo("Available routes:")
    for r in learner.list_routes():
        typer.echo(f"  - {r}")
    raise typer.Exit(1)


@app.command("add-utterance")
def add_utterance(
    route: Annotated[str, typer.Argument(help="Name of the route to update")],
    utterance: Annotated[str, typer.Argument(help="New utterance to add")],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
) -> None:
    """Add a new utterance to a route for better matching."""
    from para_files.learner import RoutingLearner

    tree_path = _get_reference_tree_path(reference_tree)
    _ensure_tree_exists(tree_path)
    learner = RoutingLearner(tree_path)

    if learner.add_utterance(route, utterance):
        typer.echo(f"Added utterance '{utterance}' to route '{route}'")
    elif learner.get_route_info(route) is None:
        typer.echo(f"Route '{route}' not found", err=True)
        _show_available_routes(learner)
    else:
        typer.echo(f"Utterance '{utterance}' already exists in route '{route}'")


def _print_route_with_utterances(learner: RoutingLearner, route_name: str) -> None:
    """Print route with its utterances."""
    route_info = learner.get_route_info(route_name)
    utterances = route_info.get("utterances", []) if route_info else []
    typer.echo(f"\n  {route_name}:")
    for utt in utterances[:MAX_UTTERANCES_SHOWN]:
        typer.echo(f"    - {utt}")
    if len(utterances) > MAX_UTTERANCES_SHOWN:
        remaining = len(utterances) - MAX_UTTERANCES_SHOWN
        typer.echo(f"    ... and {remaining} more")


@app.command("routes")
def list_routes(
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    show_utterances: Annotated[
        bool,
        typer.Option("--utterances", "-u", help="Show utterances for each route"),
    ] = False,
) -> None:
    """List all available routes in the reference tree."""
    from para_files.learner import RoutingLearner

    tree_path = _get_reference_tree_path(reference_tree)
    _ensure_tree_exists(tree_path)
    learner = RoutingLearner(tree_path)
    routes = learner.list_routes()

    if not routes:
        typer.echo("No routes found")
        return

    typer.echo(f"Available routes ({len(routes)}):")
    for route_name in routes:
        if show_utterances:
            _print_route_with_utterances(learner, route_name)
        else:
            typer.echo(f"  - {route_name}")


@app.command("issuers")
def list_issuers(
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
) -> None:
    """List all known issuers by category."""
    from para_files.learner import RoutingLearner

    tree_path = _get_reference_tree_path(reference_tree)
    _ensure_tree_exists(tree_path)
    learner = RoutingLearner(tree_path)
    known_issuers = learner.get_known_issuers()

    if not known_issuers:
        typer.echo("No issuers defined")
        return

    typer.echo("Known issuers by category:")
    for category, issuers in known_issuers.items():
        typer.echo(f"\n  {category}:")
        for issuer in issuers:
            typer.echo(f"    - {issuer}")


def _validate_file_or_exit(file_path: Path) -> None:
    """Validate file exists and is a file, exit on error."""
    if not file_path.exists():
        logger.error("File not found: %s", file_path)
        raise typer.Exit(1)
    if not file_path.is_file():
        logger.error("Not a file: %s", file_path)
        raise typer.Exit(1)


def _select_route_from_choice(choice: str, routes: list[str]) -> str | None:
    """Parse user route selection choice."""
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(routes):
            return routes[idx]
    elif choice in routes:
        return choice
    return None


def _handle_keyword_addition(learner: RoutingLearner, route: str) -> None:
    """Handle optional keyword addition during learning."""
    if not typer.confirm("Would you like to add a keyword to improve matching?", default=True):
        return

    keyword = typer.prompt("Enter keyword to add (from document content)")
    if keyword.strip():
        if learner.add_utterance(route, keyword.strip()):
            typer.echo(f"Added keyword '{keyword}' to route '{route}'")
        else:
            typer.echo("Keyword already exists or could not be added")


@app.command()
def learn(
    file: Annotated[Path, typer.Argument(help="Path to file to learn from")],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Interactive classification learning from a file."""
    from para_files.learner import RoutingLearner

    setup_logging(verbose=verbose)
    file_path = file.resolve()
    _validate_file_or_exit(file_path)

    config = _load_config_or_exit()
    if reference_tree:
        config.reference_tree_path = reference_tree

    pipeline = ClassificationPipeline(config)
    result = pipeline.classify_file(file_path)
    target_path = pipeline.get_target_path(result)

    _print_classification_result(file_path, result, target_path)

    if typer.confirm("\nIs this classification correct?", default=True):
        typer.echo("Classification confirmed. No changes needed.")
        return

    _ensure_tree_exists(config.reference_tree_path)
    learner = RoutingLearner(config.reference_tree_path)
    routes = learner.list_routes()

    typer.echo("\nAvailable routes:")
    for i, route_name in enumerate(routes, 1):
        typer.echo(f"  {i}. {route_name}")

    choice = typer.prompt("\nEnter route number or name (or 'skip' to cancel)", default="skip")
    if choice.lower() == "skip":
        typer.echo("Learning cancelled.")
        return

    correct_route = _select_route_from_choice(choice, routes)
    if correct_route is None:
        typer.echo(f"Invalid selection: {choice}", err=True)
        raise typer.Exit(1)

    typer.echo(f"\nSelected route: {correct_route}")
    _handle_keyword_addition(learner, correct_route)
    typer.echo("\nLearning complete!")


def _print_route_details(route: str, route_info: dict[str, Any]) -> None:
    """Print route details."""
    typer.echo(f"\nRoute: {route}")
    if "pattern" in route_info:
        typer.echo(f"   Pattern: {route_info['pattern']}")
    if "utterances" in route_info:
        typer.echo(f"   Utterances ({len(route_info['utterances'])}):")
        for utterance in route_info["utterances"]:
            typer.echo(f"     - {utterance}")
    else:
        typer.echo("   Utterances: (none)")


def _test_file_against_route(
    file_path: Path,
    expected_route: str,
    reference_tree: Path | None,
) -> None:
    """Test a file against an expected route."""
    typer.echo(f"\nTesting file: {file_path.name}")

    config = _load_config_or_exit()
    if reference_tree:
        config.reference_tree_path = reference_tree

    pipeline = ClassificationPipeline(config)
    result = pipeline.classify_file(file_path)

    typer.echo(f"   Classification: {result.category}")
    conf = result.confidence
    typer.echo(f"   Confidence: {conf.value:.0%} ({conf.source.value})")

    if not result.route_name:
        typer.echo("\n   No route matched (defaulted to inbox)")
    elif result.route_name == expected_route:
        typer.echo(f"   Matched route: {result.route_name}")
        typer.echo("\n   File matches this route!")
    else:
        typer.echo(f"   Matched route: {result.route_name}")
        typer.echo(f"\n   File matched different route: {result.route_name}")


@app.command("test-route")
def test_route(
    route: Annotated[str, typer.Argument(help="Name of the route to test")],
    file: Annotated[
        Path | None,
        typer.Option("--file", "-f", help="Optional file to test against the route"),
    ] = None,  # noqa: PT028
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,  # noqa: PT028
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,  # noqa: PT028
) -> None:
    """Test a route's configuration and optionally match a file against it."""
    from para_files.learner import RoutingLearner

    setup_logging(verbose=verbose)
    tree_path = _get_reference_tree_path(reference_tree)
    _ensure_tree_exists(tree_path)

    learner = RoutingLearner(tree_path)
    route_info = learner.get_route_info(route)

    if route_info is None:
        typer.echo(f"Route '{route}' not found", err=True)
        _show_available_routes(learner)
        raise typer.Exit(1)

    _print_route_details(route, route_info)

    if file is not None:
        file_path = file.resolve()
        _validate_file_or_exit(file_path)
        _test_file_against_route(file_path, route, reference_tree)


@app.command()
def scan(
    directory: Annotated[Path, typer.Argument(help="Directory to scan for files")],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", "-R", help="Scan subdirectories recursively"),
    ] = False,
    extensions: Annotated[
        str | None,
        typer.Option("--ext", "-e", help="Filter by extensions (comma-separated)"),
    ] = None,
    output_json: Annotated[
        bool, typer.Option("--json", "-j", help="Output results as JSON")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Scan a directory and preview file classifications without moving."""
    setup_logging(verbose=verbose)

    dir_path = directory.resolve()
    _validate_directory_or_exit(dir_path)

    config = _load_config_or_exit()
    if reference_tree:
        config.reference_tree_path = reference_tree

    ext_filter = _parse_extensions_filter(extensions)
    files = _discover_files(dir_path, recursive=recursive, ext_filter=ext_filter)

    if not files:
        typer.echo("No files found matching criteria")
        return

    pipeline = ClassificationPipeline(config)
    results: list[dict[str, Any]] = []
    stats: dict[str, int] = {}

    for file_path in files:
        file_result = _classify_file_for_scan(file_path, pipeline, stats, output_json=output_json)
        if file_result is not None:
            results.append(file_result)

    _print_scan_summary(dir_path, files, stats, results, output_json=output_json)


def _clean_junk_files(
    dir_path: Path,
    cleanup_logger: CleanupLogger,
    results: dict[str, Any],
    *,
    recursive: bool,
    dry_run: bool,
    output_json: bool,
) -> None:
    """Clean junk files from directory."""
    from para_files.utils.cleanup import cleanup_junk, scan_for_junk

    junk_files, junk_dirs = scan_for_junk(dir_path, recursive=recursive)

    if not junk_files and not junk_dirs:
        return

    deleted_files, deleted_dirs = cleanup_junk(dir_path, recursive=recursive, dry_run=dry_run)

    for f in deleted_files:
        cleanup_logger.log_deleted(f, "junk_file", f.name, dry_run=dry_run)
        results["deleted_files"].append(str(f))

    for d in deleted_dirs:
        cleanup_logger.log_deleted(d, "junk_dir", d.name, dry_run=dry_run)
        results["deleted_dirs"].append(str(d))

    if not output_json:
        action = "Would delete" if dry_run else "Deleted"
        if deleted_files:
            typer.echo(f"  {action} {len(deleted_files)} junk files")
        if deleted_dirs:
            typer.echo(f"  {action} {len(deleted_dirs)} junk directories")


def _clean_nfo_files(
    dir_path: Path,
    cleanup_logger: CleanupLogger,
    results: dict[str, Any],
    *,
    recursive: bool,
    dry_run: bool,
    output_json: bool,
) -> None:
    """Clean .nfo files from directory."""
    nfo_files = list(dir_path.rglob("*.nfo")) if recursive else list(dir_path.glob("*.nfo"))
    deleted_count = 0

    for nfo_file in nfo_files:
        if dry_run:
            logger.info("[DRY-RUN] Would delete NFO: %s", nfo_file)
            deleted_count += 1
        else:
            try:
                nfo_file.unlink()
                logger.info("Deleted NFO: %s", nfo_file)
                deleted_count += 1
            except OSError:
                logger.exception("Failed to delete NFO %s", nfo_file)
                continue

        cleanup_logger.log_deleted(nfo_file, "nfo", "NFO file cleanup", dry_run=dry_run)
        results["deleted_nfo"].append(str(nfo_file))

    if deleted_count and not output_json:
        action = "Would delete" if dry_run else "Deleted"
        typer.echo(f"  {action} {deleted_count} NFO files")


def _clean_empty_directories(
    dir_path: Path,
    cleanup_logger: CleanupLogger,
    results: dict[str, Any],
    *,
    dry_run: bool,
    output_json: bool,
) -> None:
    """Clean empty directories from path."""
    from para_files.utils.cleanup import cleanup_empty_dirs

    deleted_empty = cleanup_empty_dirs(dir_path, dry_run=dry_run)

    for d in deleted_empty:
        cleanup_logger.log_deleted(d, "empty_dir", "Empty directory", dry_run=dry_run)
        results["deleted_dirs"].append(str(d))

    if deleted_empty and not output_json:
        action = "Would delete" if dry_run else "Deleted"
        typer.echo(f"  {action} {len(deleted_empty)} empty directories")


@app.command()
def clean(
    directory: Annotated[Path, typer.Argument(help="Directory to clean")],
    recursive: Annotated[
        bool,
        typer.Option("--recursive", "-R", help="Clean subdirectories recursively"),
    ] = True,
    junk: Annotated[
        bool,
        typer.Option("--junk", help="Delete Apple/Windows temp files (.DS_Store, Thumbs.db, etc.)"),
    ] = True,
    nfo: Annotated[
        bool,
        typer.Option("--nfo", help="Delete .nfo files after using them as hints"),
    ] = False,
    empty_dirs: Annotated[
        bool,
        typer.Option("--empty-dirs", help="Delete empty directories"),
    ] = True,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview deletions without actually deleting"),
    ] = False,
    output_json: Annotated[
        bool, typer.Option("--json", "-j", help="Output results as JSON")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Clean junk files and empty directories from a location.

    By default, removes Apple/Windows temp files and empty directories.
    Use --nfo to also remove .nfo files after classification.
    """
    from para_files.utils.cleanup_log import CleanupLogger, get_default_log_path

    setup_logging(verbose=verbose)
    config = _load_config_or_exit()

    dir_path = directory.resolve()
    _validate_directory_or_exit(dir_path)

    # Setup audit log
    log_path = get_default_log_path(Path(config.para_root).expanduser())
    cleanup_logger = CleanupLogger(log_path if not dry_run else None)

    results: dict[str, Any] = {
        "directory": str(dir_path),
        "dry_run": dry_run,
        "deleted_files": [],
        "deleted_dirs": [],
        "deleted_nfo": [],
    }

    if not output_json:
        mode = "[DRY-RUN] " if dry_run else ""
        typer.echo(f"{mode}Cleaning {dir_path}")

    # Clean junk files
    if junk:
        _clean_junk_files(
            dir_path,
            cleanup_logger,
            results,
            recursive=recursive,
            dry_run=dry_run,
            output_json=output_json,
        )

    # Clean .nfo files
    if nfo:
        _clean_nfo_files(
            dir_path,
            cleanup_logger,
            results,
            recursive=recursive,
            dry_run=dry_run,
            output_json=output_json,
        )

    # Clean empty directories
    if empty_dirs:
        _clean_empty_directories(
            dir_path, cleanup_logger, results, dry_run=dry_run, output_json=output_json
        )

    # Write audit log
    if not dry_run:
        cleanup_logger.write_log()

    # Summary
    total_deleted = (
        len(results["deleted_files"]) + len(results["deleted_dirs"]) + len(results["deleted_nfo"])
    )

    if output_json:
        typer.echo(json.dumps(results, indent=2))
    elif total_deleted == 0:
        typer.echo("  Nothing to clean")
    else:
        action = "would be deleted" if dry_run else "deleted"
        typer.echo(f"\nTotal: {total_deleted} items {action}")


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
        typer.Option("--dry-run", "-n", help="Preview folders without creating them"),
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Initialize PARA folder structure from reference tree."""
    import yaml

    setup_logging(verbose=verbose)

    config = _load_config_or_exit()
    para_root = destination or config.para_root
    tree_path = reference_tree or config.reference_tree_path
    _ensure_tree_exists(tree_path)

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


@app.command()
def tree(
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    validate: Annotated[
        bool,
        typer.Option("--validate", help="Validate reference tree structure"),
    ] = False,
    show_issuers: Annotated[
        bool,
        typer.Option("--issuers", "-i", help="Show known issuers"),
    ] = False,
    show_rules: Annotated[
        bool,
        typer.Option("--rules", help="Show routing rules"),
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Show or validate the reference tree structure."""
    import yaml

    setup_logging(verbose=verbose)

    tree_path = _get_reference_tree_path(reference_tree)
    _ensure_tree_exists(tree_path)

    with tree_path.open() as f:
        tree_data = yaml.safe_load(f)

    version = tree_data.get("version", "unknown")
    generated = tree_data.get("generated", "unknown")
    typer.echo(f"\U0001f4da Reference Tree: {tree_path}")
    typer.echo(f"   Version: {version} | Generated: {generated}")

    errors: list[str] = []
    warnings: list[str] = []

    route_count, utterance_count = _show_tree_sections(
        tree_data, validate=validate, errors=errors, warnings=warnings
    )

    if show_rules:
        _show_routing_rules(tree_data)

    if show_issuers:
        _show_known_issuers(tree_data, verbose=verbose)

    typer.echo(f"\n\U0001f4ca Summary: {route_count} routes, {utterance_count} utterances")

    if validate:
        _print_validation_results(errors, warnings)


@app.command()
def config(
    show: Annotated[
        bool,
        typer.Option("--show", "-s", help="Show current configuration values"),
    ] = True,
    path: Annotated[
        bool,
        typer.Option("--path", "-p", help="Show reference tree path"),
    ] = False,
) -> None:
    """Show configuration (loaded from reference tree YAML)."""
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


@app.callback(invoke_without_command=True)
def main(
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


def cli() -> None:
    """CLI entry point for console script."""
    app()


if __name__ == "__main__":
    cli()
