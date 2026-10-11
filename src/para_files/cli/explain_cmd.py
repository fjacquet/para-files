"""`para-files explain FILE`: the evidence, every signal's verdict, and what to edit."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from para_files.cli.app import app
from para_files.cli.common import context_or_exit, relative, settings_or_exit
from para_files.core.decide import NO_VERDICT, Verdict, decision_for, signal_verdicts
from para_files.core.evidence import Evidence, extract


PREVIEW_SHOWN = 160
EDIT_HINTS = {
    "rules": "edit or reorder this rule in rules.yaml",
    "books": "ISBN lookup decided; add a rule in rules.yaml to override it",
    "issuers": "edit the issuer in issuers.yaml, or the leaf keywords in tree.yaml",
    "fallback": "the model chose; add a rule or an issuer to make this deterministic",
    "none": "add a rule (rules.yaml) or an issuer (issuers.yaml) for files like this",
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


def _verdict_line(name: str, verdict: Verdict | None, note: str | None) -> str:
    if verdict is not None:
        return f"  {name:<9} {verdict.leaf_id} ({verdict.confidence:.2f}): {verdict.summary}"
    return f"  {name:<9} {note or 'no match'}"


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
    typer.echo("signals (first match wins):")
    rows = signal_verdicts(evidence, ctx, ask_fallback=ask_model)
    for name, verdict, note in rows:
        typer.echo(_verdict_line(name, verdict, note))
    winner = next((verdict for _, verdict, _ in rows if verdict is not None), NO_VERDICT)
    decision = decision_for(evidence, winner, ctx)
    target = decision.target_dir or "stays in place"
    typer.echo(f"decision: {decision.band}, {decision.leaf_id or 'no leaf'} -> {target}")
    typer.echo(f"to change it: {EDIT_HINTS.get(winner.signal, EDIT_HINTS['none'])}")
