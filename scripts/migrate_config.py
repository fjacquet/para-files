"""Draft tree.yaml, rules.yaml and issuers.yaml from the current PARA tree (Stage 1, throwaway).

Read-only on the PARA root. Writes only to --out (default: <config dir>/draft).

Usage:
    uv run python scripts/migrate_config.py --para-root "$PARA"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from para_inventory import (
    INBOX,
    LIBRARY,
    MEDIA,
    Folder,
    is_member,
    make_canon,
    nfc,
    retention_of,
    retentions_by_stem,
    scan_folders,
    scan_notes,
    strip_prefix,
)

from para_files.config import default_reference_tree
from para_files.core.tree import TreeError, config_dir, load_tree_config, validation_warnings


BOOKS = frozenset({"livres", "books"})
TAGS = {
    "1_Projets": "projects",
    "2_Areas": "areas",
    "3_Resources": "resources",
    "4_Archives": "archives",
}
DRAFT_FILES = ("tree.yaml", "rules.yaml", "issuers.yaml", "review.md")
RETENTIONS = frozenset({"ret", "10y", "5y", "2y", "ctr"})
RETENTION_FROM_DOCS = {
    "permanent": "permanent",
    "retirement": "ret",
    "10_years": "10y",
    "5_years": "5y",
    "contract_duration": "ctr",
    "warranty_2_years": "2y",
}
YEAR = re.compile(r"^(19|20)\d{2}$")
PLACEHOLDER = re.compile(r"\{[^}]+\}")
SUBKEY_FROM_DOCS = ("{issuer}", "{year}")
Canon = Callable[[str], str]
DEFAULT_DOCUMENTS = Path(__file__).resolve().parent.parent / "config" / "documents.json"


def slug(text: str) -> str:
    """ASCII snake_case of text."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")


def folder_of(pattern: str) -> str | None:
    """bucket/folder of a destination pattern, or None when that part is a placeholder."""
    parts = [nfc(part).strip() for part in pattern.split("/") if part.strip()]
    if len(parts) < 2 or PLACEHOLDER.search(parts[0]) or PLACEHOLDER.search(parts[1]):
        return None
    return f"{parts[0]}/{parts[1]}"


def document_folders(
    documents: dict[str, Any], canon: Canon, notes: list[str]
) -> dict[str, tuple[str, str | None]]:
    """Canonical folder -> (retention, subkey) taken from documents.json."""
    found: dict[str, tuple[str, str | None]] = {}
    unknown_noted: set[str] = set()
    for category in documents.get("categories", []):
        for doc in category.get("documents", []):
            pattern = doc.get("para_pattern") or category.get("para_pattern") or ""
            folder = folder_of(pattern)
            if folder is None:
                continue
            subkey = "/".join(p for p in SUBKEY_FROM_DOCS if p in pattern) or None
            known = doc.get("retention", "")
            if known not in RETENTION_FROM_DOCS and folder not in unknown_noted:
                unknown_noted.add(folder)
                notes.append(
                    f"unknown retention '{known}' in documents.json for {folder}; "
                    "proposed permanent"
                )
            retention = RETENTION_FROM_DOCS.get(known, "permanent")
            target = canon(folder)
            if target != INBOX:
                found.setdefault(target, (retention, subkey))
    return found


