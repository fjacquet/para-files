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


def group_by_leaf(decisions: Sequence[Decision]) -> list[tuple[str, list[Decision]]]:
    """Yellow decisions with a leaf, by leaf: biggest group first, then by leaf id."""
    groups: dict[str, list[Decision]] = {}
    for decision in decisions:
        if decision.band == "yellow" and decision.leaf_id:
            groups.setdefault(decision.leaf_id, []).append(decision)
    ordered = [(leaf, sorted(group, key=lambda d: str(d.path))) for leaf, group in groups.items()]
    return sorted(ordered, key=lambda item: (-len(item[1]), item[0]))


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
        "ranked": [[leaf, round(p, 3)] for leaf, p in decision.ranked],
        "about": decision.about,
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
        "by_signal": dict(sorted(Counter(d.signal for d in decisions).items())),
    }


def _line(decision: Decision, root: Path) -> str:
    name = relative(decision.path, root)
    if decision.leaf_id is None:
        return f"  {name}  ({decision.evidence_summary})"
    rename = f" as {decision.suggested_name!r}" if decision.suggested_name else ""
    about = f"  — {decision.about}" if decision.about else ""
    return (
        f"  {name}  ->  {decision.target_dir}{rename}  "
        f"[{decision.signal} {decision.confidence:.2f}]{about}"
    )


def print_plan(decisions: Sequence[Decision], root: Path) -> None:
    """Band-grouped plan (yellow by folder); secrets get their own heading."""
    secrets = [d for d in decisions if d.signal == "secret"]
    for band, label in SECTIONS:
        shown = [d for d in decisions if d.band == band and d.signal != "secret"]
        if not shown:
            continue
        typer.echo(f"{band.upper()} ({len(shown)}): {label}")
        if band == "yellow":
            for leaf_id, group in group_by_leaf(shown):
                typer.echo(f"  {leaf_id} ({len(group)})")
                for decision in group:
                    typer.echo("  " + _line(decision, root))
        else:
            for decision in shown:
                typer.echo(_line(decision, root))
    if secrets:
        typer.echo(f"SECRETS ({len(secrets)}): never sent, never moved; keep them in a vault")
        for decision in secrets:
            typer.echo(f"  {relative(decision.path, root)}")
    hinted = sum(d.signal == "hint" for d in decisions)
    if hinted:
        typer.echo(f"{hinted} files decided by hints only (model off or did not answer)")
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
