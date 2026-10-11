"""apply_ops: contained, never overwriting, journaled; emptied folders removed."""

from __future__ import annotations

import pytest

from para_files.core import apply as apply_mod
from para_files.core.apply import Op, apply_ops
from para_files.core.decide import Decision
from para_files.core.evidence import sha256_of
from para_files.core.journal import Journal, read_run
from para_files.utils.filename_sanitizer import sanitize_filename
from tests.core_helpers import make_config, make_settings


def setup(tmp_path):
    settings = make_settings(tmp_path)
    return settings.para_root.resolve(), settings.state_dir  # apply reports resolved paths


def inbox(root, rel, text="payslip"):
    path = root / "0_Inbox" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def decision(path, *, leaf="archives_10y_travail", target="4_Archives/10y_travail/2025", **kw):
    values = {
        "path": path,
        "sha256": sha256_of(path),
        "leaf_id": leaf,
        "target_dir": target,
        "band": "green",
        "signal": "rules",
        "confidence": 1.0,
        "evidence_summary": "rule",
        "kind": "record",
    }
    values.update(kw)
    return Decision(**values)


def run(root, state, ops, roots=None):
    with Journal(state, "r1") as journal:
        report = apply_ops(
            ops,
            config=make_config(),
            para_root=root,
            journal=journal,
            roots=roots or [root / "0_Inbox"],
        )
    journal_file = state / "journal" / "r1.jsonl"
    return report, read_run(state, "r1") if journal_file.exists() else []


def test_move_is_journaled(tmp_path):
    root, state = setup(tmp_path)
    src = inbox(root, "Payslip_2025.txt")
    report, entries = run(root, state, [Op(decision(src), "archives_10y_travail", "auto")])
    dst = root / "4_Archives" / "10y_travail" / "2025" / "Payslip_2025.txt"
    assert dst.read_text() == "payslip"
    assert not src.exists()
    assert report.moved == [(src, dst)]
    assert [e["op"] for e in entries] == ["mkdir", "mkdir", "move"]
    move = entries[-1]
    assert move["src"] == str(src)
    assert move["dst"] == str(dst)
    assert (move["leaf"], move["proposed_leaf"], move["decided_by"]) == (
        "archives_10y_travail",
        "archives_10y_travail",
        "auto",
    )
    assert move["sha256"] == sha256_of(dst)


def test_same_content_goes_to_trash(tmp_path):
    root, state = setup(tmp_path)
    existing = root / "4_Archives" / "10y_travail" / "2025" / "Payslip_2025.txt"
    existing.parent.mkdir(parents=True)
    existing.write_text("payslip")
    src = inbox(root, "Payslip_2025.txt")
    report, entries = run(root, state, [Op(decision(src), "archives_10y_travail", "auto")])
    trashed = root / ".trash" / "r1" / "0_Inbox" / "Payslip_2025.txt"
    assert trashed.read_text() == "payslip"
    assert existing.read_text() == "payslip"
    assert report.trashed == [(src, trashed)]
    assert entries[-1]["op"] == "trash"


def test_different_content_gets_a_suffix(tmp_path):
    root, state = setup(tmp_path)
    existing = root / "4_Archives" / "10y_travail" / "2025" / "Payslip_2025.txt"
    existing.parent.mkdir(parents=True)
    existing.write_text("older payslip")
    src = inbox(root, "Payslip_2025.txt")
    run(root, state, [Op(decision(src), "archives_10y_travail", "auto")])
    assert existing.read_text() == "older payslip"
    assert (existing.parent / "Payslip_2025 (2).txt").read_text() == "payslip"


def test_target_outside_root_is_refused(tmp_path):
    root, state = setup(tmp_path)
    src = inbox(root, "a.txt")
    op = Op(decision(src, target="4_Archives/../../outside"), "archives_10y_travail", "auto")
    report, entries = run(root, state, [op])
    assert report.skipped == [(src, "target outside the PARA root")]
    assert src.exists()
    assert not (tmp_path / "outside").exists()
    assert entries == []


def test_secret_unknown_leaf_missing_and_changed_are_skipped(tmp_path):
    root, state = setup(tmp_path)
    secret = inbox(root, "keys.txt")
    changed = inbox(root, "changed.txt")
    changed_decision = decision(changed)
    changed.write_text("edited after preview")
    missing = inbox(root, "missing.txt")
    missing_decision = decision(missing)
    missing.unlink()
    ops = [
        Op(decision(secret, signal="secret"), "archives_10y_travail", "auto"),
        Op(decision(inbox(root, "b.txt")), "no_such_leaf", "owner"),
        Op(missing_decision, "archives_10y_travail", "auto"),
        Op(changed_decision, "archives_10y_travail", "auto"),
    ]
    report, _ = run(root, state, ops)
    assert [reason for _, reason in report.skipped] == [
        "secret",
        "unknown leaf 'no_such_leaf'",
        "source missing",
        "changed since the preview",
    ]
    assert secret.exists()


