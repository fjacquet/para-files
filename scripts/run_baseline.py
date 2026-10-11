"""Baseline: the old pipeline over the golden corpus, written as predictions for eval.py.

The old pipeline runs with the semantic classifier and the LLM off, so it uses books, rules,
taxonomy and the extension router. OCR rename is off and patched out. Each file is classified
through a symlink in a temporary folder, so its PARA location cannot leak into the decision.
Read-only on PARA.

Usage:
    uv run python scripts/run_baseline.py --para-root "$PARA"
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from para_inventory import make_canon, nfc, retentions_by_stem, scan_folders

from para_files.core.tree import Tree, config_dir, load_tree_config


Classify = Callable[[Path], tuple[str, float, str]]


def leaf_for_category(category: str, tree: Tree, canon: Callable[[str], str]) -> str | None:
    """Most specific leaf whose path contains the old pipeline's category path."""
    parts = [nfc(part).strip() for part in category.split("/") if part.strip()]
    if len(parts) < 2:
        return None
    path = "/".join([canon("/".join(parts[:2])), *parts[2:]])
    best: str | None = None
    for leaf_id, leaf in tree.leaves.items():
        inside = path == leaf.path or path.startswith(leaf.path + "/")
        if inside and (best is None or len(leaf.path) > len(tree.leaves[best].path)):
            best = leaf_id
    return best


def old_pipeline_classifier() -> Classify:
    """The old pipeline with semantic, LLM and OCR rename disabled."""
    os.environ.update(
        PARA_FILES_MLX_SEMANTIC_ENABLED="false",
        PARA_FILES_LLM_ENABLED="false",
        PARA_FILES_OCR_RENAME__ENABLED="false",
    )
    from para_files.config import load_config
    from para_files.pipeline import ClassificationPipeline

    pipeline = ClassificationPipeline(load_config())
    pipeline._maybe_rename_generic_pdf = lambda path: path  # never rename during a measurement

    def classify(path: Path) -> tuple[str, float, str]:
        result = pipeline.classify_file(path)
        return result.category, result.confidence.value, str(result.confidence.source)

    return classify


def run_baseline(
    para_root: Path,
    golden: list[dict[str, Any]],
    tree: Tree,
    canon: Callable[[str], str],
    classify: Classify,
    workdir: Path,
) -> list[dict[str, Any]]:
    """One prediction per golden row; a failing file becomes a red row."""
    preds: list[dict[str, Any]] = []
    for index, row in enumerate(golden):
        source = para_root / row["path"]
        link = workdir / str(index) / source.name
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(source)
        start = time.monotonic()
        try:
            category, confidence, signal = classify(link)
            leaf = leaf_for_category(category, tree, canon)
        except Exception as exc:  # noqa: BLE001 - one unreadable file must not stop the run
            category, confidence, signal, leaf = f"error: {type(exc).__name__}", 0.0, "error", None
        preds.append(
            {
                "path": row["path"],
                "leaf": leaf,
                "confidence": confidence if leaf else 0.0,
                "band": "green" if leaf else "red",
                "signal": signal,
                "raw": category,
                "secs": round(time.monotonic() - start, 3),
                "cost": 0.0,
            }
        )
    return preds


def main(argv: list[str] | None = None) -> int:
    """Write pred_baseline.jsonl next to the golden corpus; return 0."""
    parser = argparse.ArgumentParser(description="Run the old pipeline over the golden corpus.")
    parser.add_argument("--para-root", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=None)
    parser.add_argument("--documents", type=Path, default=Path("config/documents.json"))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    para_root = args.para_root.expanduser().resolve()
    cfg_dir = args.config_dir or config_dir()
    out = (args.out or cfg_dir / "pred_baseline.jsonl").expanduser().resolve()
    if out.is_relative_to(para_root):
        parser.error("--out must be outside the PARA root")
    golden = [json.loads(line) for line in (cfg_dir / "golden.jsonl").read_text().splitlines()]
    tree = load_tree_config(cfg_dir).tree
    taxonomy = retentions_by_stem(json.loads(args.documents.read_text(encoding="utf-8")))
    canon = make_canon(scan_folders(para_root), taxonomy)  # same canonical map as the seeder
    with tempfile.TemporaryDirectory() as workdir:
        preds = run_baseline(
            para_root, golden, tree, canon, old_pipeline_classifier(), Path(workdir)
        )
    out.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in preds), "utf-8")
    decided = sum(1 for p in preds if p["leaf"])
    print(f"baseline: {decided}/{len(preds)} decided -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
