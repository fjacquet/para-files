"""Scan command for para-files CLI.

This module provides the 'scan' command which previews file classifications
without actually moving any files.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Annotated, Any

import typer

from para_files.cli.app import app
from para_files.cli.classify_cmd import _classify_single_file
from para_files.cli.shared import (
    discover_files,
    load_config_or_exit,
    parse_extensions_filter,
    setup_logging,
    validate_directory_or_exit,
)
from para_files.pipeline import ClassificationPipeline


logger = logging.getLogger(__name__)


def _classify_file_for_scan(
    file_path: Path,
    pipeline: ClassificationPipeline,
    stats: dict[str, int],
    *,
    output_json: bool,
) -> dict[str, Any] | None:
    """Classify a single file for scan command.

    Processes a file and updates statistics, optionally printing
    results to the console.

    Args:
        file_path: Path to the file to classify.
        pipeline: The classification pipeline.
        stats: Dictionary to update with classification source counts.
        output_json: If True, return dict for JSON output.

    Returns:
        Classification result dict if output_json is True, else None.
    """
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
        typer.echo(f"📄 {file_path.name}")
        typer.echo(f"   → {result.category} ({confidence_pct} {source})")
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
    """Print scan summary.

    Displays a summary of the scan operation, either as JSON or
    formatted console output.

    Args:
        dir_path: The scanned directory.
        files: List of files that were scanned.
        stats: Classification source statistics.
        results: List of classification results.
        output_json: If True, output as JSON.
    """
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
    """Scan a directory and preview file classifications without moving.

    Classifies all files in the specified directory using the 5-signal
    pipeline and displays the results. Useful for previewing what would
    happen before running the 'move' command.
    """
    setup_logging(verbose=verbose)

    dir_path = directory.resolve()
    validate_directory_or_exit(dir_path)

    config = load_config_or_exit()
    if reference_tree:
        config.reference_tree_path = reference_tree

    ext_filter = parse_extensions_filter(extensions)
    files = discover_files(dir_path, recursive=recursive, ext_filter=ext_filter)

    if not files:
        typer.echo("No files found matching criteria")
        return

    pipeline = ClassificationPipeline(config)
    results: list[dict[str, Any]] = []
    stats: dict[str, int] = {}
    max_workers = config.max_workers

    # Use parallel processing if max_workers > 1
    if max_workers > 1 and len(files) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_classify_single_file, f, pipeline): f for f in files}
            for future in as_completed(futures):
                file_path = futures[future]
                result_dict = future.result()
                if "error" not in result_dict:
                    # Update stats
                    source = result_dict.get("source", "unknown")
                    stats[source] = stats.get(source, 0) + 1
                    results.append(result_dict)
                    # Print result immediately if not JSON mode
                    if not output_json:
                        conf_pct = f"{result_dict['confidence']:.0%}"
                        typer.echo(f"📄 {file_path.name}")
                        typer.echo(f"   → {result_dict['category']} ({conf_pct} {source})")
                elif not output_json:
                    typer.echo(f"⚠️ {file_path.name}: {result_dict.get('error')}")
    else:
        # Sequential processing (original behavior)
        for file_path in files:
            file_result = _classify_file_for_scan(
                file_path, pipeline, stats, output_json=output_json
            )
            if file_result is not None:
                results.append(file_result)

    _print_scan_summary(dir_path, files, stats, results, output_json=output_json)
