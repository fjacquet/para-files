"""Sample the golden corpus from the owner-approved tree (spec §4.5). Read-only on PARA.

Writes <config dir>/golden.jsonl with lines {"path": <relative to PARA root>, "leaf": id,
"kind": kind}. Secret-looking and hidden files are never sampled. Delete lines for ambiguous
files before running the baseline. An existing golden.jsonl is not overwritten unless --force is
passed, since it may hold those edits.

Usage:
    uv run python scripts/build_golden.py --para-root "$PARA" [--force]
"""

from __future__ import annotations

import argparse
import json
import os
import random
from collections import Counter
from pathlib import Path
from typing import Any, NamedTuple

from para_inventory import nfc

from para_files.core.secrets import secret_reason
from para_files.core.tree import TreeConfig, config_dir, load_tree_config


WALK_CAP = 2000


class Walk(NamedTuple):
    """One leaf's walk: candidate files, whether it stopped at WALK_CAP, unreadable folders."""

    files: list[Path]
    stopped_early: bool
    unreadable: list[str]


def _regular_file(path: Path) -> bool:
    """A regular file that is not a symlink; one that cannot be stat'ed does not count."""
    try:
        return path.is_file() and not path.is_symlink()
    except OSError:
        return False


def leaf_files(root: Path, excluded: set[str], rng: random.Random) -> Walk:
    """Candidate files under root, skipping hidden, secret-named (files and folders), symlinked
    and special files, and other leaves' folders.

    The walk stops after the folder in which WALK_CAP candidates are reached; stopped_early is
    set only when folders were left unvisited. Folders that cannot be read are listed.
    """
    found: list[Path] = []
    unreadable: list[str] = []
    if not root.is_dir():
        return Walk(found, stopped_early=False, unreadable=unreadable)

    def note_unreadable(error: OSError) -> None:
        unreadable.append(os.path.relpath(str(error.filename), root))

    walker = os.walk(root, onerror=note_unreadable)
    for dirpath, dirnames, filenames in walker:
        here = Path(dirpath)
        dirnames[:] = sorted(
            d
            for d in dirnames
            if not d.startswith(".")
            and secret_reason(d) is None
            and nfc(str(here / d)) not in excluded
        )
        rng.shuffle(dirnames)
        found += [
            here / name
            for name in sorted(filenames)
            if not name.startswith((".", "~$"))
            and secret_reason(name) is None
            and _regular_file(here / name)
        ]
        if len(found) >= WALK_CAP:
            return Walk(found, stopped_early=next(walker, None) is not None, unreadable=unreadable)
    return Walk(found, stopped_early=False, unreadable=unreadable)


def build_golden(
    para_root: Path, config: TreeConfig, *, per_leaf: int, knowledge_per_leaf: int, seed: int
) -> tuple[list[dict[str, Any]], list[str]]:
    """Up to per_leaf files per leaf (knowledge_per_leaf for knowledge leaves), plus notes."""
    leaf_dirs = {leaf_id: para_root / leaf.path for leaf_id, leaf in config.tree.leaves.items()}
    rows: list[dict[str, Any]] = []
    notes: list[str] = []
    root = para_root.resolve()
    for leaf_id, leaf in config.tree.leaves.items():
        if leaf_dirs[leaf_id].is_symlink():
            notes.append(f"leaf {leaf_id}: root is a symlink; skipped")
            continue
        if not leaf_dirs[leaf_id].resolve().is_relative_to(root):
            notes.append(f"leaf {leaf_id}: resolves outside the PARA root; skipped")
            continue
        rng = random.Random(f"{seed}:{leaf_id}")  # noqa: S311 - sampling, not security
        excluded = {nfc(str(path)) for other, path in leaf_dirs.items() if other != leaf_id}
        walk = leaf_files(leaf_dirs[leaf_id], excluded, rng)
        notes += [f"leaf {leaf_id}: unreadable folder skipped: {name}" for name in walk.unreadable]
        if walk.stopped_early:
            notes.append(
                f"leaf {leaf_id}: walk stopped at {WALK_CAP} files; "
                f"the sample covers part of {leaf.path}"
            )
        if not walk.files:
            notes.append(f"leaf {leaf_id}: no files under {leaf.path}")
            continue
        wanted = knowledge_per_leaf if leaf.kind == "knowledge" else per_leaf
        rows += [
            {"path": nfc(str(path.relative_to(para_root))), "leaf": leaf_id, "kind": leaf.kind}
            for path in sorted(rng.sample(walk.files, min(wanted, len(walk.files))))
        ]
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
    parser.add_argument("--force", action="store_true", help="overwrite an existing golden.jsonl")
    args = parser.parse_args(argv)
    para_root = args.para_root.expanduser().resolve()
    if not para_root.is_dir():
        parser.error(f"--para-root is not a directory: {para_root}")
    cfg_dir = args.config_dir.expanduser().resolve() if args.config_dir else config_dir()
    out = (args.out or cfg_dir / "golden.jsonl").expanduser().resolve()
    if out.is_relative_to(para_root):
        parser.error("--out must be outside the PARA root")
    if out.exists() and not args.force:
        parser.error(f"{out} exists and may hold your edits; pass --force to overwrite")
    rows, notes = build_golden(
        para_root,
        load_tree_config(cfg_dir),
        per_leaf=args.per_leaf,
        knowledge_per_leaf=args.knowledge_per_leaf,
        seed=args.seed,
    )
    if not rows:
        print(*notes, sep="\n")
        parser.error("no files sampled; nothing written")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    for kind, count in sorted(Counter(row["kind"] for row in rows).items()):
        print(f"{count:5}  {kind}")
    print(*notes, sep="\n")
    print(f"golden -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
