"""Score predictions against the golden corpus, per kind and per signal (spec §4.5).

Usage:
    uv run python scripts/eval.py --pred ~/.config/para-files/pred_baseline.jsonl
    uv run python scripts/eval.py --pred ~/.config/para-files/pred_jev.jsonl --only-predicted
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path
from typing import Any

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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Rows of a JSONL file."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def key(path: str) -> str:
    """Join key for paths: NFC, so NFD names from macOS volumes still match."""
    return unicodedata.normalize("NFC", path)


def _quantile(values: list[float], q: float) -> float:
    return values[min(len(values) - 1, int(q * len(values)))]


def _candidates(pred: dict[str, Any]) -> list[str]:
    """Top-3 leaf ids of a prediction, or its leaf alone when it lists no top-3."""
    return pred.get("top3") or ([pred["leaf"]] if pred.get("leaf") else [])


def curve(rows: list[dict[str, Any]], n: int) -> list[tuple[float, float, float]]:
    """(threshold, precision, coverage of n) at each distinct confidence of decided rows."""
    decided = [r for r in rows if r["pred"].get("leaf")]
    ranked = sorted(decided, key=lambda r: -float(r["pred"].get("confidence", 0.0)))
    points: list[tuple[float, float, float]] = []
    correct = 0
    for index, row in enumerate(ranked, 1):
        correct += row["pred"]["leaf"] == row["gold"]["leaf"]
        confidence = float(row["pred"].get("confidence", 0.0))
        following = ranked[index]["pred"].get("confidence") if index < len(ranked) else None
        if following is None or float(following) != confidence:
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
        "max_coverage_at_98": max_coverage(curve(rows, n)),
        "p50_secs": _quantile(secs, 0.5) if secs else None,
        "p95_secs": _quantile(secs, 0.95) if secs else None,
        "cost_per_1000": cost / len(predicted) * 1000 if predicted else None,
    }


def evaluate(golden: list[dict[str, Any]], preds: list[dict[str, Any]]) -> dict[str, Any]:
    """Join predictions to golden rows by NFC path and compute all metrics.

    Per-signal metrics are relative to that signal's own rows (used to set its band threshold);
    top-3 candidates are compared on the overall and per-kind rows.
    """
    by_path = {key(p["path"]): p for p in preds}
    rows = [{"gold": g, "pred": by_path.get(key(g["path"]), {"band": "red"})} for g in golden]
    report: dict[str, Any] = {"overall": summarize(rows), "kinds": {}, "signals": {}}
    for kind in sorted({g["kind"] for g in golden}):
        report["kinds"][kind] = summarize([r for r in rows if r["gold"]["kind"] == kind])
    for signal in sorted({r["pred"]["signal"] for r in rows if r["pred"].get("signal")}):
        subset = [r for r in rows if r["pred"].get("signal") == signal]
        report["signals"][signal] = {**summarize(subset), "curve": curve(subset, len(subset))}
    report["missing_predictions"] = sum(1 for r in rows if "path" not in r["pred"])
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