def propose_leaf(
    folder: Folder, docs: dict[str, tuple[str, str | None]], notes: list[str]
) -> dict[str, Any]:
    """kind / retention / subkey / describe proposal for one canonical folder."""
    rel = f"{folder.bucket}/{folder.name.strip()}"
    name = strip_prefix(folder.name)
    subs = [s.strip() for s in folder.subfolders]
    years = [s for s in subs if YEAR.match(s)]
    year_subkey = "{year}" if subs and len(years) * 2 >= len(subs) else None
    others = [s for s in subs if not YEAR.match(s)][:10]
    describe = folder.name.strip() + (f" (contains: {', '.join(others)})" if others else "")
    leaf: dict[str, Any] = {"path": rel, "describe": describe}
    prefix = retention_of(folder.name)
    doc_retention, doc_subkey = docs.get(rel, (None, None))
    if is_member(name, MEDIA):
        leaf.update(kind="media", subkey="{year}")
    elif is_member(name, LIBRARY):
        leaf.update(kind="library", subkey="{thema}" if is_member(name, BOOKS) else None)
    elif prefix in RETENTIONS and folder.bucket == "4_Archives":
        leaf.update(kind="record", retention=prefix, subkey=doc_subkey or year_subkey)
    elif prefix is not None or doc_retention is not None or folder.bucket == "4_Archives":
        if prefix is not None or doc_retention not in (None, "permanent"):
            notes.append(f"{rel}: retention needs a decision; proposed permanent")
        elif doc_retention is None:
            notes.append(f"{rel}: unprefixed archive folder; proposed record/permanent")
        leaf.update(kind="record", retention="permanent", subkey=doc_subkey or year_subkey)
    else:
        leaf.update(kind="knowledge")
    return {key: value for key, value in leaf.items() if value is not None}


def draft_tree(
    folders: list[Folder], canon: Canon, docs: dict[str, tuple[str, str | None]], notes: list[str]
) -> dict[str, dict[str, Any]]:
    """One proposed leaf per canonical target (created when no folder has it yet)."""
    scanned = {folder.trimmed: folder for folder in folders}
    targets: list[str] = []
    for folder in folders:
        if folder.name != folder.name.strip():
            notes.append(
                f"padded folder name on disk: '{folder.rel}' — rename it to the trimmed name "
                "before building the golden corpus"
            )
        rel = folder.trimmed
        target = canon(rel)
        if target == INBOX:
            notes.append(f"doubtful: {rel} -> {INBOX} (later batch)")
            continue
        if target != rel:
            note = f"merge: {rel} -> {target}"
            if slug(rel) == slug(target):  # twins: golden samples leaf paths, not folder names
                note += (
                    "; rename on disk before building the golden corpus "
                    "(golden samples leaf paths only)"
                )
            notes.append(note)
        if target not in targets:
            targets.append(target)
    leaves: dict[str, dict[str, Any]] = {}
    for index, target in enumerate(targets, start=1):
        bucket, _, name = target.partition("/")
        folder = scanned.get(target) or Folder(bucket, name, 0)
        if slug(name):
            base = f"{TAGS.get(bucket, slug(bucket))}_{slug(name)}"
        else:
            base = f"leaf_{index}"
            notes.append(
                f"folder name {target} has no ASCII letters or digits; leaf id {base}, "
                "rename the folder to set a readable id"
            )
        leaf_id, counter = base, 2
        while leaf_id in leaves:
            leaf_id, counter = f"{base}_{counter}", counter + 1
        leaves[leaf_id] = propose_leaf(folder, docs, notes)
    return leaves


def combine_globs(patterns: list[str], extensions: list[str]) -> list[str]:
    """Globs equivalent to the legacy rule: a filename pattern AND an extension."""
    exts = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions]
    if not patterns:
        return [f"*{ext}" for ext in exts]
    if not exts:
        return list(dict.fromkeys(patterns))
    globs = []
    for pattern in patterns:
        for ext in exts:
            if pattern.lower().endswith(ext):
                globs.append(pattern)
            elif pattern.endswith("*"):
                globs.append(f"{pattern}{ext}")
    return list(dict.fromkeys(globs))


def is_short_substring(glob: str) -> bool:
    """A '*xy*'-style glob with 3 or fewer literal characters (matches far too much)."""
    literals = re.sub(r"[*?\[\]]", "", glob)
    return glob.startswith("*") and glob.endswith("*") and len(literals) <= 3


