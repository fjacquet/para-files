"""`para-files sort`: classify, show the plan, and move files only with --apply."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import typer

from para_files.cli.app import app
from para_files.cli.common import context_or_exit, fail, settings_or_exit
from para_files.cli.output import decision_dict, print_plan, print_report, report_dict, summary
from para_files.cli.review import review_ops
from para_files.core.decide import Context, Decision
from para_files.core.settings import INBOX
from para_files.core.sort import apply, auto_ops, preview


def _in_dot_folder(path: Path, root: Path) -> bool:
    """True when path is inside the PARA root and a folder below the root starts with a dot."""
    resolved, base = path.resolve(), root.resolve()
    if not resolved.is_relative_to(base):
        return False
    return any(part.startswith(".") for part in resolved.relative_to(base).parts)


def _apply(
    decisions: Sequence[Decision],
    ctx: Context,
    roots: Sequence[Path],
    *,
    review: bool,
    as_json: bool,
) -> dict[str, object] | None:
    """Move the green files (and the reviewed ones); None when there is nothing to move."""
    root = ctx.settings.para_root
    ops = auto_ops(decisions)
    if review:
        ops += review_ops(decisions, ctx.config, root)
    if not ops:
        if not as_json:
            typer.echo("nothing to move")
        return None
    run_id, report = apply(ops, ctx, roots)
    if not as_json:
        print_report(run_id, report, root)
    return report_dict(run_id, report, root)


def _check_inputs(roots: Sequence[Path], root: Path) -> None:
    """Exit unless every path exists and none is a dot-folder inside the PARA root."""
    for path in roots:
        if not path.exists():
            fail(f"no such file or folder: {path}")
        if _in_dot_folder(path, root):
            fail(f"dot-folders are never sorted: {path}")


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
    root = settings.para_root
    _check_inputs(roots, root)
    decisions = preview(roots, ctx)
    if not as_json:
        print_plan(decisions, root)
    output: dict[str, object] = {
        "decisions": [decision_dict(decision, root) for decision in decisions],
        "summary": summary(decisions),
    }
    if apply_:
        applied = _apply(decisions, ctx, roots, review=review, as_json=as_json)
        if applied is not None:
            output["applied"] = applied
    if as_json:
        typer.echo(json.dumps(output, ensure_ascii=False, indent=2))
