"""`para-files sort`: classify, show the plan, and move files only with --apply."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from para_files.cli.app import app
from para_files.cli.common import context_or_exit, fail, settings_or_exit
from para_files.cli.output import decision_dict, print_plan, print_report, report_dict, summary
from para_files.cli.review import review_ops
from para_files.core.settings import INBOX
from para_files.core.sort import apply, auto_ops, preview


@app.command("sort")
def sort_command(
    paths: Annotated[
        list[Path] | None, typer.Argument(help="Files or folders to sort (default: 0_Inbox).")
    ] = None,
    apply_: Annotated[
        bool, typer.Option("--apply", help="Move green files (and confirmed ones with --review).")
    ] = False,
    review: Annotated[
        bool, typer.Option("--review", help="Confirm or correct yellow files one by one.")
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print the plan as JSON.")] = False,
    workers: Annotated[
        int | None, typer.Option("--workers", "-w", min=1, max=16, help="Parallel classifiers.")
    ] = None,
) -> None:
    """Classify files and show the plan; nothing moves without --apply."""
    if review and not apply_:
        fail("--review needs --apply: the files you confirm are moved")
    if review and as_json:
        fail("--review is interactive; drop --json")
    settings = settings_or_exit(**({"max_workers": workers} if workers else {}))
    ctx = context_or_exit(settings)
    roots = [path.expanduser() for path in paths] if paths else [settings.para_root / INBOX]
    for path in roots:
        if not path.exists():
            fail(f"no such file or folder: {path}")
    root = settings.para_root
    decisions = preview(roots, ctx)
    if not as_json:
        print_plan(decisions, root)
    output: dict[str, object] = {
        "decisions": [decision_dict(decision, root) for decision in decisions],
        "summary": summary(decisions),
    }
    if apply_:
        ops = auto_ops(decisions)
        if review:
            ops += review_ops(decisions, ctx.config, root)
        run_id, report = apply(ops, ctx, roots)
        output["applied"] = report_dict(run_id, report, root)
        if not as_json:
            print_report(run_id, report, root)
    if as_json:
        typer.echo(json.dumps(output, ensure_ascii=False, indent=2))
