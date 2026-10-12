"""Interactive confirmation of yellow decisions (`sort --apply --review`), folder by folder.

Files proposed for the same leaf are reviewed together: accept the group, skip it, send it
elsewhere, or go through it one by one. Every answer is an owner decision (spec §4.5).
"""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import typer

from para_files.cli.common import relative
from para_files.cli.output import group_by_leaf
from para_files.core.apply import Op
from para_files.core.decide import Decision
from para_files.core.tree import TreeConfig


Ask = Callable[[str], str]
GROUP_PROMPT = "  [Enter] accept all, o one by one, s skip, q stop, ? list leaves, or a leaf id: "
FILE_PROMPT = "  [Enter] accept, 2/3 alternative, s skip, q stop, ? list leaves, or a leaf id: "


class Stop(Exception):  # noqa: N818 - a signal, not an error
    """The owner typed q or input ended: keep what was confirmed, ask nothing more."""


def _ask(prompt: str) -> str:
    return str(typer.prompt(prompt, default="", show_default=False))


def stdin_is_tty() -> bool:
    """True when a person can answer the questions: stdin is a terminal."""
    return sys.stdin.isatty()


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


def _choice(ask: Ask, prompt: str, config: TreeConfig) -> str:
    """The owner's answer; "?" lists the leaves and asks again. Raises Stop at end of input."""
    try:
        answer = ask(prompt).strip()
        while answer == "?":
            _list_leaves(config)
            answer = ask(prompt).strip()
    except typer.Abort as exc:
        raise Stop from exc
    return answer


def _typed_leaf(answer: str, config: TreeConfig) -> str | None:
    leaf_id = resolve_leaf(answer, config)
    if leaf_id is None:
        typer.echo(f"  unknown or ambiguous leaf: {answer!r}")
    return leaf_id


def _alternatives(decision: Decision) -> str:
    others = [f"{n}) {leaf} {p:.2f}" for n, (leaf, p) in enumerate(decision.ranked[1:], 2)]
    return f"  alternatives: {', '.join(others)}" if others else ""


def _one(decision: Decision, config: TreeConfig, root: Path, ask: Ask, position: str) -> Op | None:
    """Ask about one file: an Op, or None when skipped. Raises Stop on q or end of input."""
    typer.echo(f"{position} {relative(decision.path, root)}")
    typer.echo(
        f"  proposed: {decision.leaf_id} -> {decision.target_dir} "
        f"({decision.signal} {decision.confidence:.2f}; {decision.evidence_summary})"
    )
    if decision.about:
        typer.echo(f"  about: {decision.about}")
    if alternatives := _alternatives(decision):
        typer.echo(alternatives)
    while True:
        answer = _choice(ask, FILE_PROMPT, config)
        if answer in {"", "y"}:
            return Op(decision, str(decision.leaf_id), "owner")
        if answer == "s":
            return None
        if answer == "q":
            raise Stop
        if answer.isdigit() and 1 <= int(answer) <= len(decision.ranked):
            return Op(decision, decision.ranked[int(answer) - 1][0], "owner")
        if (leaf_id := _typed_leaf(answer, config)) is not None:
            return Op(decision, leaf_id, "owner")


def _show(decision: Decision, root: Path) -> None:
    about = f" — {decision.about}" if decision.about else ""
    typer.echo(
        f"    {relative(decision.path, root)}  [{decision.signal} {decision.confidence:.2f}]{about}"
    )
    if len(decision.ranked) > 1:
        others = ", ".join(f"{leaf} {p:.2f}" for leaf, p in decision.ranked[1:])
        typer.echo(f"      also: {others}")


def _each(group: list[Decision], context: tuple[TreeConfig, Path, Ask], ops: list[Op]) -> None:
    """Go through a group one file at a time; confirmed ops are appended as they are given."""
    config, root, ask = context
    for index, decision in enumerate(group, start=1):
        if (op := _one(decision, config, root, ask, f"  [{index}/{len(group)}]")) is not None:
            ops.append(op)


def _group(
    leaf_id: str,
    group: list[Decision],
    context: tuple[TreeConfig, Path, Ask],
    position: str,
    ops: list[Op],
) -> None:
    """Ask about one group; confirmed ops are appended to ops as soon as they are given."""
    config, root, ask = context
    if len(group) == 1:
        if (op := _one(group[0], config, root, ask, position)) is not None:
            ops.append(op)
        return
    typer.echo(f"{position} {leaf_id} -> {config.tree.leaves[leaf_id].path} ({len(group)} files)")
    for decision in group:
        _show(decision, root)
    while True:
        answer = _choice(ask, GROUP_PROMPT, config)
        if answer in {"", "y"}:
            ops.extend(Op(decision, leaf_id, "owner") for decision in group)
            return
        if answer == "s":
            return
        if answer == "q":
            raise Stop
        if answer == "o":
            _each(group, context, ops)
            return
        if (target := _typed_leaf(answer, config)) is not None:
            ops.extend(Op(decision, target, "owner") for decision in group)
            return


def review_ops(
    decisions: Sequence[Decision], config: TreeConfig, root: Path, ask: Ask = _ask
) -> list[Op]:
    """Ask about each folder group of yellow decisions; return the confirmed operations."""
    groups = group_by_leaf(decisions)
    ops: list[Op] = []
    with contextlib.suppress(Stop):
        for index, (leaf_id, group) in enumerate(groups, start=1):
            _group(leaf_id, group, (config, root, ask), f"[{index}/{len(groups)}]", ops)
    return ops
