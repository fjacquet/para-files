"""File and path validation utilities.

This module provides unified validation functions for files and directories,
consolidating duplicate validation logic from the CLI module.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger


def validate_file_exists(
    file_path: Path,
    *,
    exit_on_error: bool = False,
) -> bool:
    """Validate that a file exists and is a regular file.

    This function checks if the given path exists and points to a file
    (not a directory or other filesystem object). It can either return
    a boolean result or raise SystemExit on failure.

    Args:
        file_path: The path to validate.
        exit_on_error: If True, raise SystemExit(1) on validation failure
            instead of returning False. Useful for CLI commands that should
            terminate on invalid input.

    Returns:
        True if the path exists and is a file, False otherwise.
        Only returns False if exit_on_error is False.

    Raises:
        SystemExit: If exit_on_error is True and validation fails.

    Examples:
        >>> validate_file_exists(Path("/etc/hosts"))
        True
        >>> validate_file_exists(Path("/nonexistent"))
        False
        >>> validate_file_exists(Path("/nonexistent"), exit_on_error=True)
        SystemExit: 1
    """
    if not file_path.exists():
        msg = f"File not found: {file_path}"
        if exit_on_error:
            logger.error(msg)
            raise SystemExit(1)
        logger.warning(msg)
        return False

    if not file_path.is_file():
        msg = f"Not a file: {file_path}"
        if exit_on_error:
            logger.error(msg)
            raise SystemExit(1)
        logger.warning(msg)
        return False

    return True


def validate_directory_exists(
    dir_path: Path,
    *,
    exit_on_error: bool = False,
) -> bool:
    """Validate that a directory exists and is a directory.

    This function checks if the given path exists and points to a directory
    (not a file or other filesystem object). It can either return a boolean
    result or raise SystemExit on failure.

    Args:
        dir_path: The path to validate.
        exit_on_error: If True, raise SystemExit(1) on validation failure
            instead of returning False. Useful for CLI commands that should
            terminate on invalid input.

    Returns:
        True if the path exists and is a directory, False otherwise.
        Only returns False if exit_on_error is False.

    Raises:
        SystemExit: If exit_on_error is True and validation fails.

    Examples:
        >>> validate_directory_exists(Path("/etc"))
        True
        >>> validate_directory_exists(Path("/nonexistent"))
        False
        >>> validate_directory_exists(Path("/nonexistent"), exit_on_error=True)
        SystemExit: 1
    """
    if not dir_path.exists():
        msg = f"Directory not found: {dir_path}"
        if exit_on_error:
            logger.error(msg)
            raise SystemExit(1)
        logger.warning(msg)
        return False

    if not dir_path.is_dir():
        msg = f"Not a directory: {dir_path}"
        if exit_on_error:
            logger.error(msg)
            raise SystemExit(1)
        logger.warning(msg)
        return False

    return True
