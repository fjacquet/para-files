"""Inventory of the PARA buckets and the canonical folder map (Stage 1, read-only).

Each first-level folder maps to its canonical folder, or to INBOX when it is doubtful
(spec §4.1 "Tree cleanup policy": doubtful content goes back to 0_Inbox in a later batch).
A retention prefix is part of a folder's identity: name-based rules never merge two
different prefixes; only a prefix the taxonomy does not define for a stem is remapped.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


BUCKETS = ("1_Projets", "2_Areas", "3_Resources", "4_Archives")
ARCHIVES = "4_Archives"
INBOX = "0_Inbox"
# Same retention words as para_files.core.tree.RETENTION_PREFIX, which takes an underscore only;
# the seeder also accepts a dash or a space after the prefix (e.g. "5y factures").
RETENTION_PREFIX = re.compile(r"^(\d+y|ret|ctr)[_\- ]")
SYNONYMS = (("livres", "books"), ("formation", "formations"), ("docs", "documentation"))
MEDIA = frozenset({"photos", "videos", "media", "screenshots"})
LIBRARY = frozenset(
    {
        "livres",
        "books",
        "docs",
        "documentation",
        "formation",
        "formations",
        "certifications",
        "courses-completed",
        "licences",
        "isos",
        "programmes",
    }
)
COUNT_CAP = 5000


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Rows of a UTF-8 JSONL file; blank or whitespace-only lines are skipped."""
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def nfc(text: str) -> str:
    """Text in Unicode NFC (macOS and SMB volumes may hand back NFD names)."""
    return unicodedata.normalize("NFC", text)


def strip_prefix(name: str) -> str:
    """Folder name without its retention prefix, trimmed and lower-cased."""
    return RETENTION_PREFIX.sub("", nfc(name).strip()).lower()


def retention_of(name: str) -> str | None:
    """Retention prefix of a folder name (5y, 10y, 2y, ret, ctr), or None."""
    match = RETENTION_PREFIX.match(nfc(name).strip())
    return match.group(1) if match else None


