#!/usr/bin/env python3
"""Analyze inbox files and suggest new routes.

Run this script to get a complete analysis of files in your inbox
that couldn't be classified, with suggestions for new routes.

Usage:
    uv run scripts/analyze_inbox.py --inbox /path/to/inbox
    uv run scripts/analyze_inbox.py --help
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import click


# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from para_files.utils.pandoc import extract_text as pandoc_extract  # noqa: I001

# Maximum number of items to display in reports
_MAX_DISPLAY_ITEMS = 10


def extract_text(file_path: Path, max_chars: int = 2000) -> str:
    """Extract text from a file for analysis.

    Uses pandoc for supported formats, falls back to direct read for text files.

    Args:
        file_path: Path to the file.
        max_chars: Maximum characters to extract.

    Returns:
        Extracted text content or error message.
    """
    ext = file_path.suffix.lower()

    try:
        # Try pandoc first (handles PDF, DOCX, etc.)
        result = pandoc_extract(file_path, max_chars=max_chars)
        if result and result.text:
            return result.text[:max_chars]

        # Fallback for simple text formats
        if ext in {".txt", ".md", ".json", ".yaml", ".yml", ".xml", ".csv"}:
            with file_path.open(encoding="utf-8", errors="ignore") as f:
                return f.read()[:max_chars]

    except (OSError, ValueError) as e:
        return f"[Error reading: {e}]"

    return f"[Binary file: {ext}]"


def classify_files(
    inbox_path: Path,
    config_path: Path,
    para_root: Path,
    timeout: int = 1800,
) -> list[dict[str, Any]]:
    """Classify all files in inbox using para-files.

    Args:
        inbox_path: Path to inbox directory.
        config_path: Path to YAML config file.
        para_root: PARA root directory.
        timeout: Maximum time in seconds (default 30 minutes).

    Returns:
        List of classification result dictionaries.
    """
    env = os.environ.copy()
    env["PARA_FILES_PARA_ROOT"] = str(para_root)

    cmd = [
        "uv",
        "run",
        "para-files",
        "classify",
        str(inbox_path),
        "-r",
        str(config_path),
        # "-R",  # Recursive
        "--json",
    ]

    click.echo(f"Running: {' '.join(cmd)}", err=True)

    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        click.echo("ERROR: Classification timed out", err=True)
        return []

    if result.returncode != 0:
        click.echo(f"WARNING: Command returned {result.returncode}", err=True)
        if result.stderr:
            click.echo(f"STDERR: {result.stderr[:500]}", err=True)

    # Parse JSON output - find the JSON array in the output
    output = result.stdout.strip()

    result_list: list[dict[str, Any]] = []

    # Try to find JSON array in output (skip log lines)
    for raw_line in output.split("\n"):
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            try:
                result_list = json.loads(line)
                return result_list
            except json.JSONDecodeError:
                continue

    # Try parsing multi-line JSON
    try:
        # Find start of JSON array
        start_idx = output.find("[")
        end_idx = output.rfind("]")
        if start_idx != -1 and end_idx != -1:
            json_str = output[start_idx : end_idx + 1]
            result_list = json.loads(json_str)
            return result_list
    except json.JSONDecodeError:
        pass

    # Last resort: try whole output
    try:
        result_list = json.loads(output)
        return result_list
    except json.JSONDecodeError:
        click.echo("ERROR: Could not parse JSON output", err=True)
        click.echo(f"Output preview: {output[:500]}", err=True)

    return result_list


def analyze_unclassified(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze unclassified files and suggest routes.

    Args:
        results: List of classification results.

    Returns:
        Analysis dictionary with statistics and suggestions.
    """
    unclassified = [r for r in results if r.get("confidence", 0) == 0]
    classified = [r for r in results if r.get("confidence", 0) > 0]

    # Group by extension
    by_extension: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in unclassified:
        ext = Path(r["source_file"]).suffix.lower()
        by_extension[ext].append(r)

    # Build suggestions for each extension group
    suggested_routes = []
    for ext, files in sorted(by_extension.items(), key=lambda x: -len(x[1])):
        # Sample content from first few files
        samples = []
        for f in files[:5]:
            file_path = Path(f["source_file"])
            if file_path.exists():
                content = extract_text(file_path, max_chars=500)
                samples.append(
                    {
                        "file": file_path.name,
                        "content_preview": content[:500],
                    }
                )

        suggested_routes.append(
            {
                "extension": ext,
                "count": len(files),
                "samples": samples,
                "files": [Path(f["source_file"]).name for f in files],
            }
        )

    return {
        "total_files": len(results),
        "classified_count": len(classified),
        "unclassified_count": len(unclassified),
        "classified_by_source": _group_by_source(classified),
        "classified_by_route": _group_by_route(classified),
        "unclassified_by_extension": suggested_routes,
    }


