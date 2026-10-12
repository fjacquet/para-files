"""`--review` prompts: end of input after "?" and the group view."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from para_files.cli import review
from para_files.core.decide import Decision
from tests.core_helpers import make_config


def decision(name: str, ranked=()) -> Decision:
    return Decision(
        path=Path("/p/0_Inbox") / name,
        sha256="a" * 64,
        leaf_id="resources_it",
        target_dir="3_Resources/IT",
        band="yellow",
        signal="fallback",
        confidence=0.6,
        evidence_summary="m1",
        kind="resource",
        ranked=ranked,
    )


def ask_then_abort(answers):
    queue = list(answers)

    def ask(_prompt: str) -> str:
        if queue:
            return queue.pop(0)
        raise typer.Abort

    return ask


def test_end_of_input_after_a_question_mark_stops():
    with pytest.raises(review.Stop):
        review._choice(ask_then_abort(["?"]), "> ", make_config())


def test_end_of_input_after_a_question_mark_keeps_confirmed_ops():
    config = make_config()
    decisions = [decision("a.md"), decision("b.md")]
    groups = review.group_by_leaf(decisions)
    assert len(groups) == 1
    # One group of two: "o", accept the first file, then "?" and end of input.
    ops = review.review_ops(decisions, config, Path("/p"), ask_then_abort(["o", "", "?"]))
    assert [op.decision.path.name for op in ops] == ["a.md"]


def test_group_view_has_no_numbered_alternatives(capsys):
    ranked = (("resources_it", 0.6), ("archives_5y_factures", 0.3))
    decisions = [decision("a.md", ranked), decision("b.md", ranked)]
    review.review_ops(decisions, make_config(), Path("/p"), ask_then_abort(["s"]))
    out = capsys.readouterr().out
    assert "2)" not in out
    assert "also: archives_5y_factures 0.30" in out