def name_key(name: str) -> str:
    """Variant key: case, accents, separators, plural and padding folded; prefix KEPT."""
    text = unicodedata.normalize("NFKD", nfc(name).strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[\s_\-.]+", " ", text).strip()
    return re.sub(r"(?<=\w\w)[sx]$", "", text)


def is_member(name: str, group: frozenset[str]) -> bool:
    """Whether name (prefix already removed) is a word of group, compared by variant key."""
    return name_key(name) in {name_key(word) for word in group}


def stem_key(name: str) -> str:
    """name_key without the retention prefix; only used to find twins and stray prefixes."""
    return name_key(RETENTION_PREFIX.sub("", nfc(name).strip()))


@dataclass
class Folder:
    """A first-level folder of a PARA bucket."""

    bucket: str
    name: str  # NFC; may still carry padding spaces, as on disk
    files: int
    subfolders: list[str] = field(default_factory=list)

    @property
    def rel(self) -> str:
        """bucket/name as on disk (NFC)."""
        return f"{self.bucket}/{self.name}"

    @property
    def trimmed(self) -> str:
        """bucket/name with the padding removed."""
        return f"{self.bucket}/{self.name.strip()}"


def count_files(root: Path, cap: int = COUNT_CAP) -> int:
    """Count non-hidden files under root, stopping at cap; never follows symlinks."""
    total = 0
    for _dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        total += sum(1 for name in filenames if not name.startswith("."))
        if total >= cap:
            return cap
    return total


def scan_folders(para_root: Path, buckets: tuple[str, ...] = BUCKETS) -> list[Folder]:
    """First-level folders of each bucket; other top-level folders are never read."""
    folders: list[Folder] = []
    for bucket in buckets:
        base = para_root / bucket
        if not base.is_dir() or base.is_symlink():
            continue
        for entry in sorted(base.iterdir(), key=lambda path: path.name):
            if entry.is_symlink() or not entry.is_dir() or entry.name.startswith((".", "_")):
                continue
            subfolders = sorted(
                nfc(sub.name)
                for sub in entry.iterdir()
                if sub.is_dir() and not sub.is_symlink() and not sub.name.startswith(".")
            )
            folders.append(Folder(bucket, nfc(entry.name), count_files(entry), subfolders))
    return folders


def scan_notes(para_root: Path, buckets: tuple[str, ...] = BUCKETS) -> list[str]:
    """Review lines for what scan_folders leaves out: dot or underscore folders, loose files."""
    notes: list[str] = []
    for bucket in buckets:
        base = para_root / bucket
        entries = sorted(base.iterdir(), key=lambda path: path.name) if base.is_dir() else []
        for entry in entries:
            if entry.is_dir() and entry.name.startswith((".", "_")):
                notes.append(
                    f"skipped folder: {bucket}/{nfc(entry.name)} (name starts with . or _)"
                )
        loose = sum(1 for entry in entries if entry.is_file() and not entry.name.startswith("."))
        notes.append(f"loose files in {bucket}: {loose}")
    return notes


def retentions_by_stem(documents: dict[str, Any]) -> dict[str, set[str]]:
    """Archive stem -> retention prefixes documents.json files it under (the taxonomy)."""
    found: dict[str, set[str]] = {}
    for category in documents.get("categories", []):
        for doc in category.get("documents", []):
            parts = (doc.get("para_pattern") or "").split("/")
            prefix = retention_of(parts[1]) if len(parts) > 1 and parts[0] == ARCHIVES else None
            if prefix:
                found.setdefault(stem_key(parts[1]), set()).add(prefix)
    return found


def _group_targets(
    bucket: str, stem: str, group: list[Folder], taxonomy: dict[str, set[str]]
) -> dict[str, str]:
    """Targets for one (bucket, stem) group of folders."""
    reps: dict[str, Folder] = {}
    # ties at COUNT_CAP fall back to the number of subfolders, then to the name
    for folder in sorted(group, key=lambda f: (-f.files, -len(f.subfolders), f.name)):
        reps.setdefault(name_key(folder.name), folder)  # R4: variants fold into the largest
    rep_target = {key: rep.trimmed for key, rep in reps.items()}
    prefixed = [rep for rep in reps.values() if retention_of(rep.name)]
    plain = [rep for rep in reps.values() if not retention_of(rep.name)]
    lead = max(prefixed, key=lambda f: f.files) if prefixed else None
    if bucket != ARCHIVES and lead and is_member(strip_prefix(lead.name), MEDIA | LIBRARY):
        bare = RETENTION_PREFIX.sub("", lead.name.strip())  # R9: media/library drop it
        target = plain[0].trimmed if plain else f"{bucket}/{bare}"
        return {folder.rel: target for folder in group}
    if prefixed or (bucket == ARCHIVES and stem in taxonomy):  # records: the vault decides
        allowed = taxonomy.get(stem) or {retention_of(rep.name) for rep in prefixed}
        vault = {key: f"{ARCHIVES}/{rep.name.strip()}" for key, rep in reps.items()}
        keepers = [
            vault[name_key(rep.name)] for rep in prefixed if retention_of(rep.name) in allowed
        ]
        single = None
        if len(allowed) == 1:  # the taxonomy prefix, created when no folder has it yet
            base = RETENTION_PREFIX.sub("", next(iter(reps.values())).name.strip())
            single = keepers[0] if keepers else f"{ARCHIVES}/{next(iter(allowed))}_{base}"
        for key, rep in reps.items():
            if retention_of(rep.name) in allowed:
                rep_target[key] = vault[key]  # its own vault folder (R9 moves it there)
            elif single is not None:
                rep_target[key] = single  # R1 legacy twin, R3 stray prefix
            elif len(allowed) > 1:
                rep_target[key] = INBOX  # R2: legacy or stray folder of a split stem, doubtful
    return {folder.rel: rep_target[name_key(folder.name)] for folder in group}


def _target_named(targets: list[str], bucket: str, word: str) -> str | None:
    """The target in bucket whose folder name has the same variant key as word, if any."""
    for target in targets:
        target_bucket, _, name = target.partition("/")
        if target_bucket == bucket and name_key(name) == name_key(word):
            return target
    return None


def canonical_map(
    folders: list[Folder], taxonomy: dict[str, set[str]] | None = None
) -> dict[str, str]:
    """Map each folder's rel path (as on disk) to its canonical rel path, or to INBOX."""
    taxonomy = taxonomy or {}
    groups: dict[tuple[str, str], list[Folder]] = {}
    for folder in folders:
        groups.setdefault((folder.bucket, stem_key(folder.name)), []).append(folder)
    mapping: dict[str, str] = {}
    for (bucket, stem), group in groups.items():
        mapping.update(_group_targets(bucket, stem, group, taxonomy))
    size: Counter[str] = Counter()
    for folder in folders:
        size[mapping[folder.rel]] += folder.files
    for first, second in SYNONYMS:  # R5: the smaller folds into the larger
        for bucket in BUCKETS:
            a = _target_named(list(size), bucket, first)
            b = _target_named(list(size), bucket, second)
            if a is None or b is None or a == b:
                continue
            keep, drop = (a, b) if size[a] >= size[b] else (b, a)
            mapping = {rel: keep if target == drop else target for rel, target in mapping.items()}
            size[keep] += size.pop(drop)
    return mapping


def make_canon(
    folders: list[Folder], taxonomy: dict[str, set[str]] | None = None
) -> Callable[[str], str]:
    """Return canon(rel) -> canonical rel or INBOX; unknown paths match by variant key."""
    mapping = canonical_map(folders, taxonomy)
    by_trimmed = {folder.trimmed: mapping[folder.rel] for folder in folders}
    by_key = {(folder.bucket, name_key(folder.name)): mapping[folder.rel] for folder in folders}
    for first, second in SYNONYMS:
        for bucket in BUCKETS:
            for word, other in ((first, second), (second, first)):
                known = by_key.get((bucket, name_key(other)))
                if known is not None:
                    by_key.setdefault((bucket, name_key(word)), known)

    def canon(rel: str) -> str:
        key = nfc(rel).strip()
        if key in by_trimmed:
            return by_trimmed[key]
        bucket, _, name = key.partition("/")
        return by_key.get((bucket, name_key(name)), key)

    return canon
