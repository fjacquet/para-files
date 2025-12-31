"""Logging configuration using loguru.

Provides unified logging for all para-files operations:
- Console output (human-readable)
- File output (JSON format for audit trail)
- Automatic rotation and retention

Configuration via config.yaml or environment variables:
    logging:
      level: INFO          # DEBUG, INFO, WARNING, ERROR
      rotation: "10 MB"    # Size-based rotation
      retention: "30 days" # How long to keep logs
      compression: gz      # gz, bz2, xz, zip
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger


if TYPE_CHECKING:
    from para_files.config import LoggingConfig


# Re-export logger for convenience
__all__ = ["logger", "setup_logging"]


def setup_logging(
    para_root: Path | None = None,
    *,
    verbose: bool = False,
    log_to_file: bool = True,
    config: LoggingConfig | None = None,
) -> None:
    """Configure loguru for para-files.

    Args:
        para_root: PARA root directory for log files. If None, file logging disabled.
        verbose: Enable DEBUG level logging (overrides config.level for console).
        log_to_file: Write logs to file (JSON format with rotation).
        config: Optional LoggingConfig with rotation/retention/level settings.
    """
    # Import here to avoid circular dependency
    from para_files.config import LoggingConfig

    # Use defaults if no config provided
    if config is None:
        config = LoggingConfig()

    # Remove default handler
    logger.remove()

    # Console: DEBUG if verbose, otherwise INFO
    console_level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=console_level,
        format="<level>{level}:</level> {message}",
        colorize=True,
    )

    # File: JSON format with configurable rotation
    if log_to_file and para_root:
        log_dir = para_root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "operations.log"

        logger.add(
            log_path,
            rotation=config.rotation,
            retention=config.retention,
            compression=config.compression,
            serialize=True,  # JSON format
            level=config.level,
            enqueue=True,  # Thread-safe async writes
        )
