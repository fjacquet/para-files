"""CLI module for para-files.

This module provides the command-line interface for para-files,
including all commands and shared utilities.

The module is organized as follows:
- app.py: Typer application instance
- shared.py: Shared utilities used across commands
- *_cmd.py: Individual command implementations

Commands are automatically registered when the module is imported.
"""

from __future__ import annotations

# Import all command modules to register them with the app
# The @app.command() decorators in each module register the commands
from para_files.cli import (
    classify_cmd,
    clean_cmd,
    config_cmd,
    dedupe_cmd,
    init_cmd,
    learn_cmd,
    migrate_cmd,
    move_cmd,
    routes_cmd,
    scan_cmd,
    tree_cmd,
)

# Import app first - this is the main Typer instance
from para_files.cli.app import app

# Import shared utilities for external use
from para_files.cli.shared import (
    MAX_PATTERNS_SHOWN,
    MAX_UTTERANCES_SHOWN,
    ConflictChoice,
    discover_files,
    ensure_tree_exists,
    expand_paths_to_files,
    format_result_json,
    get_reference_tree_path,
    load_config_or_exit,
    parse_extensions_filter,
    print_classification_result,
    setup_logging,
)


__all__ = [
    "MAX_PATTERNS_SHOWN",
    "MAX_UTTERANCES_SHOWN",
    # Shared utilities
    "ConflictChoice",
    # App
    "app",
    # Command modules (for documentation purposes)
    "classify_cmd",
    "clean_cmd",
    "config_cmd",
    "dedupe_cmd",
    "discover_files",
    "ensure_tree_exists",
    "expand_paths_to_files",
    "format_result_json",
    "get_reference_tree_path",
    "init_cmd",
    "learn_cmd",
    "load_config_or_exit",
    "migrate_cmd",
    "move_cmd",
    "parse_extensions_filter",
    "print_classification_result",
    "routes_cmd",
    "scan_cmd",
    "setup_logging",
    "tree_cmd",
]
