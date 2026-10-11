"""Apply a plan (spec §4.3): sequential, contained, never overwriting, journaled per operation."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from para_files.core.decide import Decision
from para_files.core.evidence import sha256_of
from para_files.core.journal import DecidedBy, Journal
from para_files.core.tree import TreeConfig
from para_files.utils.filename_sanitizer import sanitize_filename


TRASH = ".trash"
MAX_SUFFIX = 1000


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


def free_path(path: Path) -> Path:
    """path, or 'stem (2).ext', 'stem (3).ext'… whichever does not exist yet."""
    if not path.exists():
        return path
    for number in range(2, MAX_SUFFIX):
        candidate = path.with_name(f"{path.stem} ({number}){path.suffix}")
        if not candidate.exists():
            return candidate
    msg = f"no free name for {path}"
    raise FileExistsError(msg)


class _Applier:
    def __init__(self, config: TreeConfig, para_root: Path, journal: Journal) -> None:
        self.config = config
        self.root = para_root.resolve()
        self.journal = journal
        self.report = ApplyReport()

    def inside(self, path: Path) -> bool:
        return path.resolve().is_relative_to(self.root)

    def makedirs(self, directory: Path) -> None:
        missing: list[Path] = []
        current = directory
        while not current.exists():
            missing.append(current)
            current = current.parent
        for path in reversed(missing):
            path.mkdir()
            self.journal.append({"op": "mkdir", "dst": str(path)})

    def record(self, name: str, op: Op, src: Path, dst: Path) -> None:
        decision = op.decision
        self.journal.append(
            {
                "op": name,
                "src": str(src),
                "dst": str(dst),
                "sha256": decision.sha256,
                "size": dst.stat().st_size,
                "leaf": op.leaf_id,
                "proposed_leaf": decision.leaf_id,
                "decided_by": op.decided_by,
                "signal": decision.signal,
                "confidence": decision.confidence,
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
        return self.root / self.config.tree.leaves[op.leaf_id].path

    def apply(self, op: Op) -> None:
        src = op.decision.path
        reason = self.refusal(op)
        target = self.target(op) if reason is None else None
        if target is not None and not self.inside(target):
            reason = "target outside the PARA root"
        suggested = op.decision.suggested_name
        name = sanitize_filename(suggested, preserve_extension=True) if suggested else src.name
        if (
            target is not None
            and reason is None
            and src.parent.resolve() == target.resolve()
            and name == src.name
        ):
            reason = "already in place"
        if reason is not None or target is None:
            self.report.skipped.append((src, reason or "no target"))
            return
        dst = target / name
        if dst.is_file() and sha256_of(dst) == op.decision.sha256:
            self.trash(op, src)
            return
        self.makedirs(target)
        dst = free_path(dst)
        shutil.move(src, dst)
        self.record("move", op, src, dst)
        self.report.moved.append((src, dst))

    def trash(self, op: Op, src: Path) -> None:
        relative = src.resolve().relative_to(self.root) if self.inside(src) else Path(src.name)
        dst = free_path(self.root / TRASH / self.journal.run_id / relative)
        self.makedirs(dst.parent)
        shutil.move(src, dst)
        self.record("trash", op, src, dst)
        self.report.trashed.append((src, dst))

    def remove_emptied(self, roots: Sequence[Path]) -> None:
        bases = [root.resolve() for root in roots]
        sources = {src.parent.resolve() for src, _ in self.report.moved + self.report.trashed}
        for directory in sorted(sources, key=lambda path: len(path.parts), reverse=True):
            current = directory
            while (
                any(current != base and current.is_relative_to(base) for base in bases)
                and current.is_dir()
                and not any(current.iterdir())
            ):
                current.rmdir()
                self.journal.append({"op": "rmdir", "dst": str(current)})
                self.report.removed_dirs.append(current)
                current = current.parent


def apply_ops(
    ops: Sequence[Op],
    *,
    config: TreeConfig,
    para_root: Path,
    journal: Journal,
    roots: Sequence[Path],
) -> ApplyReport:
    """Run every operation in order, then remove folders this run emptied inside roots."""
    applier = _Applier(config, para_root, journal)
    for op in ops:
        applier.apply(op)
    applier.remove_emptied(roots)
    return applier.report
