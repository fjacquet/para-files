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
    assert overall["max_coverage_at_98"] == pytest.approx(1 / 3)  # record/library/media only
    assert overall["p50_secs"] == pytest.approx(0.3)
    assert overall["p95_secs"] == pytest.approx(1.0)
    assert overall["cost_per_1000"] == pytest.approx(0.002 / 3 * 1000)
    assert report["missing_predictions"] == 1


def test_nfd_golden_path_joins_nfc_prediction(report):
    assert report["kinds"]["knowledge"]["top3_hit"] == pytest.approx(1.0)
    assert report["kinds"]["knowledge"]["yellow_share"] is None  # suggestions only


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


def test_null_confidence_ties_form_one_curve_point(load_script):
    golden = [{"path": f"{name}.pdf", "leaf": "inv", "kind": "record"} for name in "abcd"]
    preds = [
        {
            "path": f"{name}.pdf",
            "leaf": leaf,
            "confidence": None,
            "band": "green",
            "signal": "rules",
        }
        for name, leaf in zip("abcd", ("inv", "inv", "inv", "other"), strict=True)
    ]
    report = load_script("eval").evaluate(golden, preds)
    assert report["signals"]["rules"]["curve"] == [pytest.approx((0.0, 0.75, 1.0))]
    assert report["overall"]["max_coverage_at_98"] == 0.0


def test_null_and_zero_confidence_tie_form_one_curve_point(load_script):
    golden = [
        {"path": "a.pdf", "leaf": "inv", "kind": "record"},
        {"path": "b.pdf", "leaf": "inv", "kind": "record"},
    ]
    preds = [
        {"path": "a.pdf", "leaf": "inv", "confidence": None, "band": "green", "signal": "rules"},
        {"path": "b.pdf", "leaf": "other", "confidence": 0.0, "band": "green", "signal": "rules"},
    ]
    report = load_script("eval").evaluate(golden, preds)
    assert report["signals"]["rules"]["curve"] == [pytest.approx((0.0, 0.5, 1.0))]


PCT_BUT_TOP3 = (
    "accuracy",
    "green_precision",
    "green_coverage",
    "yellow_share",
    "red_share",
    "max_coverage_at_98",
)


def test_knowledge_rows_are_suggestions_only(load_script):
    golden = [
        {"path": "a.pdf", "leaf": "inv", "kind": "record"},
        {"path": "k.md", "leaf": "notes", "kind": "knowledge"},
    ]
    preds = [
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
            "path": "k.md",
            "leaf": "notes",
            "confidence": 0.95,
            "band": "yellow",
            "signal": "fallback",
            "top3": ["notes"],
            "secs": 0.1,
            "cost": 0.0,
        },
    ]
    report = load_script("eval").evaluate(golden, preds)
    knowledge = report["kinds"]["knowledge"]
    assert knowledge["top3_hit"] == pytest.approx(1.0)
    assert all(knowledge[column] is None for column in PCT_BUT_TOP3)
    # The knowledge row sits outside the curve: only the record decides coverage.
    assert report["overall"]["max_coverage_at_98"] == pytest.approx(1.0)
    assert report["signals"]["rules"]["curve"] == [pytest.approx((0.9, 1.0, 1.0))]
    assert report["signals"]["fallback"]["curve"] == []


def test_drop_rule_combines_baseline_green_with_candidate_threshold(load_script):
    golden = [
        {"path": "a.pdf", "leaf": "inv", "kind": "record"},
        {"path": "b.pdf", "leaf": "inv", "kind": "record"},
        {"path": "c.pdf", "leaf": "books", "kind": "library"},
        {"path": "k.md", "leaf": "notes", "kind": "knowledge"},
    ]
    baseline = [
        {"path": "a.pdf", "leaf": "inv", "band": "green", "signal": "rules", "confidence": 0.9},
        {"path": "b.pdf", "leaf": None, "band": "red", "signal": "rules", "confidence": 0.0},
        {"path": "c.pdf", "leaf": None, "band": "red", "signal": "rules", "confidence": 0.0},
    ]
    candidate = [
        {"path": "b.pdf", "leaf": "inv", "confidence": 0.9, "band": "green", "signal": "llm"},
        {"path": "c.pdf", "leaf": "books", "confidence": 0.8, "band": "green", "signal": "llm"},
    ]
    report = load_script("eval").evaluate(golden, candidate, baseline)
    drop = report["drop_rule"]
    assert drop["baseline_green_coverage"] == pytest.approx(1 / 3)
    assert drop["candidate_threshold"] == pytest.approx(0.8)
    assert drop["combined_green_coverage"] == pytest.approx(1.0)
    assert drop["gain_over_baseline"] == pytest.approx((1.0 - 1 / 3) * 100)


def test_no_drop_rule_without_a_baseline(load_script):
    golden = [{"path": "a.pdf", "leaf": "inv", "kind": "record"}]
    report = load_script("eval").evaluate(golden, [])
    assert "drop_rule" not in report


def test_only_predicted_prints_subset_n_and_warns(load_script, tmp_path: Path, capsys):
    module = load_script("eval")
    golden, preds = tmp_path / "golden.jsonl", tmp_path / "preds.jsonl"
    golden.write_text("".join(json.dumps(row) + "\n" for row in GOLDEN))
    preds.write_text("".join(json.dumps(row) + "\n" for row in PREDS))
    module.main(["--golden", str(golden), "--pred", str(preds), "--only-predicted"])
    err = capsys.readouterr().err
    assert "3 of 4" in err
    assert "warning" in err.lower()


def test_only_predicted_with_full_coverage_has_no_warning(load_script, tmp_path: Path, capsys):
    module = load_script("eval")
    golden, preds = tmp_path / "golden.jsonl", tmp_path / "preds.jsonl"
    golden.write_text("".join(json.dumps(row) + "\n" for row in GOLDEN[:2]))
    preds.write_text("".join(json.dumps(row) + "\n" for row in PREDS[:2]))
    module.main(["--golden", str(golden), "--pred", str(preds), "--only-predicted"])
    err = capsys.readouterr().err
    assert "2 of 2" in err
    assert "warning" not in err.lower()


def test_main_renders_drop_rule_with_baseline(load_script, tmp_path: Path, capsys):
    module = load_script("eval")
    golden, preds, base = tmp_path / "g.jsonl", tmp_path / "p.jsonl", tmp_path / "b.jsonl"
    golden.write_text(json.dumps(GOLDEN[0]) + "\n")
    preds.write_text(json.dumps(PREDS[0]) + "\n")
    base.write_text(json.dumps({**PREDS[0], "band": "red", "leaf": None}) + "\n")
    argv = ["--golden", str(golden), "--pred", str(preds), "--baseline", str(base)]
    assert module.main(argv) == 0
    assert "drop rule: combined green coverage 100.0%" in capsys.readouterr().out
