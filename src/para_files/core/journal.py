"""Run journal (spec §4.3): one JSONL file per run, one flushed line per operation.

Owner-decided moves are the labels of spec §4.5: confirmed_counts() feeds the calibration cap.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Self

from para_files.core.tree import Tree


DecidedBy = Literal["auto", "owner"]
RUN_ID_FORMAT = "%Y%m%d-%H%M%S"


def journal_dir(state_dir: Path) -> Path:
    """Where run journals live."""
    return state_dir / "journal"


def new_run_id(state_dir: Path, now: datetime | None = None) -> str:
    """YYYYMMDD-HHMMSS (local time), with -2, -3… when already taken."""
    base = (now or datetime.now().astimezone()).strftime(RUN_ID_FORMAT)
    run_id, counter = base, 2
    while (journal_dir(state_dir) / f"{run_id}.jsonl").exists():
        run_id, counter = f"{base}-{counter}", counter + 1
    return run_id


class Journal:
    """Append-only journal of one run; each line is on disk before append() returns."""

    def __init__(self, state_dir: Path, run_id: str) -> None:
        directory = journal_dir(state_dir)
        directory.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.path = directory / f"{run_id}.jsonl"
        self._handle = self.path.open("x", encoding="utf-8")

    def append(self, entry: dict[str, Any]) -> None:
        """Write one operation, flush and fsync."""
        line = json.dumps({"run_id": self.run_id, **entry}, ensure_ascii=False)
        self._handle.write(line + "\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self) -> None:
        """Close the file."""
        self._handle.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def read_run(state_dir: Path, run_id: str) -> list[dict[str, Any]]:
    """Entries of one run, in order."""
    text = (journal_dir(state_dir) / f"{run_id}.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.split("\n") if line.strip()]


def _marker(state_dir: Path, run_id: str) -> Path:
    return journal_dir(state_dir) / f"{run_id}.undone"


def mark_undone(state_dir: Path, run_id: str) -> None:
    """Record that a run was undone."""
    _marker(state_dir, run_id).touch()


def is_undone(state_dir: Path, run_id: str) -> bool:
    """True when the run was undone."""
    return _marker(state_dir, run_id).exists()


def run_ids(state_dir: Path) -> list[str]:
    """Every journaled run, oldest first."""
    directory = journal_dir(state_dir)
    return sorted(path.stem for path in directory.glob("*.jsonl")) if directory.is_dir() else []


def last_run_id(state_dir: Path) -> str | None:
    """Newest run that was not undone."""
    live = [run_id for run_id in run_ids(state_dir) if not is_undone(state_dir, run_id)]
    return live[-1] if live else None


def confirmed_counts(state_dir: Path, tree: Tree) -> dict[str, int]:
    """Owner-decided moves per leaf kind, over every run not undone."""
    counts: Counter[str] = Counter()
    for run_id in run_ids(state_dir):
        if is_undone(state_dir, run_id):
            continue
        for entry in read_run(state_dir, run_id):
            leaf = tree.leaves.get(str(entry.get("leaf")))
            if entry.get("op") == "move" and entry.get("decided_by") == "owner" and leaf:
                counts[leaf.kind] += 1
    return dict(counts)
