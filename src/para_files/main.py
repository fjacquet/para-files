"""Main entry point for the PARA Files classification system.

CLI for classifying files using the 5-signal pipeline.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from para_files.config import load_config
from para_files.pipeline import ClassificationPipeline


logger = logging.getLogger(__name__)


def setup_logging(*, verbose: bool = False) -> None:
    """Configure logging.

    Args:
        verbose: Enable debug logging if True.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def classify_command(args: argparse.Namespace) -> int:
    """Execute the classify command.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    file_path = Path(args.file).resolve()

    if not file_path.exists():
        logger.error("File not found: %s", file_path)
        return 1

    if not file_path.is_file():
        logger.error("Not a file: %s", file_path)
        return 1

    # Load configuration
    try:
        config = load_config()
    except ValidationError:
        logger.exception("Configuration error")
        return 1

    # Override config with CLI args if provided
    if args.reference_tree:
        config.reference_tree_path = Path(args.reference_tree)

    # Create pipeline and classify
    pipeline = ClassificationPipeline(config)
    result = pipeline.classify_file(file_path)

    # Output result
    target_path = pipeline.get_target_path(result)

    if args.json:
        import json

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
        print(json.dumps(output, indent=2))  # noqa: T201
    else:
        print(f"Category: {result.category}")  # noqa: T201
        print(  # noqa: T201
            f"Confidence: {result.confidence.value:.0%} ({result.confidence.source.value})"
        )
        print(f"Target: {target_path}")  # noqa: T201
        if result.route_name:
            print(f"Route: {result.route_name}")  # noqa: T201

    return 0


def main() -> int:
    """Run the PARA Files CLI.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        prog="para-files",
        description="Classify files using the PARA method with MLX-powered semantic routing.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Classify command
    classify_parser = subparsers.add_parser(
        "classify",
        help="Classify a file",
    )
    classify_parser.add_argument(
        "file",
        help="Path to file to classify",
    )
    classify_parser.add_argument(
        "--reference-tree",
        "-r",
        help="Path to reference tree YAML file",
    )
    classify_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output result as JSON",
    )

    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "classify":
        return classify_command(args)

    return 0


def cli() -> None:
    """CLI entry point for console script."""
    sys.exit(main())


if __name__ == "__main__":
    cli()