def _group_by_source(results: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Group classified files by classification source."""
    by_source: dict[str, list[str]] = defaultdict(list)
    for r in results:
        source = r.get("source", "unknown")
        by_source[source].append(Path(r["source_file"]).name)
    return dict(by_source)


def _group_by_route(results: list[dict[str, Any]]) -> dict[str, int]:
    """Group classified files by route/category."""
    by_route: dict[str, int] = defaultdict(int)
    for r in results:
        route = r.get("route_name") or r.get("category", "unknown")
        by_route[route] += 1
    return dict(sorted(by_route.items(), key=lambda x: -x[1]))


def suggest_route_config(ext: str) -> str:
    """Generate suggested route configuration based on extension.

    Args:
        ext: File extension.

    Returns:
        YAML configuration suggestion.
    """
    suggestions = {
        ".xml": """  # Bank statement XMLs (CAMT.053/054)
  bank_statements_xml:
    patterns: ['CAMT.053*', 'CAMT.054*', '*camt053*', '*camt054*']
    extensions: ['.xml']
    destination: '4_Archives/banques/{issuer}/{YYYY}'""",
        ".lic": """  # Software licenses
  software_licenses:
    extensions: ['.lic', '.license', '.key']
    destination: '3_Resources/licences/{YYYY}'""",
        ".ics": """  # Calendar events
  calendar_events:
    extensions: ['.ics']
    destination: '3_Resources/calendrier/{YYYY}'""",
        ".vcf": """  # Contact cards
  contacts:
    extensions: ['.vcf']
    destination: '3_Resources/contacts'""",
        ".eml": """  # Email archives
  emails:
    extensions: ['.eml', '.msg']
    destination: '4_Archives/emails/{YYYY}/{MM}'""",
    }

    if ext in suggestions:
        return suggestions[ext]

    if ext in {".pdf", ".docx", ".doc"}:
        return """  # Analyze content samples above to determine:
  # - Add issuer to known_issuers.yaml if recognizable sender
  # - Add pattern to routing_rules if filename has pattern
  # - Add route with utterances for semantic matching"""

    return f"""  # Custom rule for {ext} files
  custom_{ext.lstrip(".")}:
    extensions: ['{ext}']
    destination: '3_Resources/other/{ext.lstrip(".")}'"""


def print_report(analysis: dict[str, Any]) -> None:
    """Print human-readable analysis report.

    Args:
        analysis: Analysis dictionary from analyze_unclassified().
    """
    click.echo("=" * 80)
    click.echo("INBOX ANALYSIS REPORT")
    click.echo("=" * 80)
    click.echo()

    # Summary
    total = analysis["total_files"]
    classified = analysis["classified_count"]
    unclassified = analysis["unclassified_count"]
    pct = (classified / total * 100) if total > 0 else 0

    click.echo(f"Total files scanned: {total}")
    click.echo(f"Successfully classified: {classified} ({pct:.1f}%)")
    click.echo(f"Need new routes: {unclassified}")
    click.echo()

    # Classified by source
    click.echo("-" * 80)
    click.echo("CLASSIFIED FILES BY SOURCE")
    click.echo("-" * 80)
    for source, files in sorted(analysis["classified_by_source"].items(), key=lambda x: -len(x[1])):
        click.echo(f"\n{source} ({len(files)} files):")
        for f in files[:_MAX_DISPLAY_ITEMS]:
            click.echo(f"  - {f}")
        if len(files) > _MAX_DISPLAY_ITEMS:
            click.echo(f"  ... and {len(files) - _MAX_DISPLAY_ITEMS} more")

    # Classified by route
    click.echo()
    click.echo("-" * 80)
    click.echo("TOP ROUTES")
    click.echo("-" * 80)
    for route, count in list(analysis["classified_by_route"].items())[:15]:
        click.echo(f"  {count:4d}  {route}")

    # Unclassified suggestions
    click.echo()
    click.echo("-" * 80)
    click.echo("UNCLASSIFIED FILES - SUGGESTED NEW ROUTES")
    click.echo("-" * 80)

    for group in analysis["unclassified_by_extension"]:
        click.echo(f"\n### Extension: {group['extension']} ({group['count']} files)")
        click.echo()

        click.echo("Files:")
        for f in group["files"][:_MAX_DISPLAY_ITEMS]:
            click.echo(f"  - {f}")
        if len(group["files"]) > _MAX_DISPLAY_ITEMS:
            click.echo(f"  ... and {len(group['files']) - _MAX_DISPLAY_ITEMS} more")

        if group["samples"]:
            click.echo()
            click.echo("Content samples:")
            for sample in group["samples"][:3]:
                click.echo(f"\n  [{sample['file']}]")
                preview = sample["content_preview"].replace("\n", " ")[:200]
                click.echo(f"  {preview}...")

        click.echo()
        click.echo("Suggested route configuration:")
        suggestion = suggest_route_config(group["extension"])
        for line in suggestion.split("\n"):
            click.echo(f"  {line}")


@click.command()
@click.option(
    "--inbox",
    "-i",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.home() / "Library/CloudStorage/OneDrive-Home/0_Inbox",
    help="Path to inbox directory",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path(__file__).parent.parent / "config/personal_file_tree.yaml",
    help="Path to YAML config file",
)
@click.option(
    "--para-root",
    "-p",
    type=click.Path(path_type=Path),
    default=None,
    help="PARA root directory (default: system temp dir)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output JSON file path",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=1800,
    help="Classification timeout in seconds (default: 1800)",
)
def main(
    inbox: Path,
    config: Path,
    para_root: Path | None,
    output: Path | None,
    timeout: int,
) -> None:
    """Analyze inbox files and suggest new routes.

    Classifies all files in the inbox directory and generates a report
    showing which files couldn't be classified, grouped by extension,
    with suggested route configurations.
    """
    # Use system temp dir if para_root not specified
    if para_root is None:
        para_root = Path(tempfile.gettempdir()) / "para-files-analysis"

    click.echo("Starting inbox analysis...", err=True)
    click.echo(f"Inbox: {inbox}", err=True)
    click.echo(f"Config: {config}", err=True)
    click.echo(f"PARA root: {para_root}", err=True)
    click.echo()

    # Ensure PARA root exists
    para_root.mkdir(parents=True, exist_ok=True)

    # Classify all files
    click.echo("Classifying files (this may take a while)...", err=True)
    results = classify_files(inbox, config, para_root, timeout=timeout)

    if not results:
        click.echo("ERROR: No classification results. Check stderr for errors.", err=True)
        raise SystemExit(1)

    click.echo(f"Classified {len(results)} files", err=True)

    # Analyze results
    click.echo("Analyzing results...", err=True)
    analysis = analyze_unclassified(results)

    # Print report to stdout
    print_report(analysis)

    # Save JSON if requested
    json_path = output or Path("inbox_analysis.json")
    with json_path.open("w") as f:
        json.dump(analysis, f, indent=2, default=str)
    click.echo(f"\nJSON saved to: {json_path}", err=True)


if __name__ == "__main__":
    main()
