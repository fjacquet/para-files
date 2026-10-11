"""Undo a run (spec §4.3): replay its journal newest first, checking every step."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from para_files.core.evidence import sha256_of
from para_files.core.journal import (
    RUN_ID_PATTERN,
    is_undone,
    journal_dir,
    last_run_id,
    mark_undone,
    read_run,
)


class UndoError(RuntimeError):
    """The run cannot be undone (unknown, or already undone)."""


@dataclass
class UndoReport:
    """What undo restored, recreated and removed, and what it left alone and why."""

    run_id: str
    restored: list[Path] = field(default_factory=list)
    recreated: list[Path] = field(default_factory=list)
    removed_dirs: list[Path] = field(default_factory=list)
    kept_dirs: list[Path] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)


def _already_restored(dst: Path, src: Path, sha256: str) -> bool:
    """dst is gone and src is a regular file with the recorded content (a retried undo)."""
    return not dst.exists() and src.is_file() and not src.is_symlink() and sha256_of(src) == sha256


def _blocked(dst: Path, src: Path, sha256: str) -> str | None:
    if not dst.is_file():
        return "missing"
    if sha256_of(dst) != sha256:
        return "changed since the run"
    if src.exists() or src.is_symlink():
        return "source path taken"
    return None


def _undo_entry(entry: dict[str, Any], report: UndoReport) -> None:
    op, dst = entry.get("op"), Path(entry["dst"])
    if op == "rmdir":
        dst.mkdir(parents=True, exist_ok=True)
        report.recreated.append(dst)
    elif op == "mkdir":
        if dst.is_dir() and not any(dst.iterdir()):
            dst.rmdir()
            report.removed_dirs.append(dst)
        elif dst.exists():
            report.kept_dirs.append(dst)
    elif op in {"move", "trash"}:
        src = Path(entry["src"])
        if _already_restored(dst, src, entry["sha256"]):
            return
        reason = _blocked(dst, src, entry["sha256"])
        if reason is not None:
            report.skipped.append((str(dst), reason))
            return
        src.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(dst, src)
        report.restored.append(src)


def undo_run(state_dir: Path, run_id: str | None = None) -> UndoReport:
    """Undo one run (default: the last one not undone) and mark it undone."""
    if run_id is not None and RUN_ID_PATTERN.fullmatch(run_id) is None:
        msg = f"not a run id: {run_id}"
        raise UndoError(msg)
    target = run_id or last_run_id(state_dir)
    if target is None:
        msg = "no run to undo"
        raise UndoError(msg)
    if not (journal_dir(state_dir) / f"{target}.jsonl").exists():
        msg = f"no journal for run {target}"
        raise UndoError(msg)
    if is_undone(state_dir, target):
        msg = f"run {target} was already undone"
        raise UndoError(msg)
    report = UndoReport(target)
    for entry in reversed(read_run(state_dir, target)):
        _undo_entry(entry, report)
    if not report.skipped:
        mark_undone(state_dir, target)
    return report
