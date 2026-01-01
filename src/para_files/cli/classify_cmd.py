"""Classify command for para-files CLI.

This module provides the 'classify' command which uses the 5-signal
classification pipeline to categorize files according to the PARA method.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Annotated, Any

import typer
from loguru import logger

from para_files.cli.app import app
from para_files.cli.shared import (
    expand_paths_to_files,
    format_result_json,
    load_config_or_exit,
    parse_extensions_filter,
    print_classification_result,
    setup_logging,
)
from para_files.pipeline import ClassificationPipeline
from para_files.utils.validation import validate_file_exists


def _classify_single_file(
    file_path: Path,
    pipeline: ClassificationPipeline,
) -> dict[str, Any]:
    """Classify a single file and return result dict (for parallel processing).

    This function is designed to be called from a ThreadPoolExecutor.
    It handles its own error handling and returns a dict with either
    the result or an error message.

    Args:
        file_path: Path to the file to classify.
        pipeline: The classification pipeline to use.

    Returns:
        Dictionary containing either the classification result or an error.
    """
    if not validate_file_exists(file_path):
        return {"source_file": str(file_path), "error": "file not found"}

    try:
        result = pipeline.classify_file(file_path)
        target_path = pipeline.get_target_path(result)
        return format_result_json(file_path, result, target_path)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to classify {}: {}", file_path, e)
        return {"source_file": str(file_path), "error": "classification failed"}


def _print_parallel_result(file_path: Path, result_dict: dict[str, Any]) -> None:
    """Print classification result from parallel processing.

    Displays the classification result for a single file that was
    processed in parallel mode.

    Args:
        file_path: Path to the classified file.
        result_dict: Dictionary containing the classification result or error.
    """
    if "error" not in result_dict:
        typer.echo(f"\n📄 {file_path.name}")
        typer.echo(f"   Category: {result_dict['category']}")
        conf = result_dict["confidence"]
        typer.echo(f"   Confidence: {conf:.0%} ({result_dict['source']})")
        typer.echo(f"   Target: {result_dict['target_path']}")
    else:
        typer.echo(f"\n⚠️ {file_path.name}: {result_dict.get('error', 'unknown error')}")


def _classify_files_parallel(
    expanded_files: list[Path],
    pipeline: ClassificationPipeline,
    max_workers: int,
    *,
    output_json: bool,
) -> list[dict[str, Any]]:
    """Classify files in parallel using ThreadPoolExecutor.

    Processes multiple files concurrently for improved performance
    when classifying large numbers of files.

    Args:
        expanded_files: List of file paths to classify.
        pipeline: The classification pipeline to use.
        max_workers: Maximum number of concurrent workers.
        output_json: If True, suppress console output (for JSON mode).

    Returns:
        List of classification result dictionaries.
    """
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_classify_single_file, f, pipeline): f for f in expanded_files}
        for future in as_completed(futures):
            file_path = futures[future]
            result_dict = future.result()
            results.append(result_dict)
            if not output_json:
                _print_parallel_result(file_path, result_dict)
    return results


def _classify_files_sequential(
    expanded_files: list[Path],
    pipeline: ClassificationPipeline,
    *,
    output_json: bool,
) -> list[dict[str, Any]]:
    """Classify files sequentially (original behavior).

    Processes files one at a time. Used when max_workers is 1 or
    there is only a single file to process.

    Args:
        expanded_files: List of file paths to classify.
        pipeline: The classification pipeline to use.
        output_json: If True, collect results for JSON output.

    Returns:
        List of classification result dictionaries.
    """
    results: list[dict[str, Any]] = []
    for file_path in expanded_files:
        if not validate_file_exists(file_path):
            continue

        try:
            result = pipeline.classify_file(file_path)
            target_path = pipeline.get_target_path(result)

            if output_json:
                results.append(format_result_json(file_path, result, target_path))
            else:
                print_classification_result(file_path, result, target_path)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to classify {}", file_path)
            if output_json:
                results.append({"source_file": str(file_path), "error": "classification failed"})
    return results


@app.command()
def classify(
    files: Annotated[
        list[Path], typer.Argument(help="Path(s) to file(s) or directory to classify")
    ],
    reference_tree: Annotated[
        Path | None,
        typer.Option("--reference-tree", "-r", help="Path to reference tree YAML file"),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", "-R", help="Process directories recursively"),
    ] = False,
    extensions: Annotated[
        str | None,
        typer.Option("--ext", "-e", help="Filter by extensions (comma-separated)"),
    ] = None,
    output_json: Annotated[
        bool, typer.Option("--json", "-j", help="Output result as JSON")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
) -> None:
    """Classify one or more files using the PARA method.

    Uses a 5-signal classification pipeline to determine the appropriate
    PARA category for each file:
    1. Validated DB - Manual mappings from user feedback
    2. Rules Engine - Glob patterns on filename/path
    3. Book Detector - PDF book detection via ISBN/metadata
    4. Domain KB - Known issuer to category mappings
    5. Semantic Router - MLX embedding similarity
    """
    setup_logging(verbose=verbose)
    config = load_config_or_exit()

    if reference_tree:
        config.reference_tree_path = reference_tree

    # Expand directories to file lists
    ext_filter = parse_extensions_filter(extensions)
    expanded_files, _ = expand_paths_to_files(files, recursive=recursive, ext_filter=ext_filter)

    if not expanded_files:
        typer.echo("No files found matching criteria")
        return

    pipeline = ClassificationPipeline(config)
    max_workers = config.max_workers

    # Use parallel or sequential processing based on max_workers
    if max_workers > 1 and len(expanded_files) > 1:
        results = _classify_files_parallel(
            expanded_files, pipeline, max_workers, output_json=output_json
        )
    else:
        results = _classify_files_sequential(expanded_files, pipeline, output_json=output_json)

    if output_json:
        typer.echo(json.dumps(results, indent=2))
