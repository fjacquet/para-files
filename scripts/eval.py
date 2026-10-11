"""Score predictions against the golden corpus, per kind and per signal (spec §4.5).

Usage:
    uv run python scripts/eval.py --pred ~/.config/para-files/pred_baseline.jsonl
    uv run python scripts/eval.py --pred ~/.config/para-files/pred_jev.jsonl --only-predicted
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from para_inventory import nfc, read_jsonl
from para_files.core.tree import config_dir


TARGET_PRECISION = 0.98
PCT = (
    "accuracy",
    "green_precision",
    "green_coverage",
    "yellow_share",
    "red_share",
    "top3_hit",
    "max_coverage_at_98",
)
COLUMNS = ("n", *PCT, "p50_secs", "p95_secs", "cost_per_1000")


def key(path: str) -> str:
    """Join key for paths: NFC, so NFD names from macOS volumes still match."""
    return nfc(path)


def _number(value: Any) -> float:
    """A confidence as a float; a missing (null) value counts as 0.0."""
    return 0.0 if value is None else float(value)


def _quantile(values: list[float], q: float) -> float:
    """Nearest-rank quantile of sorted values: the value at index int(q * n), capped at n - 1.

    For an even n the median is therefore the upper of the two middle values.
    """
    return values[min(len(values) - 1, int(q * len(values)))]


def _candidates(pred: dict[str, Any]) -> list[str]:
    """Top-3 leaf ids of a prediction, or its leaf alone when it lists no top-3."""
    return pred.get("top3") or ([pred["leaf"]] if pred.get("leaf") else [])


def curve(rows: list[dict[str, Any]]) -> list[tuple[float, float, float]]:
    """(threshold, precision, coverage) at each distinct confidence of decided rows.

    Knowledge rows are left out: they are suggestions only (top-3), never decided. Coverage is
    relative to the record, library and media rows of the given set.
    """
    scored = [r for r in rows if r["gold"]["kind"] != "knowledge"]
    n = len(scored)
    decided = [r for r in scored if r["pred"].get("leaf")]
    ranked = sorted(decided, key=lambda r: -_number(r["pred"].get("confidence")))
    points: list[tuple[float, float, float]] = []
    correct = 0
    for index, row in enumerate(ranked, 1):
        correct += row["pred"]["leaf"] == row["gold"]["leaf"]
        confidence = _number(row["pred"].get("confidence"))
        following = ranked[index]["pred"].get("confidence") if index < len(ranked) else None
        if following is None or _number(following) != confidence:
            points.append((confidence, correct / index, index / n))
    return points


def max_coverage(
    points: list[tuple[float, float, float]], target: float = TARGET_PRECISION
) -> float:
    """Largest coverage among curve points whose precision reaches target."""
    return max((cov for _, precision, cov in points if precision >= target), default=0.0)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Metrics for a set of joined {"gold", "pred"} rows."""
    n = len(rows)
    if n == 0:
        return {"n": 0}
    green = [r for r in rows if r["pred"].get("band") == "green"]
    green_ok = sum(r["pred"].get("leaf") == r["gold"]["leaf"] for r in green)
    predicted = [r for r in rows if "path" in r["pred"]]
    secs = sorted(float(r["pred"]["secs"]) for r in predicted if r["pred"].get("secs") is not None)
    cost = sum(float(r["pred"].get("cost", 0.0) or 0.0) for r in predicted)
    return {
        "n": n,
        "accuracy": sum(r["pred"].get("leaf") == r["gold"]["leaf"] for r in rows) / n,
        "green_precision": green_ok / len(green) if green else None,
        "green_coverage": len(green) / n,
        "yellow_share": sum(r["pred"].get("band") == "yellow" for r in rows) / n,
        "red_share": sum(r["pred"].get("band", "red") == "red" for r in rows) / n,
        "top3_hit": sum(r["gold"]["leaf"] in _candidates(r["pred"]) for r in rows) / n,
        "max_coverage_at_98": max_coverage(curve(rows)),
        "p50_secs": _quantile(secs, 0.5) if secs else None,
        "p95_secs": _quantile(secs, 0.95) if secs else None,
        "cost_per_1000": cost / len(predicted) * 1000 if predicted else None,
    }


