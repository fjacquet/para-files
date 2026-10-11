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
    assert overall["top3_hit"] == pytest.approx(0.5)
    assert overall["max_coverage_at_98"] == pytest.approx(0.25)
    assert overall["p50_secs"] == pytest.approx(0.3)
    assert overall["p95_secs"] == pytest.approx(1.0)
    assert overall["cost_per_1000"] == pytest.approx(0.002 / 3 * 1000)
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


def test_latency_ignores_unpredicted_files(load_script):
    golden = [
        {"path": "a.pdf", "leaf": "inv", "kind": "record"},
        {"path": "b.pdf", "leaf": "inv", "kind": "record"},
        {"path": "c.pdf", "leaf": "books", "kind": "library"},
    ]
    preds = [
        {
            "path": "a.pdf",
            "leaf": "inv",
            "confidence": 0.9,
            "band": "green",
            "signal": "rules",
            "secs": 2.0,
            "cost": 0.0,
        },
    ]
    overall = load_script("eval").evaluate(golden, preds)["overall"]
    assert overall["p50_secs"] == pytest.approx(2.0)
    assert overall["p95_secs"] == pytest.approx(2.0)


def test_top3_counts_unanswered_files(load_script):
    golden = [
        {"path": "k1.pdf", "leaf": "notes", "kind": "knowledge"},
        {"path": "k2.pdf", "leaf": "notes", "kind": "knowledge"},
    ]
    preds = [
        {
            "path": "k1.pdf",
            "leaf": "misc",
            "confidence": 0.4,
            "band": "yellow",
            "signal": "fallback",
            "top3": ["misc", "notes"],
            "secs": 1.0,
            "cost": 0.0,
        },
    ]
    report = load_script("eval").evaluate(golden, preds)
    assert report["kinds"]["knowledge"]["top3_hit"] == pytest.approx(0.5)


def test_top3_falls_back_to_predicted_leaf(load_script):
    golden = [{"path": "k1.pdf", "leaf": "notes", "kind": "knowledge"}]
    preds = [
        {
            "path": "k1.pdf",
            "leaf": "notes",
            "confidence": 0.9,
            "band": "green",
            "signal": "rules",
            "secs": 0.1,
            "cost": 0.0,
        },
    ]
    report = load_script("eval").evaluate(golden, preds)
    assert report["kinds"]["knowledge"]["top3_hit"] == pytest.approx(1.0)


def test_curve_is_not_truncated(load_script):
    golden = [{"path": f"f{i}.pdf", "leaf": "inv", "kind": "record"} for i in range(25)]
    preds = [
        {
            "path": f"f{i}.pdf",
            "leaf": "inv",
            "confidence": 1.0 - i / 100,
            "band": "green",
            "signal": "rules",
            "secs": 0.1,
            "cost": 0.0,
        }
        for i in range(25)
    ]
    report = load_script("eval").evaluate(golden, preds)
    assert len(report["signals"]["rules"]["curve"]) == 25


def test_read_jsonl_skips_whitespace_only_lines(load_script, tmp_path: Path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"path": "a.pdf"}\n   \n\t\n{"path": "b.pdf"}\n', encoding="utf-8")
    assert [row["path"] for row in load_script("eval").read_jsonl(path)] == ["a.pdf", "b.pdf"]


def test_null_confidence_counts_as_zero_and_null_secs_as_missing(load_script):
    golden = [
        {"path": "a.pdf", "leaf": "inv", "kind": "record"},
        {"path": "b.pdf", "leaf": "inv", "kind": "record"},
    ]
    preds = [
        {
            "path": "a.pdf",
            "leaf": "inv",
            "confidence": None,
            "band": "green",
            "signal": "rules",
            "secs": None,
            "cost": None,
        },
        {
            "path": "b.pdf",
            "leaf": "inv",
            "confidence": 0.5,
            "band": "green",
            "signal": "rules",
            "secs": 0.2,
            "cost": 0.0,
        },
    ]
    report = load_script("eval").evaluate(golden, preds)
    assert report["overall"]["p50_secs"] == pytest.approx(0.2)
    assert report["signals"]["rules"]["curve"] == [
        pytest.approx((0.5, 1.0, 0.5)),
        pytest.approx((0.0, 1.0, 1.0)),
    ]


def test_duplicate_predictions_keep_first_and_are_counted(load_script):
    golden = [{"path": "a.pdf", "leaf": "inv", "kind": "record"}]
    preds = [
        {"path": "a.pdf", "leaf": "inv", "confidence": 0.9, "band": "green", "signal": "rules"},
        {"path": "a.pdf", "leaf": "other", "confidence": 0.1, "band": "red", "signal": "rules"},
        {"path": "zzz.pdf", "leaf": "inv", "confidence": 0.5, "band": "green", "signal": "rules"},
    ]
    report = load_script("eval").evaluate(golden, preds)
    assert report["duplicate_predictions"] == 1
    assert report["unmatched_predictions"] == 1
    assert report["overall"]["accuracy"] == pytest.approx(1.0)


def test_empty_golden_gives_empty_report(load_script):
    module = load_script("eval")
    report = module.evaluate([], [])
    assert report["overall"] == {"n": 0}
    assert report["kinds"] == {}
    assert report["signals"] == {}
    assert report["missing_predictions"] == 0
    assert "missing predictions: 0" in module.render(report)


def test_tied_confidences_form_one_curve_point(load_script):
    golden = [
        {"path": "a.pdf", "leaf": "inv", "kind": "record"},
        {"path": "b.pdf", "leaf": "inv", "kind": "record"},
    ]
    preds = [
        {"path": "a.pdf", "leaf": "inv", "confidence": 0.7, "band": "green", "signal": "rules"},
        {"path": "b.pdf", "leaf": "other", "confidence": 0.7, "band": "green", "signal": "rules"},
    ]
    report = load_script("eval").evaluate(golden, preds)
    assert report["signals"]["rules"]["curve"] == [pytest.approx((0.7, 0.5, 1.0))]
