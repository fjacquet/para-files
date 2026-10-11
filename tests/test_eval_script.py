"""Tests for scripts/eval.py (per-kind and per-signal metrics, spec §4.5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


GOLDEN = [
    {"path": "a.pdf", "leaf": "inv", "kind": "record"},
    {"path": "b.pdf", "leaf": "inv", "kind": "record"},
    {"path": "c.pdf", "leaf": "books", "kind": "library"},
    {"path": "Matière.pdf", "leaf": "notes", "kind": "knowledge"},  # NFD on purpose
]
PREDS = [
    {
        "path": "a.pdf",
        "leaf": "inv",
        "confidence": 0.9,
        "band": "green",
        "signal": "rules",
        "secs": 0.1,
        "cost": 0.0,
    },
    {
        "path": "b.pdf",
        "leaf": "bank",
        "confidence": 0.6,
        "band": "green",
        "signal": "rules",
        "secs": 0.3,
        "cost": 0.0,
    },
    {
        "path": "Matière.pdf",
        "leaf": "misc",
        "confidence": 0.4,
        "band": "yellow",
        "signal": "fallback",
        "top3": ["misc", "notes", "x"],
        "secs": 1.0,
        "cost": 0.002,
    },
]


@pytest.fixture
def report(load_script):
    return load_script("eval").evaluate(GOLDEN, PREDS)


def test_overall_metrics(report):
    overall = report["overall"]
    assert overall["n"] == 4
    assert overall["accuracy"] == pytest.approx(0.25)
    assert overall["green_precision"] == pytest.approx(0.5)
    assert overall["green_coverage"] == pytest.approx(0.5)
    assert overall["yellow_share"] == pytest.approx(0.25)
    assert overall["red_share"] == pytest.approx(0.25)
    assert overall["top3_hit"] == pytest.approx(1.0)
    assert overall["max_coverage_at_98"] == pytest.approx(0.25)
    assert overall["p50_secs"] == pytest.approx(0.3)
    assert overall["p95_secs"] == pytest.approx(1.0)
    assert overall["cost_per_1000"] == pytest.approx(0.5)
    assert report["missing_predictions"] == 1


def test_nfd_golden_path_joins_nfc_prediction(report):
    assert report["kinds"]["knowledge"]["top3_hit"] == pytest.approx(1.0)
    assert report["kinds"]["knowledge"]["yellow_share"] == pytest.approx(1.0)


def test_per_kind_metrics(report):
    assert report["kinds"]["record"]["n"] == 2
    assert report["kinds"]["record"]["accuracy"] == pytest.approx(0.5)
    assert report["kinds"]["library"]["red_share"] == pytest.approx(1.0)


def test_per_signal_curve(report):
    rules = report["signals"]["rules"]
    assert rules["curve"] == [
        pytest.approx((0.9, 1.0, 0.5)),
        pytest.approx((0.6, 0.5, 1.0)),
    ]
    assert rules["max_coverage_at_98"] == pytest.approx(0.5)


def test_main_renders_markdown_and_filters_to_predicted(load_script, tmp_path: Path, capsys):
    module = load_script("eval")
    golden, preds = tmp_path / "golden.jsonl", tmp_path / "preds.jsonl"
    golden.write_text("".join(json.dumps(row) + "\n" for row in GOLDEN))
    preds.write_text("".join(json.dumps(row) + "\n" for row in PREDS))
    assert module.main(["--golden", str(golden), "--pred", str(preds), "--only-predicted"]) == 0
    output = capsys.readouterr().out
    assert "| overall | 3 |" in output
    assert "| record |" in output
    assert module.main(["--golden", str(golden), "--pred", str(preds), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["overall"]["n"] == 4
