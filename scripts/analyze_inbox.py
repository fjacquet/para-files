#!/usr/bin/env python3
"""Analyze inbox files and suggest new routes.

Run this script to get a complete analysis of files in your inbox
that couldn't be classified, with suggestions for new routes.

Usage:
    uv run scripts/analyze_inbox.py > inbox_analysis.txt 2>&1 &
    # or
    nohup uv run scripts/analyze_inbox.py > inbox_analysis.txt 2>&1 &
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def extract_text(file_path: Path) -> str:
    """Extract text from a file for analysis."""
    ext = file_path.suffix.lower()

    try:
        if ext == ".pdf":
            result = subprocess.run(
                ["pdftotext", str(file_path), "-"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout[:2000]  # First 2000 chars
        elif ext == ".xml":
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                return f.read()[:2000]
        elif ext in {".txt", ".md", ".json", ".yaml", ".yml"}:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                return f.read()[:2000]
        else:
            return f"[Binary file: {ext}]"
    except Exception as e:
        return f"[Error reading: {e}]"


def classify_files(inbox_path: Path, config_path: Path) -> list[dict]:
    """Classify all files in inbox using para-files."""
    env = os.environ.copy()
    env["PARA_FILES_PARA_ROOT"] = "/tmp/para"

    result = subprocess.run(
        [
            "uv", "run", "para-files", "classify",
            str(inbox_path),
            "-r", str(config_path),
            "-R",  # Recursive
            "--json",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=1800,  # 30 minutes max
    )

    # Parse JSON output (skip non-JSON lines like INFO/WARNING)
    for line in result.stdout.split("\n"):
        line = line.strip()
        if line.startswith("["):
            try:
                return json.loads(line + result.stdout.split(line, 1)[1].split("]")[0] + "]")
            except json.JSONDecodeError:
                pass

    # Try parsing the whole output
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        # Return empty if parsing fails
        print(f"STDERR: {result.stderr}", file=sys.stderr)
        return []


def analyze_unclassified(results: list[dict]) -> dict:
    """Analyze unclassified files and suggest routes."""
    unclassified = [r for r in results if r.get("confidence", 0) == 0]
    classified = [r for r in results if r.get("confidence", 0) > 0]

    # Group by extension
    by_extension = defaultdict(list)
    for r in unclassified:
        ext = Path(r["source_file"]).suffix.lower()
        by_extension[ext].append(r)

    # Group by detected patterns
    suggested_routes = []

    for ext, files in by_extension.items():
        # Analyze content of first few files
        samples = []
        for f in files[:5]:
            content = extract_text(Path(f["source_file"]))
            samples.append({
                "file": Path(f["source_file"]).name,
                "content_preview": content[:500],
            })

        suggested_routes.append({
            "extension": ext,
            "count": len(files),
            "samples": samples,
            "files": [Path(f["source_file"]).name for f in files],
        })

    return {
        "total_files": len(results),
        "classified_count": len(classified),
        "unclassified_count": len(unclassified),
        "classified_by_source": _group_by_source(classified),
        "unclassified_by_extension": suggested_routes,
    }


def _group_by_source(results: list[dict]) -> dict:
    """Group classified files by classification source."""
    by_source = defaultdict(list)
    for r in results:
        source = r.get("source", "unknown")
        by_source[source].append(Path(r["source_file"]).name)
    return dict(by_source)


def print_report(analysis: dict) -> None:
    """Print human-readable report."""
    print("=" * 80)
    print("INBOX ANALYSIS REPORT")
    print("=" * 80)
    print()

    print(f"Total files scanned: {analysis['total_files']}")
    print(f"Successfully classified: {analysis['classified_count']}")
    print(f"Need new routes: {analysis['unclassified_count']}")
    print()

    print("-" * 80)
    print("CLASSIFIED FILES BY SOURCE")
    print("-" * 80)
    for source, files in analysis["classified_by_source"].items():
        print(f"\n{source} ({len(files)} files):")
        for f in files[:10]:
            print(f"  - {f}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")

    print()
    print("-" * 80)
    print("UNCLASSIFIED FILES - SUGGESTED NEW ROUTES")
    print("-" * 80)

    for group in analysis["unclassified_by_extension"]:
        print(f"\n### Extension: {group['extension']} ({group['count']} files)")
        print()
        print("Files:")
        for f in group["files"][:10]:
            print(f"  - {f}")
        if len(group["files"]) > 10:
            print(f"  ... and {len(group['files']) - 10} more")

        print()
        print("Content samples:")
        for sample in group["samples"][:3]:
            print(f"\n  [{sample['file']}]")
            preview = sample["content_preview"].replace("\n", " ")[:200]
            print(f"  {preview}...")

        # Suggest route based on extension
        print()
        print("Suggested route:")
        if group["extension"] == ".xml":
            print("  # Bank statement XMLs (CAMT.053)")
            print("  bank_statements_xml:")
            print("    patterns: ['CAMT.053*', 'CAMT.054*']")
            print("    extensions: ['.xml']")
            print("    destination: '4_Archives/banques/{issuer}/{year}'")
        elif group["extension"] == ".lic":
            print("  # Software licenses")
            print("  software_licenses:")
            print("    extensions: ['.lic', '.license', '.key']")
            print("    destination: '3_Resources/licences/{year}'")
        elif group["extension"] in {".pdf", ".docx", ".doc"}:
            print("  # Need content analysis - check samples above")
            print("  # Consider adding issuer to known_issuers or pattern to routing_rules")
        else:
            print(f"  # Unknown extension {group['extension']}")
            print(f"  # Consider creating a category or extension rule")


def main():
    """Main entry point."""
    inbox_path = Path("/Users/fjacquet/Library/CloudStorage/OneDrive-Home/0_Inbox")
    config_path = Path("/Users/fjacquet/Projects/para-files/config/personal_file_tree.yaml")

    print("Starting inbox analysis...", file=sys.stderr)
    print(f"Inbox: {inbox_path}", file=sys.stderr)
    print(f"Config: {config_path}", file=sys.stderr)
    print()

    # Classify all files
    print("Classifying files (this may take a while)...", file=sys.stderr)
    results = classify_files(inbox_path, config_path)

    if not results:
        print("ERROR: No classification results. Check stderr for errors.", file=sys.stderr)
        return 1

    print(f"Classified {len(results)} files", file=sys.stderr)

    # Analyze results
    print("Analyzing results...", file=sys.stderr)
    analysis = analyze_unclassified(results)

    # Print report
    print_report(analysis)

    # Also save JSON for programmatic use
    json_path = Path("inbox_analysis.json")
    with open(json_path, "w") as f:
        json.dump(analysis, f, indent=2)
    print(f"\nJSON saved to: {json_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