def test_already_in_place(tmp_path):
    root, state = setup(tmp_path)
    folder = root / "4_Archives" / "10y_travail" / "2025"
    folder.mkdir(parents=True)
    src = folder / "Payslip_2025.txt"
    src.write_text("payslip")
    report, _ = run(root, state, [Op(decision(src), "archives_10y_travail", "auto")])
    assert report.skipped == [(src, "already in place")]


def test_suggested_name_is_sanitized(tmp_path):
    root, state = setup(tmp_path)
    src = inbox(root, "scan.pdf")
    op = Op(decision(src, suggested_name="A: B?.pdf"), "archives_10y_travail", "auto")
    run(root, state, [op])
    name = sanitize_filename("A: B?.pdf", preserve_extension=True)
    assert (root / "4_Archives" / "10y_travail" / "2025" / name).exists()


def test_owner_correction_goes_to_the_leaf_root(tmp_path):
    root, state = setup(tmp_path)
    src = inbox(root, "Payslip_2025.txt")
    _, entries = run(root, state, [Op(decision(src), "archives_5y_factures", "owner")])
    assert (root / "4_Archives" / "5y_factures" / "Payslip_2025.txt").exists()
    move = entries[-1]
    assert (move["leaf"], move["proposed_leaf"], move["decided_by"]) == (
        "archives_5y_factures",
        "archives_10y_travail",
        "owner",
    )


def test_emptied_folders_are_removed_inside_roots_only(tmp_path):
    root, state = setup(tmp_path)
    src = inbox(root, "batch/sub/Payslip_2025.txt")
    keep = inbox(root, "other/keep.txt", "keep")
    report, entries = run(root, state, [Op(decision(src), "archives_10y_travail", "auto")])
    assert not (root / "0_Inbox" / "batch").exists()
    assert (root / "0_Inbox").is_dir()
    assert keep.exists()
    assert report.removed_dirs == [root / "0_Inbox" / "batch" / "sub", root / "0_Inbox" / "batch"]
    assert [e["op"] for e in entries][-2:] == ["rmdir", "rmdir"]


def test_nothing_is_deleted(tmp_path):
    root, state = setup(tmp_path)
    existing = root / "4_Archives" / "10y_travail" / "2025" / "Payslip_2025.txt"
    existing.parent.mkdir(parents=True)
    existing.write_text("payslip")
    sources = [inbox(root, f"Payslip_2025_{n}.txt") for n in range(3)]
    sources.append(inbox(root, "Payslip_2025.txt"))
    before = sum(1 for p in root.rglob("*") if p.is_file())
    run(root, state, [Op(decision(s), "archives_10y_travail", "auto") for s in sources])
    assert sum(1 for p in root.rglob("*") if p.is_file()) == before


def test_trash_folder_name(tmp_path):
    assert apply_mod.TRASH == ".trash"


@pytest.mark.parametrize("name", [".", "..", "   "])
def test_invalid_suggested_name_is_skipped(tmp_path, name):
    root, state = setup(tmp_path)
    src = inbox(root, "scan.pdf")
    before = sorted(p.relative_to(root) for p in root.rglob("*"))
    op = Op(decision(src, suggested_name=name), "archives_10y_travail", "auto")
    report, _ = run(root, state, [op])
    assert report.skipped == [(src, "invalid file name")]
    assert src.exists()
    assert sorted(p.relative_to(root) for p in root.rglob("*")) == before
    assert {p.name for p in tmp_path.iterdir()} <= {"PARA", "cache", "state"}


def test_dangling_symlink_at_destination_is_not_overwritten(tmp_path):
    root, state = setup(tmp_path)
    src = inbox(root, "Payslip_2025.txt")
    target = root / "4_Archives" / "10y_travail" / "2025"
    target.mkdir(parents=True)
    link = target / "Payslip_2025.txt"
    link.symlink_to(root / "nowhere.txt")
    report, _ = run(root, state, [Op(decision(src), "archives_10y_travail", "auto")])
    assert link.is_symlink()
    assert not link.exists()
    assert (target / "Payslip_2025 (2).txt").read_text() == "payslip"
    assert report.moved == [(src, target / "Payslip_2025 (2).txt")]
