"""Tests for scripts/run_baseline.py (old pipeline over the golden corpus)."""

from __future__ import annotations

from pathlib import Path

import pytest

from para_files.core.tree import Tree


TREE = Tree.model_validate(
    {
        "leaves": {
            "invoices": {
                "kind": "record",
                "retention": "5y",
                "path": "4_Archives/5y_factures",
                "describe": "Invoices",
            },
            "telecom": {
                "kind": "record",
                "retention": "5y",
                "path": "4_Archives/5y_factures/Telephonie",
                "describe": "Telecom invoices",
            },
            "docs": {"kind": "library", "path": "3_Resources/docs", "describe": "Vendor docs"},
        }
    }
)
CANON_MAP = {
    "4_Archives/factures": "4_Archives/5y_factures",
    "3_Resources/documentation": "3_Resources/docs",
}


def canon(rel: str) -> str:
    return CANON_MAP.get(rel, rel)


@pytest.mark.parametrize(
    ("category", "leaf"),
    [
        ("4_Archives/factures/Telephonie/2024", "telecom"),
        ("4_Archives/5y_factures/2024", "invoices"),
        ("3_Resources/documentation/VMware", "docs"),
        ("0_Inbox", None),
        ("4_Archives/unknown/x", None),
    ],
)
def test_leaf_for_category_prefers_canonical_and_longest(load_script, category, leaf):
    baseline = load_script("run_baseline")
    assert baseline.leaf_for_category(category, TREE, canon) == leaf


def test_run_baseline_maps_errors_to_red_and_never_exposes_para_paths(
    load_script, tmp_path: Path, snapshot
):
    baseline = load_script("run_baseline")
    para = tmp_path / "PARA"
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        path = para / "4_Archives/5y_factures" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    golden = [
        {"path": f"4_Archives/5y_factures/{name}", "leaf": "invoices", "kind": "record"}
        for name in ("a.pdf", "b.pdf", "c.pdf")
    ]
    seen: list[Path] = []

    def classify(path: Path) -> tuple[str, float, str]:
        seen.append(path)
        if path.name == "b.pdf":
            msg = "unreadable"
            raise PermissionError(msg)
        if path.name == "c.pdf":
            return "0_Inbox", 0.8, "extension_router"
        return "4_Archives/factures/2024", 0.95, "rules_engine"

    before = snapshot(para)
    preds = baseline.run_baseline(para, golden, TREE, canon, classify, tmp_path / "work")
    by_name = {Path(p["path"]).name: p for p in preds}
    assert by_name["a.pdf"]["leaf"] == "invoices"
    assert by_name["a.pdf"]["band"] == "green"
    assert by_name["a.pdf"]["signal"] == "rules_engine"
    assert by_name["b.pdf"]["band"] == "red"
    assert by_name["b.pdf"]["signal"] == "error"
    assert by_name["c.pdf"]["leaf"] is None
    assert by_name["c.pdf"]["band"] == "red"
    assert all(not path.is_relative_to(para) for path in seen)
    assert snapshot(para) == before
