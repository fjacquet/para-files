"""Plan printing and the JSON shape shared by sort and explain."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import typer

from para_files.cli.common import relative
from para_files.core.apply import ApplyReport
from para_files.core.decide import Decision


SECTIONS = (
    ("green", "will move with --apply"),
    ("yellow", "to review (--apply --review)"),
    ("red", "stay where they are"),
)


def decision_dict(decision: Decision, root: Path) -> dict[str, Any]:
    """One decision as JSON."""
    return {
        "path": relative(decision.path, root),
        "band": decision.band,
        "leaf": decision.leaf_id,
        "target": decision.target_dir,
        "kind": decision.kind,
        "signal": decision.signal,
        "confidence": round(decision.confidence, 3),
        "why": decision.evidence_summary,
        "rename": decision.suggested_name,
    }


def summary(decisions: Sequence[Decision]) -> dict[str, Any]:
    """Counts per band, secrets, and per kind and band."""
    bands = Counter(decision.band for decision in decisions)
    kinds = Counter(f"{d.kind}:{d.band}" for d in decisions if d.kind)
    return {
        "files": len(decisions),
        "green": bands["green"],
        "yellow": bands["yellow"],
        "red": bands["red"],
        "secrets": sum(decision.signal == "secret" for decision in decisions),
        "by_kind": dict(sorted(kinds.items())),
    }


def _line(decision: Decision, root: Path) -> str:
    name = relative(decision.path, root)
    if decision.leaf_id is None:
        return f"  {name}  ({decision.evidence_summary})"
    rename = f" as {decision.suggested_name!r}" if decision.suggested_name else ""
    return (
        f"  {name}  ->  {decision.target_dir}{rename}  "
        f"[{decision.signal} {decision.confidence:.2f}]"
    )


def print_plan(decisions: Sequence[Decision], root: Path) -> None:
    """Band-grouped plan; secrets get their own heading."""
    secrets = [d for d in decisions if d.signal == "secret"]
    for band, label in SECTIONS:
        shown = [d for d in decisions if d.band == band and d.signal != "secret"]
        if shown:
            typer.echo(f"{band.upper()} ({len(shown)}): {label}")
            for decision in shown:
                typer.echo(_line(decision, root))
    if secrets:
        typer.echo(f"SECRETS ({len(secrets)}): never sent, never moved; keep them in a vault")
        for decision in secrets:
            typer.echo(f"  {relative(decision.path, root)}")
    counts = summary(decisions)
    typer.echo(
        f"{counts['files']} files: {counts['green']} green, {counts['yellow']} yellow, "
        f"{counts['red']} red ({counts['secrets']} secret)"
    )


def report_dict(run_id: str, report: ApplyReport, root: Path) -> dict[str, Any]:
    """An apply report as JSON."""
    return {
        "run_id": run_id,
        "moved": [[relative(src, root), relative(dst, root)] for src, dst in report.moved],
        "trashed": [[relative(src, root), relative(dst, root)] for src, dst in report.trashed],
        "skipped": [[relative(src, root), reason] for src, reason in report.skipped],
        "removed_dirs": [relative(path, root) for path in report.removed_dirs],
    }


def print_report(run_id: str, report: ApplyReport, root: Path) -> None:
    """What an apply did, and how to undo it."""
    typer.echo(
        f"run {run_id}: {len(report.moved)} moved, {len(report.trashed)} to .trash, "
        f"{len(report.skipped)} skipped, {len(report.removed_dirs)} empty folders removed"
    )
    for src, reason in report.skipped:
        typer.echo(f"  skipped {relative(src, root)}: {reason}")
    if report.moved or report.trashed:
        typer.echo(f"undo with: para-files undo {run_id}")
