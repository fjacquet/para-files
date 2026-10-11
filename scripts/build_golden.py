"""Sample the golden corpus from the owner-approved tree (spec §4.5). Read-only on PARA.

Writes <config dir>/golden.jsonl with lines {"path": <relative to PARA root>, "leaf": id,
"kind": kind}. Secret-looking and hidden files are never sampled. Delete lines for ambiguous
files before running the baseline.

Usage:
    uv run python scripts/build_golden.py --para-root "$PARA"
"""

from __future__ import annotations

import argparse
import json
import os
import random
from collections import Counter
from pathlib import Path
from typing import Any

from para_inventory import nfc

from para_files.core.secrets import secret_reason
from para_files.core.tree import TreeConfig, config_dir, load_tree_config


WALK_CAP = 2000


def leaf_files(root: Path, excluded: set[str], rng: random.Random) -> list[Path]:
    """Candidate files under root, skipping hidden, secret-named and other leaves' folders.

    The walk stops after the folder in which WALK_CAP candidates are reached.
    """
    found: list[Path] = []
    if not root.is_dir():
        return found
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        dirnames[:] = sorted(
            d for d in dirnames if not d.startswith(".") and nfc(str(here / d)) not in excluded
        )
        rng.shuffle(dirnames)
        found += [
            here / name
            for name in sorted(filenames)
            if not name.startswith((".", "~$")) and secret_reason(name) is None
        ]
        if len(found) >= WALK_CAP:
            break
    return found


def build_golden(
    para_root: Path, config: TreeConfig, *, per_leaf: int, knowledge_per_leaf: int, seed: int
) -> tuple[list[dict[str, Any]], list[str]]:
    """Up to per_leaf files per leaf (knowledge_per_leaf for knowledge leaves), plus notes."""
    rng = random.Random(seed)  # noqa: S311 - sampling, not security
    leaf_dirs = {leaf_id: para_root / leaf.path for leaf_id, leaf in config.tree.leaves.items()}
    rows: list[dict[str, Any]] = []
    notes: list[str] = []
    for leaf_id, leaf in config.tree.leaves.items():
        excluded = {nfc(str(path)) for other, path in leaf_dirs.items() if other != leaf_id}
        files = leaf_files(leaf_dirs[leaf_id], excluded, rng)
        if not files:
            notes.append(f"leaf {leaf_id}: no files under {leaf.path}")
            continue
        wanted = knowledge_per_leaf if leaf.kind == "knowledge" else per_leaf
        for path in sorted(rng.sample(files, min(wanted, len(files)))):
            rows.append(
                {"path": nfc(str(path.relative_to(para_root))), "leaf": leaf_id, "kind": leaf.kind}
            )
    return rows, notes


def main(argv: list[str] | None = None) -> int:
    """Write golden.jsonl and print counts per kind; return 0."""
    parser = argparse.ArgumentParser(description="Sample the golden corpus.")
    parser.add_argument("--para-root", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=None)
    parser.add_argument("--per-leaf", type=int, default=10)
    parser.add_argument("--knowledge-per-leaf", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    para_root = args.para_root.expanduser().resolve()
    cfg_dir = args.config_dir or config_dir()
    out = (args.out or cfg_dir / "golden.jsonl").expanduser().resolve()
    if out.is_relative_to(para_root):
        parser.error("--out must be outside the PARA root")
    rows, notes = build_golden(
        para_root,
        load_tree_config(cfg_dir),
        per_leaf=args.per_leaf,
        knowledge_per_leaf=args.knowledge_per_leaf,
        seed=args.seed,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    for kind, count in sorted(Counter(row["kind"] for row in rows).items()):
        print(f"{count:5}  {kind}")
    print(*notes, sep="\n")
    print(f"golden -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