def evaluate(golden: list[dict[str, Any]], preds: list[dict[str, Any]]) -> dict[str, Any]:
    """Join predictions to golden rows by NFC path and compute all metrics.

    Per-signal metrics are relative to that signal's own rows (used to set its band threshold);
    each signal block also reports top-3 over its own rows. Knowledge is scored as suggestions
    only: its kind block reports top-3 alone and the precision curves leave knowledge rows out. The first prediction for a path
    wins; later ones are counted as duplicates, and predictions with no golden row as unmatched.
    """
    by_path: dict[str, dict[str, Any]] = {}
    duplicates = 0
    for pred in preds:
        if key(pred["path"]) in by_path:
            duplicates += 1
        else:
            by_path[key(pred["path"])] = pred
    golden_keys = {key(g["path"]) for g in golden}
    rows = [{"gold": g, "pred": by_path.get(key(g["path"]), {"band": "red"})} for g in golden]
    report: dict[str, Any] = {"overall": summarize(rows), "kinds": {}, "signals": {}}
    for kind in sorted({g["kind"] for g in golden}):
        stats = summarize([r for r in rows if r["gold"]["kind"] == kind])
        if kind == "knowledge":  # suggestions only: top-3 is the one figure reported
            stats = {**stats, **{column: None for column in PCT if column != "top3_hit"}}
        report["kinds"][kind] = stats
    for signal in sorted({r["pred"]["signal"] for r in rows if r["pred"].get("signal")}):
        subset = [r for r in rows if r["pred"].get("signal") == signal]
        report["signals"][signal] = {**summarize(subset), "curve": curve(subset)}
    report["missing_predictions"] = sum(1 for r in rows if "path" not in r["pred"])
    report["duplicate_predictions"] = duplicates
    report["unmatched_predictions"] = sum(1 for k in by_path if k not in golden_keys)
    return report


def _cell(column: str, value: Any) -> str:
    if value is None:
        return "-"
    if column in PCT:
        return f"{value:.1%}"
    if column == "n":
        return str(value)
    return f"{value:.2f}"


def render(report: dict[str, Any]) -> str:
    """Markdown table: overall, each kind, each signal."""
    lines = ["| scope | " + " | ".join(COLUMNS) + " |", "|" + "---|" * (len(COLUMNS) + 1)]
    scopes = [
        ("overall", report["overall"]),
        *report["kinds"].items(),
        *((f"signal:{name}", stats) for name, stats in report["signals"].items()),
    ]
    for name, stats in scopes:
        if stats.get("n"):
            cells = " | ".join(_cell(column, stats.get(column)) for column in COLUMNS)
            lines.append(f"| {name} | {cells} |")
    lines.append(f"\nmissing predictions: {report['missing_predictions']}")
    lines.append(f"duplicate predictions: {report['duplicate_predictions']}")
    lines.append(f"unmatched predictions: {report['unmatched_predictions']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Print the report as Markdown (default) or JSON; return 0."""
    parser = argparse.ArgumentParser(description="Score predictions against the golden corpus.")
    parser.add_argument("--golden", type=Path, default=None)
    parser.add_argument("--pred", type=Path, required=True)
    parser.add_argument("--only-predicted", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    golden = read_jsonl(args.golden or config_dir() / "golden.jsonl")
    preds = read_jsonl(args.pred)
    if args.only_predicted:
        predicted = {key(p["path"]) for p in preds}
        golden = [g for g in golden if key(g["path"]) in predicted]
    report = evaluate(golden, preds)
    print(json.dumps(report, indent=2) if args.json else render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
