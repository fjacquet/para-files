"""Entry point for para-files CLI.

This module provides the main entry point for the para-files command-line
interface. All commands are implemented in the cli/ subpackage.

For backward compatibility with tests and external code, this module
re-exports the main symbols that were previously defined here.
"""

from __future__ import annotations

# Import all commands to register them with the app
from para_files.cli import (  # noqa: F401
    bookstore_cmd,
    classify_cmd,
    clean_cmd,
    config_cmd,
    dedupe_cmd,
    init_cmd,
    learn_cmd,
    move_cmd,
    routes_cmd,
    scan_cmd,
    tree_cmd,
)

# Import app directly from cli.app (not from cli/__init__ to satisfy mypy)
from para_files.cli.app import app
from para_files.cli.classify_cmd import (
    _classify_files_parallel,
    _classify_files_sequential,
)

# Re-exports for backward compatibility with tests
# These symbols are used by tests that import directly from para_files.main
from para_files.cli.shared import (
    ConflictChoice,
    setup_logging,
)
from para_files.cli.shared import (
    format_result_json as _format_result_json,
)
from para_files.cli.shared import (
    parse_extensions_filter as _parse_extensions_filter,
)

# Re-export ClassificationPipeline for tests that patch it via para_files.main
from para_files.pipeline import ClassificationPipeline
from para_files.utils.validation import (
    validate_file_exists as _validate_file_exists,
)


__all__ = [
    # Backward compatibility exports (used by tests)
    "ClassificationPipeline",
    "ConflictChoice",
    "_classify_files_parallel",
    "_classify_files_sequential",
    "_format_result_json",
    "_parse_extensions_filter",
    "_validate_file_exists",
    # Main application
    "app",
    "cli",
    "main",
    "setup_logging",
]


def main() -> None:
    """Run the para-files CLI application."""
    app()


def cli() -> None:
    """Alias for main() - for pyproject.toml entry point."""
    main()


if __name__ == "__main__":
    main()
