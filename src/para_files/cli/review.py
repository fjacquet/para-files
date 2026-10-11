"""Interactive confirmation of yellow decisions (`sort --apply --review`).

Every answer becomes an owner-decided operation: the journal records it as a label
(spec §4.5), which is what later lifts the calibration cap.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import typer

from para_files.cli.common import relative
from para_files.core.apply import Op
from para_files.core.decide import Decision
from para_files.core.tree import TreeConfig


Ask = Callable[[str], str]
PROMPT = "  [Enter] accept, s skip, q stop, ? list leaves, or type a leaf id: "


def _ask(prompt: str) -> str:
    return str(typer.prompt(prompt, default="", show_default=False))


def resolve_leaf(text: str, config: TreeConfig) -> str | None:
    """Exact leaf id, or the only leaf id starting with text."""
    leaves = list(config.tree.leaves)
    if text in leaves:
        return text
    found = [leaf_id for leaf_id in leaves if leaf_id.startswith(text)]
    return found[0] if len(found) == 1 else None


def _list_leaves(config: TreeConfig) -> None:
    for leaf_id, leaf in sorted(config.tree.leaves.items(), key=lambda item: item[1].path):
        typer.echo(f"    {leaf_id:<32} {leaf.path}")


def _answer(decision: Decision, config: TreeConfig, ask: Ask) -> Op | str | None:
    """An Op, "skip", "stop", or None to ask again."""
    answer = ask(PROMPT).strip()
    if answer in {"", "y"}:
        return Op(decision, str(decision.leaf_id), "owner")
    if answer in {"s", "q"}:
        return "skip" if answer == "s" else "stop"
    if answer == "?":
        _list_leaves(config)
        return None
    leaf_id = resolve_leaf(answer, config)
    if leaf_id is None:
        typer.echo(f"  unknown or ambiguous leaf: {answer!r}")
        return None
    return Op(decision, leaf_id, "owner")


def review_ops(
    decisions: Sequence[Decision], config: TreeConfig, root: Path, ask: Ask = _ask
) -> list[Op]:
    """Ask about each yellow decision; return the confirmed or corrected operations."""
    pending = [d for d in decisions if d.band == "yellow" and d.leaf_id]
    ops: list[Op] = []
    for index, decision in enumerate(pending, start=1):
        typer.echo(f"[{index}/{len(pending)}] {relative(decision.path, root)}")
        typer.echo(
            f"  proposed: {decision.leaf_id} -> {decision.target_dir} "
            f"({decision.signal} {decision.confidence:.2f}; {decision.evidence_summary})"
        )
        result: Op | str | None = None
        try:
            while result is None:
                result = _answer(decision, config, ask)
        except typer.Abort:
            return ops
        if result == "stop":
            return ops
        if isinstance(result, Op):
            ops.append(result)
    return ops