def draft_rules(
    legacy_rules: dict[str, Any], canon: Canon, leaf_of: dict[str, str], notes: list[str]
) -> tuple[list[dict[str, Any]], list[tuple[str, list[str], str | None]]]:
    """Rules (pattern rules first, extension-only rules last) and issuers found in rules."""
    pattern_rules: list[dict[str, Any]] = []
    extension_rules: list[dict[str, Any]] = []
    issuers: list[tuple[str, list[str], str | None]] = []
    for name, rule in legacy_rules.items():
        if not isinstance(rule, dict) or not rule.get("destination"):
            notes.append(f"rule {name}: no destination, dropped")
            continue
        if name.endswith("_v2") and name[:-3] in legacy_rules:
            notes.append(f"rule {name}: copy of {name[:-3]}, dropped")
            continue
        folder = folder_of(rule["destination"])
        target = canon(folder) if folder else None
        leaf = leaf_of.get(target) if target else None
        if leaf is None:
            reason = "is doubtful" if target == INBOX else "has no leaf"
            notes.append(f"rule {name}: destination {rule['destination']} {reason}, dropped")
            continue
        if rule.get("action"):
            notes.append(f"rule {name}: action {rule['action']} ignored")
        patterns = list(rule.get("patterns") or [])
        globs = combine_globs(patterns, list(rule.get("extensions") or []))
        short = [glob for glob in globs if is_short_substring(glob)]
        if short:
            notes.append(f"rule {name}: dropped short globs {short}")
        globs = [glob for glob in globs if not is_short_substring(glob)]
        if not globs:
            notes.append(f"rule {name}: no usable glob left, dropped")
            continue
        issuers += [
            (i["name"], list(i.get("patterns") or []), leaf) for i in rule.get("issuers") or []
        ]
        vendors = [*(rule.get("known_vendors") or []), *(rule.get("known_technologies") or [])]
        issuers += [(vendor, [vendor], leaf) for vendor in vendors]
        rule_list = pattern_rules if patterns else extension_rules
        rule_list.append({"name": name, "leaf": leaf, "globs": globs})
    return pattern_rules + extension_rules, issuers


def draft_issuers(
    documents: dict[str, Any],
    canon: Canon,
    leaf_of: dict[str, str],
    extra: list[tuple[str, list[str], str | None]],
    notes: list[str],
) -> dict[str, dict[str, list[str]]]:
    """Issuers from documents.json plus those found in legacy rules; patterns stay unique."""
    entries: list[tuple[str, list[str], str | None]] = []
    for category in documents.get("categories", []):
        for doc in category.get("documents", []):
            folder = folder_of(doc.get("para_pattern") or category.get("para_pattern") or "")
            leaf = leaf_of.get(canon(folder)) if folder else None
            entries += [
                (i["name"], list(i.get("patterns") or []), leaf) for i in doc.get("issuers") or []
            ]
    entries += extra
    issuers: dict[str, dict[str, list[str]]] = {}
    owner: dict[str, str] = {}
    for name, patterns, leaf in entries:
        key = slug(name) or "issuer"
        if leaf is None:
            notes.append(f"issuer {name}: destination has no leaf, skipped")
            continue
        entry = issuers.setdefault(key, {"patterns": [], "leaves": []})
        for pattern in patterns:
            first = owner.setdefault(nfc(pattern).casefold(), key)
            if first != key:
                notes.append(f"issuer {key}: pattern {pattern!r} already used by {first}, skipped")
            elif pattern not in entry["patterns"]:
                entry["patterns"].append(pattern)
        if leaf not in entry["leaves"]:
            entry["leaves"].append(leaf)
    return {key: value for key, value in issuers.items() if value["patterns"]}


def inbox_families(inbox: Path) -> list[tuple[str, int, str]]:
    """Recurring filename families in the inbox: (family, count, example), count >= 2."""
    counts: Counter[str] = Counter()
    example: dict[str, str] = {}
    for _dirpath, dirnames, filenames in os.walk(inbox):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for filename in filenames:
            if filename.startswith("."):
                continue
            path = Path(nfc(filename))
            stem = re.sub(r"\d+", "#", path.stem.lower())
            family = re.sub(r"[#_\-\s.()]+", " ", stem).strip() + path.suffix.lower()
            counts[family] += 1
            example.setdefault(family, path.name)
    return [(family, n, example[family]) for family, n in counts.most_common() if n >= 2]


