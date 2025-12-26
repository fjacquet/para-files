"""Main entry point for the PARA Files classification system.

CLI for classifying files using the 5-signal pipeline.
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from para_files.config import load_config
from para_files.mover import ConflictStrategy, move_classified_file
from para_files.pipeline import ClassificationPipeline


logger = logging.getLogger(__name__)

# Create the Typer app
app = typer.Typer(
    name="para-files",
    help="Classify files using the PARA method with MLX-powered semantic routing.",
    add_completion=True,
)


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

    # Load configuration
    try:
        config = load_config()
    except ValidationError:
        logger.exception("Configuration error")
        raise typer.Exit(1) from None

    # Override config with CLI args if provided
    if reference_tree:
        config.reference_tree_path = reference_tree

    # Create pipeline once for all files
    pipeline = ClassificationPipeline(config)

    results = []
    for file in files:
        file_path = file.resolve()

        if not file_path.exists():
            logger.warning("File not found: %s", file_path)
            continue

        if not file_path.is_file():
            logger.warning("Not a file: %s", file_path)
            continue

        try:
            result = pipeline.classify_file(file_path)
            target_path = pipeline.get_target_path(result)

            if output_json:
                output = {
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
                results.append(output)
            else:
                typer.echo(f"\n📄 {file_path.name}")
                typer.echo(f"   Category: {result.category}")
                conf = result.confidence
                typer.echo(f"   Confidence: {conf.value:.0%} ({conf.source.value})")
                typer.echo(f"   Target: {target_path}")
                if result.route_name:
                    typer.echo(f"   Route: {result.route_name}")
        except Exception:
            logger.exception("Failed to classify %s", file_path)
            if output_json:
                results.append({"source_file": str(file_path), "error": "classification failed"})

    if output_json:
        typer.echo(json.dumps(results, indent=2))


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
    output_json: Annotated[
        bool, typer.Option("--json", "-j", help="Output result as JSON")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Classify and move one or more files to their PARA destinations."""
    setup_logging(verbose=verbose)

    # Load configuration
    try:
        config = load_config()
    except ValidationError:
        logger.exception("Configuration error")
        raise typer.Exit(1) from None

    # Override config with CLI args if provided
    if reference_tree:
        config.reference_tree_path = reference_tree

    # Create pipeline once for all files
    pipeline = ClassificationPipeline(config)

    # Convert conflict choice to strategy
    conflict_strategy = ConflictStrategy(conflict.value)

    # Track results
    results = []
    success_count = 0
    fail_count = 0

    action_verb = "Would move" if dry_run else "Moved"
    if copy:
        action_verb = "Would copy" if dry_run else "Copied"

    for file in files:
        file_path = file.resolve()

        if not file_path.exists():
            logger.warning("File not found: %s", file_path)
            fail_count += 1
            if output_json:
                results.append({"source_file": str(file_path), "error": "file not found"})
            continue

        if not file_path.is_file():
            logger.warning("Not a file: %s", file_path)
            fail_count += 1
            if output_json:
                results.append({"source_file": str(file_path), "error": "not a file"})
            continue

        try:
            # Classify and get target
            result = pipeline.classify_file(file_path)
            target_dir = pipeline.get_target_path(result)

            # Move the file
            move_result = move_classified_file(
                file_path,
                target_dir,
                dry_run=dry_run,
                copy_mode=copy,
                conflict_strategy=conflict_strategy,
                add_date_prefix=date_prefix,
            )

            if output_json:
                output = {
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
                results.append(output)
            elif move_result.success:
                typer.echo(f"{action_verb}: {file_path.name}")
                typer.echo(f"  -> {move_result.destination}")
                conf = result.confidence
                typer.echo(f"  Classification: {result.category} ({conf.value:.0%})")
            else:
                typer.echo(f"Failed: {file_path.name} - {move_result.message}", err=True)

            if move_result.success:
                success_count += 1
            else:
                fail_count += 1

        except Exception:
            logger.exception("Failed to process %s", file_path)
            fail_count += 1
            if output_json:
                results.append({"source_file": str(file_path), "error": "processing failed"})

    # Output summary
    if output_json:
        typer.echo(json.dumps(results, indent=2))
    elif len(files) > 1:
        typer.echo(f"\nSummary: {success_count} succeeded, {fail_count} failed")


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

    # Determine reference tree path
    tree_path = reference_tree
    if tree_path is None:
        try:
            config = load_config()
            tree_path = config.reference_tree_path
        except ValidationError:
            tree_path = Path("personal_file_tree.yaml")

    if not tree_path.exists():
        typer.echo(f"Reference tree not found: {tree_path}", err=True)
        raise typer.Exit(1)

    learner = RoutingLearner(tree_path)

    # Show available categories if needed
    categories = learner.list_issuer_categories()
    if category not in categories:
        typer.echo(f"Creating new category: {category}")

    if learner.add_issuer(issuer, category):
        typer.echo(f"Added issuer '{issuer}' to category '{category}'")
    else:
        typer.echo(f"Issuer '{issuer}' already exists in '{category}'")


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

    # Determine reference tree path
    tree_path = reference_tree
    if tree_path is None:
        try:
            config = load_config()
            tree_path = config.reference_tree_path
        except ValidationError:
            tree_path = Path("personal_file_tree.yaml")

    if not tree_path.exists():
        typer.echo(f"Reference tree not found: {tree_path}", err=True)
        raise typer.Exit(1)

    learner = RoutingLearner(tree_path)

    if learner.add_utterance(route, utterance):
        typer.echo(f"Added utterance '{utterance}' to route '{route}'")
    else:
        # Check if route exists
        if learner.get_route_info(route) is None:
            typer.echo(f"Route '{route}' not found", err=True)
            typer.echo("Available routes:")
            for r in learner.list_routes():
                typer.echo(f"  - {r}")
            raise typer.Exit(1)
        typer.echo(f"Utterance '{utterance}' already exists in route '{route}'")


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

    # Determine reference tree path
    tree_path = reference_tree
    if tree_path is None:
        try:
            config = load_config()
            tree_path = config.reference_tree_path
        except ValidationError:
            tree_path = Path("personal_file_tree.yaml")

    if not tree_path.exists():
        typer.echo(f"Reference tree not found: {tree_path}", err=True)
        raise typer.Exit(1)

    learner = RoutingLearner(tree_path)
    routes = learner.list_routes()

    if not routes:
        typer.echo("No routes found")
        return

    max_utterances_shown = 5
    typer.echo(f"Available routes ({len(routes)}):")
    for route_name in routes:
        if show_utterances:
            route_info = learner.get_route_info(route_name)
            utterances = route_info.get("utterances", []) if route_info else []
            typer.echo(f"\n  {route_name}:")
            for utt in utterances[:max_utterances_shown]:
                typer.echo(f"    - {utt}")
            if len(utterances) > max_utterances_shown:
                remaining = len(utterances) - max_utterances_shown
                typer.echo(f"    ... and {remaining} more")
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

    # Determine reference tree path
    tree_path = reference_tree
    if tree_path is None:
        try:
            config = load_config()
            tree_path = config.reference_tree_path
        except ValidationError:
            tree_path = Path("personal_file_tree.yaml")

    if not tree_path.exists():
        typer.echo(f"Reference tree not found: {tree_path}", err=True)
        raise typer.Exit(1)

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

    if not dir_path.exists():
        logger.error("Directory not found: %s", dir_path)
        raise typer.Exit(1)

    if not dir_path.is_dir():
        logger.error("Not a directory: %s", dir_path)
        raise typer.Exit(1)

    # Load configuration
    try:
        config = load_config()
    except ValidationError:
        logger.exception("Configuration error")
        raise typer.Exit(1) from None

    # Override config with CLI args if provided
    if reference_tree:
        config.reference_tree_path = reference_tree

    # Parse extensions filter
    ext_filter: set[str] | None = None
    if extensions:
        ext_filter = {
            ext.strip().lower() if ext.startswith(".") else f".{ext.strip().lower()}"
            for ext in extensions.split(",")
        }

    # Find files
    files = list(dir_path.rglob("*")) if recursive else list(dir_path.glob("*"))

    # Filter to only files (not directories)
    files = [f for f in files if f.is_file()]

    # Apply extension filter
    if ext_filter:
        files = [f for f in files if f.suffix.lower() in ext_filter]

    if not files:
        typer.echo("No files found matching criteria")
        return

    # Create pipeline once for all files
    pipeline = ClassificationPipeline(config)

    results = []
    stats: dict[str, int] = {}

    for file_path in sorted(files):
        try:
            result = pipeline.classify_file(file_path)
            target_path = pipeline.get_target_path(result)

            # Track stats by source
            source = result.confidence.source.value
            stats[source] = stats.get(source, 0) + 1

            if output_json:
                output = {
                    "source_file": str(file_path),
                    "filename": file_path.name,
                    "category": result.category,
                    "confidence": result.confidence.value,
                    "source": source,
                    "target_path": str(target_path),
                }
                if result.route_name:
                    output["route_name"] = result.route_name
                results.append(output)
            else:
                confidence_pct = f"{result.confidence.value:.0%}"
                typer.echo(f"📄 {file_path.name}")
                typer.echo(f"   → {result.category} ({confidence_pct} {source})")

        except Exception as e:
            logger.warning("Failed to classify %s: %s", file_path.name, e)
            if output_json:
                results.append(
                    {
                        "source_file": str(file_path),
                        "filename": file_path.name,
                        "error": str(e),
                    }
                )

    if output_json:
        output_data = {
            "directory": str(dir_path),
            "total_files": len(files),
            "stats": stats,
            "results": results,
        }
        typer.echo(json.dumps(output_data, indent=2))
    else:
        typer.echo(f"\n📊 Summary: {len(files)} files scanned")
        for source, count in sorted(stats.items(), key=lambda x: -x[1]):
            typer.echo(f"   {source}: {count}")


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
    """Initialize PARA folder structure from reference tree.

    Creates the main PARA directories (0_Inbox, 1_Projects, 2_Areas,
    3_Resources, 4_Archives) and optionally subfolders based on the
    reference tree routes.
    """
    import yaml

    setup_logging(verbose=verbose)

    # Load configuration
    try:
        config = load_config()
    except ValidationError:
        logger.exception("Configuration error")
        raise typer.Exit(1) from None

    # Determine destination
    para_root = destination or config.para_root

    # Determine reference tree path
    tree_path = reference_tree or config.reference_tree_path

    if not tree_path.exists():
        typer.echo(f"Reference tree not found: {tree_path}", err=True)
        raise typer.Exit(1)

    # Load reference tree
    with tree_path.open() as f:
        tree_data = yaml.safe_load(f)

    # Main PARA directories
    main_dirs = [
        ("0_Inbox", tree_data.get("inbox", {}).get("description", "Inbox - temporary files")),
        ("1_Projects", "Active projects with deadlines"),
        ("2_Areas", "Ongoing responsibilities"),
        ("3_Resources", "Reference materials"),
        ("4_Archives", "Completed items"),
    ]

    created_dirs: list[Path] = []
    existing_dirs: list[Path] = []

    # Create main directories
    for dir_name, _description in main_dirs:
        dir_path = para_root / dir_name
        if dry_run:
            if dir_path.exists():
                typer.echo(f"  [exists] {dir_path}")
                existing_dirs.append(dir_path)
            else:
                typer.echo(f"  [create] {dir_path}")
                created_dirs.append(dir_path)
        elif dir_path.exists():
            logger.debug("Directory exists: %s", dir_path)
            existing_dirs.append(dir_path)
        else:
            dir_path.mkdir(parents=True, exist_ok=True)
            typer.echo(f"  Created: {dir_path}")
            created_dirs.append(dir_path)

    # Optionally create subfolders from routes
    if create_subfolders:
        subfolder_patterns: list[str] = []

        # Extract patterns from routes sections
        for section in ["projects", "areas", "resources", "archives"]:
            section_data = tree_data.get(section, {})
            routes = section_data.get("routes", [])
            for route in routes:
                pattern = route.get("pattern", "")
                if pattern:
                    # Extract static parts (no placeholders like {year})
                    static_path = pattern.split("{")[0].rstrip("/")
                    if static_path and static_path not in subfolder_patterns:
                        subfolder_patterns.append(static_path)

        # Create subfolders
        for pattern in sorted(subfolder_patterns):
            subfolder_path = para_root / pattern
            if dry_run:
                if subfolder_path.exists():
                    typer.echo(f"  [exists] {subfolder_path}")
                    existing_dirs.append(subfolder_path)
                else:
                    typer.echo(f"  [create] {subfolder_path}")
                    created_dirs.append(subfolder_path)
            elif subfolder_path.exists():
                logger.debug("Subfolder exists: %s", subfolder_path)
                existing_dirs.append(subfolder_path)
            else:
                subfolder_path.mkdir(parents=True, exist_ok=True)
                typer.echo(f"  Created: {subfolder_path}")
                created_dirs.append(subfolder_path)

    # Summary
    if dry_run:
        to_create = len(created_dirs)
        exists = len(existing_dirs)
        typer.echo(f"\n📁 Dry run: {to_create} folders to create, {exists} already exist")
    else:
        typer.echo(f"\n✅ PARA structure initialized at {para_root}")
        typer.echo(f"   Created: {len(created_dirs)} folders")
        typer.echo(f"   Existing: {len(existing_dirs)} folders")


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
    """Show or validate the reference tree structure.

    Displays the PARA folder structure, routes, and known issuers
    defined in the reference tree YAML file.
    """
    import yaml

    setup_logging(verbose=verbose)

    # Determine reference tree path
    tree_path = reference_tree
    if tree_path is None:
        try:
            config = load_config()
            tree_path = config.reference_tree_path
        except ValidationError:
            tree_path = Path("personal_file_tree.yaml")

    if not tree_path.exists():
        typer.echo(f"Reference tree not found: {tree_path}", err=True)
        raise typer.Exit(1)

    # Load reference tree
    with tree_path.open() as f:
        tree_data = yaml.safe_load(f)

    version = tree_data.get("version", "unknown")
    generated = tree_data.get("generated", "unknown")
    typer.echo(f"📚 Reference Tree: {tree_path}")
    typer.echo(f"   Version: {version} | Generated: {generated}")

    errors: list[str] = []
    warnings: list[str] = []

    # Show main sections
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

        typer.echo(f"\n📂 {path}")

        # Count utterances and show routes
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

            typer.echo(f"   └── {name}: {pattern} ({len(utts)} utterances)")

    # Show routing rules
    if show_rules:
        rules = tree_data.get("routing_rules", {})
        if rules:
            typer.echo("\n⚙️  Routing Rules:")
            for rule_name, rule_data in rules.items():
                dest = rule_data.get("destination", "N/A")
                exts = rule_data.get("extensions", [])
                patterns = rule_data.get("patterns", [])
                typer.echo(f"   └── {rule_name}:")
                max_show = 5
                if exts:
                    ext_str = ", ".join(exts[:max_show])
                    suffix = "..." if len(exts) > max_show else ""
                    typer.echo(f"       Extensions: {ext_str}{suffix}")
                if patterns:
                    pat_str = ", ".join(patterns[:3])
                    suffix = "..." if len(patterns) > 3 else ""
                    typer.echo(f"       Patterns: {pat_str}{suffix}")
                typer.echo(f"       → {dest}")

    # Show known issuers
    if show_issuers:
        known_issuers = tree_data.get("known_issuers", {})
        if known_issuers:
            typer.echo("\n🏢 Known Issuers:")
            issuer_count = 0
            for category, category_data in known_issuers.items():
                issuers = category_data.get("issuers", [])
                issuer_count += len(issuers)
                pattern = category_data.get("pattern", "")
                typer.echo(f"   └── {category}: {len(issuers)} issuers → {pattern}")
                if verbose:
                    for issuer in issuers:
                        typer.echo(f"       - {issuer}")
            typer.echo(f"\n   Total: {issuer_count} issuers across {len(known_issuers)} categories")

    # Summary
    typer.echo(f"\n📊 Summary: {route_count} routes, {utterance_count} utterances")

    # Validation results
    if validate:
        if errors:
            typer.echo("\n❌ Errors:", err=True)
            for error in errors:
                typer.echo(f"   - {error}", err=True)

        if warnings:
            typer.echo("\n⚠️  Warnings:")
            for warning in warnings:
                typer.echo(f"   - {warning}")

        if not errors and not warnings:
            typer.echo("\n✅ Validation passed!")
        elif errors:
            raise typer.Exit(1)


@app.command()
def config(
    show: Annotated[
        bool,
        typer.Option("--show", "-s", help="Show current configuration values"),
    ] = True,
    init: Annotated[
        bool,
        typer.Option("--init", "-i", help="Create config directory and example file"),
    ] = False,
    path: Annotated[
        bool,
        typer.Option("--path", "-p", help="Show config file path"),
    ] = False,
) -> None:
    """Show or initialize configuration."""
    from para_files.config import DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE

    if path:
        typer.echo(f"Config file: {DEFAULT_CONFIG_FILE}")
        typer.echo(f"  Exists: {DEFAULT_CONFIG_FILE.exists()}")
        return

    if init:
        # Create config directory
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        typer.echo(f"Created config directory: {DEFAULT_CONFIG_DIR}")

        if not DEFAULT_CONFIG_FILE.exists():
            # Create example config file
            example_config = '''# para-files configuration
# See: uv run para-files config --show

# PARA root directory
para_root = "~/Documents/PARA"

# Reference tree file (relative to current dir or absolute)
# reference_tree_path = "personal_file_tree.yaml"

# Content extraction settings
# content_preview_chars = 2000

[mlx]
# MLX embedding model from mlx-embedding-models registry
model_name = "nomic-text-v1.5"
# Minimum similarity score (0.0-1.0)
score_threshold = 0.75

[llm]
# Enable LLM fallback for ambiguous classifications
enabled = false
# LLM model identifier for litellm
# model = "ollama/qwen2.5:1.5b"
# API base URL for Ollama
# api_base = "http://localhost:11434"
'''
            DEFAULT_CONFIG_FILE.write_text(example_config)
            typer.echo(f"Created example config: {DEFAULT_CONFIG_FILE}")
        else:
            typer.echo(f"Config file already exists: {DEFAULT_CONFIG_FILE}")
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
            typer.echo(f"\nConfig file: {DEFAULT_CONFIG_FILE}")
            typer.echo(f"  Exists: {DEFAULT_CONFIG_FILE.exists()}")
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
