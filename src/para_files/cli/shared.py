"""Shared utilities and helpers for CLI commands.

This module contains helper functions, enums, and utilities that are shared
across multiple CLI commands. These were extracted from main.py to promote
code reuse and maintainability.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer
from loguru import logger
from pydantic import ValidationError

from para_files.config import DEFAULT_REFERENCE_TREE, load_config
from para_files.logging import setup_logging as _setup_logging
from para_files.utils.validation import (
    validate_directory_exists,
    validate_file_exists,
)


if TYPE_CHECKING:
    from para_files.config import Config, LoggingConfig
    from para_files.types import ClassificationResult


# Constants used across multiple commands
MAX_PATTERNS_SHOWN = 3
MAX_UTTERANCES_SHOWN = 5


class ConflictChoice(str, Enum):
    """CLI choices for conflict strategy.

    Defines the available options for handling file conflicts when
    moving files to their target destinations.
    """

    skip = "skip"
    overwrite = "overwrite"
    rename = "rename"
    rename_with_date = "rename_with_date"


def setup_logging(
    *,
    verbose: bool = False,
    para_root: Path | None = None,
    config: LoggingConfig | None = None,
) -> None:
    """Configure logging for CLI commands.

    Sets up loguru with console and optional file output.

    Args:
        verbose: Enable debug logging if True, otherwise use INFO level.
        para_root: PARA root directory for log files. If None, file logging disabled.
        config: Optional LoggingConfig for rotation/retention settings.
    """
    _setup_logging(
        para_root,
        verbose=verbose,
        log_to_file=para_root is not None,
        config=config,
    )


def load_config_or_exit() -> Config:
    """Load configuration, exit on error.

    Attempts to load the application configuration and exits with
    an error code if the configuration is invalid.

    Returns:
        The loaded Config object.

    Raises:
        typer.Exit: If configuration validation fails.
    """
    try:
        return load_config()
    except ValidationError:
        logger.exception("Configuration error")
        raise typer.Exit(1) from None


def get_reference_tree_path(
    reference_tree: Path | None,
    config: Config | None = None,
) -> Path:
    """Get reference tree path from CLI argument or config.

    Resolves the reference tree path using the following priority:
    1. Explicit CLI argument
    2. Configuration setting
    3. Default reference tree path

    Args:
        reference_tree: Optional explicit path from CLI argument.
        config: Optional pre-loaded configuration object.

    Returns:
        Path to the reference tree YAML file.
    """
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


def ensure_tree_exists(tree_path: Path) -> None:
    """Ensure reference tree file exists, exit if not.

    Validates that the reference tree file exists and is accessible.
    Prints an error message and exits if the file is not found.

    Args:
        tree_path: Path to the reference tree file to validate.

    Raises:
        typer.Exit: If the reference tree file does not exist.
    """
    if not tree_path.exists():
        typer.echo(f"Reference tree not found: {tree_path}", err=True)
        raise typer.Exit(1)


def validate_file_or_exit(file_path: Path) -> None:
    """Validate file exists and is a file, exit on error.

    Wrapper around validate_file_exists that uses typer.Exit for CLI.

    Args:
        file_path: Path to validate.

    Raises:
        typer.Exit: If validation fails.
    """
    if not validate_file_exists(file_path, exit_on_error=False):
        raise typer.Exit(1)


def validate_directory_or_exit(dir_path: Path) -> None:
    """Validate directory exists, exit on error.

    Wrapper around validate_directory_exists that uses typer.Exit for CLI.

    Args:
        dir_path: Path to validate.

    Raises:
        typer.Exit: If validation fails.
    """
    if not validate_directory_exists(dir_path, exit_on_error=False):
        raise typer.Exit(1)


def parse_extensions_filter(extensions: str | None) -> set[str] | None:
    """Parse comma-separated extensions into a normalized set.

    Takes a string of comma-separated extensions and normalizes them
    to lowercase with leading dots.

    Args:
        extensions: Comma-separated extension string (e.g., ".pdf,.txt" or "pdf,txt")

    Returns:
        Set of normalized extensions with leading dots, or None if input is empty.

    Examples:
        >>> parse_extensions_filter("pdf, .txt, MD")
        {".pdf", ".txt", ".md"}
        >>> parse_extensions_filter(None)
        None
    """
    if not extensions:
        return None
    return {
        ext.strip().lower() if ext.startswith(".") else f".{ext.strip().lower()}"
        for ext in extensions.split(",")
    }


def discover_files(
    dir_path: Path,
    *,
    recursive: bool,
    ext_filter: set[str] | None,
    skip_junk: bool = True,
) -> list[Path]:
    """Discover files in directory with optional filtering.

    Scans a directory for files, optionally recursively, and applies
    various filters to exclude unwanted files.

    Args:
        dir_path: Directory to scan.
        recursive: Whether to scan subdirectories.
        ext_filter: Set of extensions to include (None = all).
        skip_junk: Whether to skip junk files (DS_Store, Thumbs.db, etc.)

    Returns:
        Sorted list of file paths matching the criteria.
    """
    from para_files.utils.cleanup import is_junk_file

    files = list(dir_path.rglob("*")) if recursive else list(dir_path.glob("*"))
    files = [f for f in files if f.is_file()]

    if skip_junk:
        files = [f for f in files if not is_junk_file(f)]

    if ext_filter:
        files = [f for f in files if f.suffix.lower() in ext_filter]

    return sorted(files)


def expand_paths_to_files(
    paths: list[Path],
    *,
    recursive: bool,
    ext_filter: set[str] | None,
) -> tuple[list[Path], set[Path]]:
    """Expand paths (files or directories) to a list of files.

    Takes a mixed list of file and directory paths and expands them
    to a flat list of files, applying filters as specified.

    Args:
        paths: List of file or directory paths to expand.
        recursive: Whether to scan directories recursively.
        ext_filter: Set of extensions to include (None = all).

    Returns:
        Tuple of (expanded file list, source directories for cleanup).
        The source directories set is useful for post-processing cleanup.
    """
    expanded_files: list[Path] = []
    source_dirs: set[Path] = set()

    for path in paths:
        resolved = path.resolve()
        if resolved.is_dir():
            discovered = discover_files(resolved, recursive=recursive, ext_filter=ext_filter)
            expanded_files.extend(discovered)
            source_dirs.add(resolved)
        elif resolved.is_file():
            # Apply extension filter to explicit files too
            if ext_filter is None or resolved.suffix.lower() in ext_filter:
                expanded_files.append(resolved)
                source_dirs.add(resolved.parent)

    return expanded_files, source_dirs


def format_result_json(
    file_path: Path,
    result: ClassificationResult,
    target_path: Path,
) -> dict[str, Any]:
    """Format classification result as JSON dict.

    Converts a ClassificationResult into a dictionary suitable for
    JSON serialization and output.

    Args:
        file_path: Path to the source file that was classified.
        result: The classification result object.
        target_path: The computed target destination path.

    Returns:
        Dictionary containing the classification result data.
    """
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


def print_classification_result(
    file_path: Path,
    result: ClassificationResult,
    target_path: Path,
) -> None:
    """Print classification result to console.

    Displays a formatted classification result for a file,
    including category, confidence, and target path.

    Args:
        file_path: Path to the source file.
        result: The classification result object.
        target_path: The computed target destination path.
    """
    typer.echo(f"\n📄 {file_path.name}")
    typer.echo(f"   Category: {result.category}")
    conf = result.confidence
    typer.echo(f"   Confidence: {conf.value:.0%} ({conf.source.value})")
    typer.echo(f"   Target: {target_path}")
    if result.route_name:
        typer.echo(f"   Route: {result.route_name}")