def write_review(
    out: Path,
    leaves: dict[str, dict[str, Any]],
    notes: list[str],
    families: list[tuple[str, int, str]],
    warnings: list[str],
    scanned: list[str],
) -> None:
    """review.md: what the seeder decided and what the owner must decide."""
    kinds = Counter(leaf["kind"] for leaf in leaves.values())
    summary = ", ".join(f"{kind} {n}" for kind, n in sorted(kinds.items()))
    lines = [
        "# Draft review",
        "",
        f"{len(leaves)} leaves proposed ({summary}). Target 20-30: merge or drop leaves, "
        "then copy tree.yaml, rules.yaml and issuers.yaml one level up.",
        "",
        "## Notes",
        "",
        *[f"- {note}" for note in notes],
        "",
        "## Skipped folders and loose files",
        "",
        *[f"- {line}" for line in scanned],
        "",
        "## Recurring inbox families (issuer candidates)",
        "",
        *[f"- {family}: {n} files, e.g. {example}" for family, n, example in families],
        "",
        "## Validation warnings",
        "",
        *[f"- {warning}" for warning in warnings],
        "",
    ]
    (out / "review.md").write_text("\n".join(lines), encoding="utf-8")


def _dump(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Write the draft config and review.md; return 0."""
    parser = argparse.ArgumentParser(description="Draft tree.yaml, rules.yaml and issuers.yaml.")
    parser.add_argument("--para-root", type=Path, required=True)
    parser.add_argument("--legacy-tree", type=Path, default=None)
    parser.add_argument("--documents", type=Path, default=DEFAULT_DOCUMENTS)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--force", action="store_true", help="overwrite an existing draft")
    args = parser.parse_args(argv)
    para_root = args.para_root.expanduser().resolve()
    if not para_root.is_dir():
        parser.error(f"--para-root is not a directory: {para_root}")
    out = (args.out or config_dir() / "draft").expanduser().resolve()
    if out.is_relative_to(para_root):
        parser.error("--out must be outside the PARA root")
    existing = [name for name in DRAFT_FILES if (out / name).exists()]
    if existing and not args.force:
        parser.error(
            f"{', '.join(existing)} already in {out} and may hold your edits; "
            "pass --force to overwrite"
        )
    legacy_path = args.legacy_tree or default_reference_tree()
    legacy = yaml.safe_load(legacy_path.read_text(encoding="utf-8")) or {}
    documents = json.loads(args.documents.read_text(encoding="utf-8"))

    folders = scan_folders(para_root)
    canon = make_canon(folders, retentions_by_stem(documents))
    notes: list[str] = []
    leaves = draft_tree(folders, canon, document_folders(documents, canon, notes), notes)
    leaf_of = {leaf["path"]: leaf_id for leaf_id, leaf in leaves.items()}
    rules, rule_issuers = draft_rules(legacy.get("routing_rules") or {}, canon, leaf_of, notes)
    issuers = draft_issuers(documents, canon, leaf_of, rule_issuers, notes)

    out.mkdir(parents=True, exist_ok=True)
    _dump(out / "tree.yaml", {"leaves": leaves})
    _dump(out / "rules.yaml", {"rules": rules})
    _dump(out / "issuers.yaml", {"issuers": issuers})
    status = 0
    try:
        warnings = validation_warnings(load_tree_config(out))
    except TreeError as exc:  # still write review.md so the owner sees why
        warnings, status = [f"the draft does not load: {exc}"], 1
    write_review(
        out, leaves, notes, inbox_families(para_root / "0_Inbox"), warnings, scan_notes(para_root)
    )
    print(f"{len(leaves)} leaves, {len(rules)} rules, {len(issuers)} issuers -> {out}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
