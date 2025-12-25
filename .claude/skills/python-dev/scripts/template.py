#!/usr/bin/env python3
"""
Script template following python-dev skill guidelines.

Usage:
    .venv/bin/python scripts/template.py --input data.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field


if TYPE_CHECKING:
    from collections.abc import Sequence


# =============================================================================
# Models (Pydantic)
# =============================================================================


class InputConfig(BaseModel):
    """Input configuration schema."""

    input_path: Path = Field(..., description="Path to input file")
    output_path: Path | None = Field(None, description="Optional output path")
    verbose: bool = Field(default=False)


class Result(BaseModel):
    """Processing result schema."""

    success: bool
    message: str
    data: dict | None = None


# =============================================================================
# Pure Functions (Functional, DRY, KISS)
# =============================================================================


def load_file(path: Path) -> str:
    """Load file content as string."""
    return path.read_text(encoding="utf-8")


def process_content(content: str) -> dict:
    """Process content and return structured result."""
    lines = content.strip().splitlines()
    return {
        "line_count": len(lines),
        "char_count": len(content),
        "non_empty_lines": len([ln for ln in lines if ln.strip()]),
    }


def format_output(data: dict) -> str:
    """Format data for display."""
    return "\n".join(f"{k}: {v}" for k, v in data.items())


# =============================================================================
# Main Logic
# =============================================================================


def run(config: InputConfig) -> Result:
    """Main processing function."""
    if not config.input_path.exists():
        return Result(success=False, message=f"File not found: {config.input_path}")

    content = load_file(config.input_path)
    data = process_content(content)

    if config.output_path:
        config.output_path.write_text(format_output(data), encoding="utf-8")

    return Result(success=True, message="Processing complete", data=data)


def parse_args(argv: Sequence[str] | None = None) -> InputConfig:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", "-i", type=Path, required=True, dest="input_path")
    parser.add_argument("--output", "-o", type=Path, dest="output_path")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args(argv)
    return InputConfig(
        input_path=args.input_path,
        output_path=args.output_path,
        verbose=args.verbose,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point."""
    config = parse_args(argv)
    result = run(config)

    if config.verbose or not result.success:
        print(result.message)

    if result.success and result.data:
        print(format_output(result.data))

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
