"""Run journal (spec §4.3): one JSONL file per run, one flushed line per operation.

Owner-decided moves are the labels of spec §4.5: confirmed_counts() feeds the calibration cap.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Self, TextIO

from para_files.core.tree import Tree


DecidedBy = Literal["auto", "owner"]
RUN_ID_FORMAT = "%Y%m%d-%H%M%S"
RUN_ID_PATTERN = re.compile(r"(\d{8}-\d{6})(?:-(\d+))?")


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


def _run_order(run_id: str) -> tuple[str, int]:
    """Sort key: base timestamp, then numeric suffix (no suffix counts as 1)."""
    match = RUN_ID_PATTERN.fullmatch(run_id)
    if match is None:
        return (run_id, 1)
    return (match.group(1), int(match.group(2) or 1))


def _fsync_directory(directory: Path) -> None:
    """Persist a directory entry (a newly created file) to disk."""
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Journal:
    """Append-only journal of one run; each line is on disk before append() returns.

    The file is created on the first append, so a run with no operations leaves no journal.
    """

    def __init__(self, state_dir: Path, run_id: str) -> None:
        self.run_id = run_id
        self._directory = journal_dir(state_dir)
        self.path = self._directory / f"{run_id}.jsonl"
        if self.path.exists():
            msg = f"journal already exists: {self.path}"
            raise FileExistsError(msg)
        self._handle: TextIO | None = None

    def _create(self) -> TextIO:
        self._directory.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("x", encoding="utf-8")
        _fsync_directory(self._directory)
        return handle

    def append(self, entry: dict[str, Any]) -> None:
        """Write one operation, flush and fsync."""
        if self._handle is None:
            self._handle = self._create()
        line = json.dumps({**entry, "run_id": self.run_id}, ensure_ascii=False)
        self._handle.write(line + "\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self) -> None:
        """Close the file, if one was created."""
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def read_run(state_dir: Path, run_id: str) -> list[dict[str, Any]]:
    """Entries of one run, in order.

    A torn final line (crash mid-write: no trailing newline, or not valid JSON) is dropped
    so that undo still works; a malformed line anywhere else raises.
    """
    text = (journal_dir(state_dir) / f"{run_id}.jsonl").read_text(encoding="utf-8")
    terminated = text.endswith("\n")
    lines = [line for line in text.split("\n") if line.strip()]
    entries: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        is_last = index == len(lines) - 1
        if is_last and not terminated:
            break
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            if is_last:
                break
            raise
    return entries


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
    if not directory.is_dir():
        return []
    return sorted((path.stem for path in directory.glob("*.jsonl")), key=_run_order)


def last_run_id(state_dir: Path) -> str | None:
    """Newest run that was not undone."""
    live = [run_id for run_id in run_ids(state_dir) if not is_undone(state_dir, run_id)]
    return live[-1] if live else None


@dataclass(frozen=True)
class Example:
    """One owner decision: the file name, the leaf it went to, and what the tool proposed."""

    name: str
    leaf_id: str
    proposed: str | None


def _owner_decisions(state_dir: Path, tree: Tree) -> Iterator[dict[str, Any]]:
    """Owner-decided moves and confirmations, in order, of every run not undone."""
    for run_id in run_ids(state_dir):
        if is_undone(state_dir, run_id):
            continue
        for entry in read_run(state_dir, run_id):
            if (
                entry.get("op") in {"move", "confirm"}
                and entry.get("decided_by") == "owner"
                and tree.leaves.get(str(entry.get("leaf")))
            ):
                yield entry


def owner_examples(state_dir: Path, tree: Tree) -> list[Example]:
    """Owner-decided moves and confirmations of runs not undone; newest first, one per file."""
    found: dict[str, Example] = {}
    for entry in _owner_decisions(state_dir, tree):
        key = str(entry.get("sha256") or entry.get("src"))
        proposed = entry.get("proposed_leaf")
        found.pop(key, None)
        found[key] = Example(
            Path(str(entry.get("src"))).name,
            str(entry["leaf"]),
            str(proposed) if proposed else None,
        )
    return list(reversed(found.values()))


def confirmation_stats(state_dir: Path, tree: Tree) -> dict[str, tuple[int, int]]:
    """Per leaf kind: (owner-decided moves, how many the tool had proposed right).

    Counts every run not undone, each (content, leaf) once: the first entry seen wins.
    The second number feeds S2 (spec §3).
    """
    stats: dict[str, list[int]] = {}
    seen: set[tuple[str, str]] = set()
    for entry in _owner_decisions(state_dir, tree):
        if entry.get("sha256"):
            key = (str(entry["sha256"]), str(entry["leaf"]))
            if key in seen:
                continue
            seen.add(key)
        kind = tree.leaves[str(entry["leaf"])].kind
        counts = stats.setdefault(kind, [0, 0])
        counts[0] += 1
        counts[1] += entry.get("proposed_leaf") == entry.get("leaf")
    return {kind: (confirmed, right) for kind, (confirmed, right) in stats.items()}


def confirmed_counts(state_dir: Path, tree: Tree) -> dict[str, int]:
    """Owner-decided moves per leaf kind, over every run not undone."""
    return {kind: confirmed for kind, (confirmed, _) in confirmation_stats(state_dir, tree).items()}
