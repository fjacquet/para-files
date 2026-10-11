"""Apply a plan (spec §4.3): sequential, contained, never overwriting, journaled per operation."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from para_files.core.decide import Decision, fill_subkey, issuer_for
from para_files.core.evidence import sha256_of
from para_files.core.journal import DecidedBy, Journal
from para_files.core.tree import TreeConfig
from para_files.utils.filename_sanitizer import sanitize_filename


TRASH = ".trash"
MAX_SUFFIX = 1000
INVALID_NAMES = frozenset({"", ".", ".."})


@dataclass(frozen=True)
class Op:
    """One file to move: the decision, the final leaf (owner may correct it), who decided."""

    decision: Decision
    leaf_id: str
    decided_by: DecidedBy


@dataclass
class ApplyReport:
    """What a run did and what it refused, with reasons."""

    moved: list[tuple[Path, Path]] = field(default_factory=list)
    trashed: list[tuple[Path, Path]] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    removed_dirs: list[Path] = field(default_factory=list)


def _taken(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def free_path(path: Path) -> Path:
    """path, or 'stem (2).ext', 'stem (3).ext'… whichever is not taken yet (links count)."""
    if not _taken(path):
        return path
    for number in range(2, MAX_SUFFIX):
        candidate = path.with_name(f"{path.stem} ({number}){path.suffix}")
        if not _taken(candidate):
            return candidate
    msg = f"no free name for {path}"
    raise FileExistsError(msg)


def make_dirs(directory: Path, journal: Journal) -> None:
    """Create directory and its missing parents, journaling each mkdir before it happens."""
    missing: list[Path] = []
    current = directory
    while not current.exists():
        missing.append(current)
        current = current.parent
    for path in reversed(missing):
        journal.append({"op": "mkdir", "dst": str(path)})
        path.mkdir()


def trash_file(src: Path, root: Path, journal: Journal, entry: dict[str, Any]) -> Path:
    """Move src to <root>/.trash/<run id>/<its path below root>, journaled; return the new path.

    root must be resolved. A src outside root keeps only its file name. entry holds the journal
    fields beyond op, src, dst and size.
    """
    resolved = src.resolve()
    relative = resolved.relative_to(root) if resolved.is_relative_to(root) else Path(src.name)
    dst = free_path(root / TRASH / journal.run_id / relative)
    make_dirs(dst.parent, journal)
    journal.append(
        {"op": "trash", "src": str(src), "dst": str(dst), "size": src.stat().st_size, **entry}
    )
    shutil.move(src, dst)
    return dst


class _Applier:
    def __init__(self, config: TreeConfig, para_root: Path, journal: Journal) -> None:
        self.config = config
        self.root = para_root.resolve()
        self.journal = journal
        self.report = ApplyReport()

    def inside(self, path: Path) -> bool:
        return path.resolve().is_relative_to(self.root)

    def contained(self, dst: Path, target: Path) -> bool:
        return dst.parent.resolve() == target.resolve() and self.inside(dst)

    def name(self, op: Op) -> str:
        suggested = op.decision.suggested_name
        if suggested:
            return sanitize_filename(suggested, preserve_extension=True)
        return op.decision.path.name

    @staticmethod
    def fields(op: Op) -> dict[str, Any]:
        decision = op.decision
        return {
            "sha256": decision.sha256,
            "leaf": op.leaf_id,
            "proposed_leaf": decision.leaf_id,
            "decided_by": op.decided_by,
            "signal": decision.signal,
            "confidence": decision.confidence,
        }

    def record(self, name: str, op: Op, src: Path, dst: Path) -> None:
        self.journal.append(
            {
                "op": name,
                "src": str(src),
                "dst": str(dst),
                "size": src.stat().st_size,
                **self.fields(op),
            }
        )

    def refusal(self, op: Op) -> str | None:
        src = op.decision.path
        if op.decision.signal == "secret":
            return "secret"
        if op.leaf_id not in self.config.tree.leaves:
            return f"unknown leaf {op.leaf_id!r}"
        if src.is_symlink() or not src.is_file():
            return "source missing"
        if sha256_of(src) != op.decision.sha256:
            return "changed since the preview"
        return None

    def target(self, op: Op) -> Path:
        decision = op.decision
        if op.leaf_id == decision.leaf_id and decision.target_dir:
            return self.root / decision.target_dir
        leaf = self.config.tree.leaves[op.leaf_id]
        issuer = issuer_for(op.leaf_id, decision.issuer, self.config)
        return self.root / fill_subkey(leaf, (*decision.fill, ("{issuer}", issuer)))

    def apply(self, op: Op) -> None:
        src = op.decision.path
        reason = self.refusal(op)
        target = self.target(op) if reason is None else None
        if target is not None and not self.inside(target):
            reason = "target outside the PARA root"
        name = self.name(op)
        if reason is None and name.strip() in INVALID_NAMES:
            reason = "invalid file name"
        if (
            target is not None
            and reason is None
            and src.parent.resolve() == target.resolve()
            and name == src.name
        ):
            reason = "already in place"
            if op.decided_by == "owner":
                self.record("confirm", op, src, src)
        if reason is not None or target is None:
            self.report.skipped.append((src, reason or "no target"))
            return
        dst = target / name
        if dst.is_file() and sha256_of(dst) == op.decision.sha256:
            self.trash(op, src)
            return
        dst = free_path(dst)
        if not self.contained(dst, target):
            self.report.skipped.append((src, "target outside the PARA root"))
            return
        make_dirs(target, self.journal)
        self.record("move", op, src, dst)
        shutil.move(src, dst)
        self.report.moved.append((src, dst))

    def trash(self, op: Op, src: Path) -> None:
        dst = trash_file(src, self.root, self.journal, self.fields(op))
        self.report.trashed.append((src, dst))

    def remove_emptied(self, roots: Sequence[Path], keep: frozenset[Path]) -> None:
        bases = [root.resolve() for root in roots]
        kept = {path.resolve() for path in keep}
        sources = {src.parent.resolve() for src, _ in self.report.moved + self.report.trashed}
        for directory in sorted(sources, key=lambda path: len(path.parts), reverse=True):
            current = directory
            while (
                any(current != base and current.is_relative_to(base) for base in bases)
                and current not in kept
                and current.is_dir()
                and not any(current.iterdir())
            ):
                self.journal.append({"op": "rmdir", "dst": str(current)})
                current.rmdir()
                self.report.removed_dirs.append(current)
                current = current.parent


def apply_ops(
    ops: Sequence[Op],
    *,
    config: TreeConfig,
    para_root: Path,
    journal: Journal,
    roots: Sequence[Path],
    keep: frozenset[Path] = frozenset(),
) -> ApplyReport:
    """Run every operation in order, then remove folders this run emptied inside roots.

    Folders in keep (bucket and leaf folders) are never removed.
    """
    applier = _Applier(config, para_root, journal)
    for op in ops:
        applier.apply(op)
    applier.remove_emptied(roots, keep)
    return applier.report
