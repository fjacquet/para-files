"""`clean` (spec §4.3, §4.4): junk files and identical duplicates to .trash, empty folders.

Everything goes through the journal, write-ahead, so `undo` can reverse a clean run.
Secret files are never trashed. Dot-folders and symlinks are never followed.
"""

from __future__ import annotations

import os
import shutil
from collections import defaultdict
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from para_files.core.apply import TRASH, free_path, make_dirs
from para_files.core.evidence import extract, sha256_of
from para_files.core.journal import Journal


JUNK_NAMES = frozenset({".ds_store", "thumbs.db", "desktop.ini"})
JUNK_PREFIXES = ("~$", "._")


@dataclass
class CleanPlan:
    """What a clean would do: junk to trash, duplicates (copy, original kept), empty folders."""

    junk: list[Path] = field(default_factory=list)
    duplicates: list[tuple[Path, Path]] = field(default_factory=list)
    empty_dirs: list[Path] = field(default_factory=list)


@dataclass
class CleanReport:
    """What a clean did."""

    trashed: list[tuple[Path, Path]] = field(default_factory=list)
    removed_dirs: list[Path] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)


def is_junk(name: str) -> bool:
    """System clutter: .DS_Store, Thumbs.db, desktop.ini, Office lock and AppleDouble files."""
    return name.casefold() in JUNK_NAMES or name.startswith(JUNK_PREFIXES)


def _walk(base: Path) -> Iterator[tuple[Path, list[str], list[str]]]:
    for dirpath, dirnames, filenames in os.walk(base, topdown=True):
        dirnames[:] = sorted(name for name in dirnames if not name.startswith("."))
        yield Path(dirpath), dirnames, sorted(filenames)


def _empty_after_junk(base: Path) -> list[Path]:
    """Folders strictly below base left empty once junk is gone, deepest first."""
    empty: set[Path] = set()
    for dirpath, dirnames, filenames in os.walk(base, topdown=False):
        here = Path(dirpath)
        if here == base or any(part.startswith(".") for part in here.relative_to(base).parts):
            continue
        dirs_left = [name for name in dirnames if here / name not in empty]
        files_left = [name for name in filenames if not is_junk(name)]
        if not dirs_left and not files_left:
            empty.add(here)
    return sorted(empty, key=lambda path: len(path.parts), reverse=True)


def _duplicates(files: Sequence[Path], root: Path) -> list[tuple[Path, Path]]:
    """(copy, kept) for every file whose content another file already has; secrets left out."""
    by_size: dict[int, list[Path]] = defaultdict(list)
    for path in files:
        size = path.stat().st_size
        if size:
            by_size[size].append(path)
    pairs: list[tuple[Path, Path]] = []
    for group in by_size.values():
        if len(group) < 2:  # noqa: PLR2004 - a duplicate needs two files
            continue
        by_hash: dict[str, list[Path]] = defaultdict(list)
        for path in group:
            by_hash[sha256_of(path)].append(path)
        for same in by_hash.values():
            kept, *copies = sorted(same, key=str)
            pairs += [(copy, kept) for copy in copies if extract(copy, root=root).secret is None]
    return pairs


def plan_clean(paths: Sequence[Path], *, root: Path, duplicates: bool) -> CleanPlan:
    """Look for junk, empty folders and (with duplicates) identical files under paths."""
    plan = CleanPlan()
    files: list[Path] = []
    for base in paths:
        for here, _dirs, names in _walk(base):
            for name in names:
                path = here / name
                if path.is_symlink() or not path.is_file():
                    continue
                if is_junk(name):
                    plan.junk.append(path)
                elif not name.startswith("."):
                    files.append(path)
        plan.empty_dirs += _empty_after_junk(base)
    if duplicates:
        plan.duplicates = _duplicates(files, root)
    return plan


def apply_clean(plan: CleanPlan, *, root: Path, journal: Journal) -> CleanReport:
    """Trash junk and duplicate copies, then remove the folders left empty."""
    report = CleanReport()
    base = root.resolve()
    for src in [*plan.junk, *(copy for copy, _ in plan.duplicates)]:
        if src.is_symlink() or not src.is_file():
            report.skipped.append((src, "source missing"))
            continue
        relative = src.resolve().relative_to(base)
        dst = free_path(base / TRASH / journal.run_id / relative)
        make_dirs(dst.parent, journal)
        journal.append(
            {
                "op": "trash",
                "src": str(src),
                "dst": str(dst),
                "sha256": sha256_of(src),
                "size": src.stat().st_size,
                "leaf": None,
                "proposed_leaf": None,
                "decided_by": "auto",
                "signal": "clean",
                "confidence": 1.0,
            }
        )
        shutil.move(src, dst)
        report.trashed.append((src, dst))
    for directory in plan.empty_dirs:
        if directory.is_dir() and not any(directory.iterdir()):
            journal.append({"op": "rmdir", "dst": str(directory)})
            directory.rmdir()
            report.removed_dirs.append(directory)
    return report
