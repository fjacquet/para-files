"""`para-files explain FILE`: the evidence, the cascade steps, the decision and what to edit."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from para_files.cli.app import app
from para_files.cli.common import context_or_exit, relative, settings_or_exit
from para_files.core.decide import Step, choose, decision_for
from para_files.core.evidence import Evidence, extract


PREVIEW_SHOWN = 160
EDIT_HINTS = {
    "rules": "edit or unpin this rule in rules.yaml",
    "books": "a verified ISBN decides before any rule; the Thema subject picks the library folder",
    "fallback": "the model chose; pin a rule, or improve the leaf's describe/keywords in tree.yaml",
    "hint": "a rule or issuer suggested this; pin the rule if it is always right, or fix it",
    "none": "add a rule (rules.yaml) or an issuer (issuers.yaml), or describe the leaf better",
}


def _evidence_lines(evidence: Evidence) -> list[str]:
    preview = " ".join(evidence.text_preview.split())[:PREVIEW_SHOWN] or "(no text)"
    lines = [f"  size {evidence.size} bytes, sha256 {evidence.sha256[:12]}", f"  text: {preview}"]
    if evidence.isbns:
        lines.append(f"  ISBNs: {', '.join(evidence.isbns)}")
    if evidence.exif_date:
        lines.append(f"  EXIF date: {evidence.exif_date.date().isoformat()}")
    if evidence.archive_listing:
        lines.append(f"  archive: {len(evidence.archive_listing)} entries")
    return lines


def _step_line(step: Step) -> str:
    if step.verdict is not None:
        verdict = step.verdict
        return f"  {step.name:<12} {verdict.leaf_id} ({verdict.confidence:.2f}): {verdict.summary}"
    return f"  {step.name:<12} {step.note or 'no match'}"


@app.command("explain")
def explain_command(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="The file to explain.")],
    ask_model: Annotated[
        bool, typer.Option("--ask-model", help="Also ask the fallback model (cloud, ZDR).")
    ] = False,
) -> None:
    """Show why a file goes where it goes. Changes nothing."""
    settings = settings_or_exit()
    ctx = context_or_exit(settings)
    evidence = extract(file, root=settings.para_root, preview_chars=settings.preview_chars)
    typer.echo(f"file: {relative(evidence.path, settings.para_root)}")
    if evidence.secret is not None:
        typer.echo(f"  secret ({evidence.secret}): never sent, never moved")
        return
    for line in _evidence_lines(evidence):
        typer.echo(line)
    typer.echo("steps:")
    verdict, steps = choose(evidence, ctx, ask_model=ask_model)
    for step in steps:
        typer.echo(_step_line(step))
    if verdict.about:
        typer.echo(f"  about: {verdict.about}")
    decision = decision_for(evidence, verdict, ctx)
    target = decision.target_dir or "stays in place"
    typer.echo(f"decision: {decision.band}, {decision.leaf_id or 'no leaf'} -> {target}")
    typer.echo(f"to change it: {EDIT_HINTS.get(verdict.signal, EDIT_HINTS['none'])}")
