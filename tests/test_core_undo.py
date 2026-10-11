"""undo_run: replays a journal backwards; S5 (byte-identical tree after undo)."""

from __future__ import annotations

import hashlib

import pytest

from para_files.core import apply as apply_mod
from para_files.core.apply import Op, apply_ops
from para_files.core.decide import Decision
from para_files.core.evidence import sha256_of
from para_files.core.journal import Journal, is_undone, last_run_id
from para_files.core.undo import UndoError, undo_run
from tests.core_helpers import make_config, make_settings


RUN = "20261011-100000"


def tree_state(root):
    """Every folder, and every file with size, content hash and mtime."""
    state = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            state[rel] = "dir"
        else:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            state[rel] = (path.stat().st_size, digest, path.stat().st_mtime_ns)
    return state


def setup(tmp_path):
    settings = make_settings(tmp_path)
    root = settings.para_root.resolve()
    existing = root / "4_Archives" / "10y_travail" / "2025" / "dup.txt"
    existing.parent.mkdir(parents=True)
    existing.write_text("dup")
    files = {
        "batch/sub/Payslip_2025.txt": "payslip",
        "batch/dup.txt": "dup",
        "loose.txt": "loose",
    }
    for rel, text in files.items():
        path = root / "0_Inbox" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root, settings.state_dir


def op_for(path, leaf="archives_10y_travail", decided_by="auto"):
    decision = Decision(
        path=path,
        sha256=sha256_of(path),
        leaf_id="archives_10y_travail",
        target_dir="4_Archives/10y_travail/2025",
        band="green",
        signal="rules",
        confidence=1.0,
        evidence_summary="rule",
        kind="record",
    )
    return Op(decision, leaf, decided_by)


def apply_all(root, state, ops, run_id=RUN):
    with Journal(state, run_id) as journal:
        return apply_ops(
            ops, config=make_config(), para_root=root, journal=journal, roots=[root / "0_Inbox"]
        )


def test_s5_undo_restores_a_byte_identical_tree(tmp_path):
    root, state = setup(tmp_path)
    before = tree_state(root)
    inbox = root / "0_Inbox"
    ops = [
        op_for(inbox / "batch" / "sub" / "Payslip_2025.txt"),
        op_for(inbox / "batch" / "dup.txt"),
        op_for(inbox / "loose.txt", leaf="archives_5y_factures", decided_by="owner"),
    ]
    report = apply_all(root, state, ops)
    assert len(report.moved) == 2
    assert len(report.trashed) == 1
    assert tree_state(root) != before
    undo = undo_run(state)
    assert undo.run_id == RUN
    assert undo.skipped == []
    assert tree_state(root) == before
    assert is_undone(state, RUN)


def test_changed_destination_is_left_alone(tmp_path):
    root, state = setup(tmp_path)
    src = root / "0_Inbox" / "loose.txt"
    apply_all(root, state, [op_for(src)])
    moved = root / "4_Archives" / "10y_travail" / "2025" / "loose.txt"
    moved.write_text("edited after the run")
    report = undo_run(state, RUN)
    assert report.skipped == [(str(moved), "changed since the run")]
    assert moved.exists()
    assert not src.exists()


def test_taken_source_path_is_left_alone(tmp_path):
    root, state = setup(tmp_path)
    src = root / "0_Inbox" / "loose.txt"
    apply_all(root, state, [op_for(src)])
    src.write_text("a new file with the same name")
    report = undo_run(state, RUN)
    moved = root / "4_Archives" / "10y_travail" / "2025" / "loose.txt"
    assert report.skipped == [(str(moved), "source path taken")]
    assert src.read_text() == "a new file with the same name"


def test_errors(tmp_path):
    root, state = setup(tmp_path)
    with pytest.raises(UndoError, match="no run"):
        undo_run(state)
    apply_all(root, state, [op_for(root / "0_Inbox" / "loose.txt")])
    with pytest.raises(UndoError, match="no journal for run 20200101-000000"):
        undo_run(state, "20200101-000000")
    undo_run(state, RUN)
    with pytest.raises(UndoError, match="already undone"):
        undo_run(state, RUN)


def test_interrupted_apply_is_fully_undoable(tmp_path, monkeypatch):
    root, state = setup(tmp_path)
    before = tree_state(root)
    real_move = apply_mod.shutil.move
    calls = []

    def move_then_stop(src, dst):
        calls.append(src)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return real_move(src, dst)

    monkeypatch.setattr(apply_mod.shutil, "move", move_then_stop)
    inbox = root / "0_Inbox"
    ops = [op_for(inbox / "loose.txt"), op_for(inbox / "batch" / "sub" / "Payslip_2025.txt")]
    with pytest.raises(KeyboardInterrupt):
        apply_all(root, state, ops)
    monkeypatch.setattr(apply_mod.shutil, "move", real_move)
    undo_run(state, RUN)
    assert tree_state(root) == before


def test_dangling_symlink_at_source_is_left_alone(tmp_path):
    root, state = setup(tmp_path)
    src = root / "0_Inbox" / "loose.txt"
    apply_all(root, state, [op_for(src)])
    src.symlink_to(root / "nowhere.txt")
    report = undo_run(state, RUN)
    moved = root / "4_Archives" / "10y_travail" / "2025" / "loose.txt"
    assert report.skipped == [(str(moved), "source path taken")]
    assert src.is_symlink()
    assert moved.read_text() == "loose"


def test_missing_destination_is_skipped(tmp_path):
    root, state = setup(tmp_path)
    src = root / "0_Inbox" / "loose.txt"
    apply_all(root, state, [op_for(src)])
    moved = root / "4_Archives" / "10y_travail" / "2025" / "loose.txt"
    moved.unlink()
    report = undo_run(state, RUN)
    assert report.skipped == [(str(moved), "missing")]
    assert not src.exists()


def test_folder_not_empty_is_kept(tmp_path):
    root, state = setup(tmp_path)
    src = root / "0_Inbox" / "loose.txt"
    apply_all(
        root,
        state,
        [op_for(src, leaf="archives_5y_factures", decided_by="owner")],
    )
    folder = root / "4_Archives" / "5y_factures"
    newcomer = folder / "new.txt"
    newcomer.write_text("added after the run")
    report = undo_run(state, RUN)
    assert folder in report.kept_dirs
    assert report.skipped == []
    assert is_undone(state, RUN)
    assert folder.is_dir()
    assert newcomer.read_text() == "added after the run"
    assert src.exists()


def test_interrupt_after_the_move_returns_is_undoable(tmp_path, monkeypatch):
    root, state = setup(tmp_path)
    before = tree_state(root)
    real_move = apply_mod.shutil.move
    calls = []

    def move_then_stop(src, dst):
        calls.append(src)
        real_move(src, dst)
        if len(calls) == 2:
            raise KeyboardInterrupt

    monkeypatch.setattr(apply_mod.shutil, "move", move_then_stop)
    inbox = root / "0_Inbox"
    ops = [op_for(inbox / "loose.txt"), op_for(inbox / "batch" / "sub" / "Payslip_2025.txt")]
    with pytest.raises(KeyboardInterrupt):
        apply_all(root, state, ops)
    monkeypatch.setattr(apply_mod.shutil, "move", real_move)
    undo_run(state, RUN)
    assert tree_state(root) == before


def test_owner_confirmation_restores_nothing(tmp_path):
    root, state = setup(tmp_path)
    folder = root / "4_Archives" / "10y_travail" / "2025"
    folder.mkdir(parents=True, exist_ok=True)
    src = folder / "Payslip_2025.txt"
    src.write_text("payslip")
    before = tree_state(root)
    with Journal(state, RUN) as journal:
        report = apply_ops(
            [op_for(src, decided_by="owner")],
            config=make_config(),
            para_root=root,
            journal=journal,
            roots=[root / "0_Inbox"],
        )
    assert report.skipped == [(src, "already in place")]
    undo = undo_run(state, RUN)
    assert undo.restored == []
    assert undo.skipped == []
    assert tree_state(root) == before


def test_run_with_a_skipped_entry_stays_undoable(tmp_path):
    root, state = setup(tmp_path)
    before = tree_state(root)
    src = root / "0_Inbox" / "loose.txt"
    apply_all(root, state, [op_for(src)])
    blocker = src.parent / "loose.txt"
    blocker.write_text("a new file took the old name")
    first = undo_run(state)
    moved = root / "4_Archives" / "10y_travail" / "2025" / "loose.txt"
    assert (str(moved), "source path taken") in first.skipped
    assert not is_undone(state, RUN)
    assert last_run_id(state) == RUN
    blocker.unlink()
    second = undo_run(state)
    assert second.skipped == []
    assert second.restored == [src]
    assert is_undone(state, RUN)
    assert tree_state(root) == before


def test_run_id_must_look_like_a_run_id(tmp_path):
    root, state = setup(tmp_path)
    apply_all(root, state, [op_for(root / "0_Inbox" / "loose.txt")])
    with pytest.raises(UndoError, match="not a run id"):
        undo_run(state, "../x")
    assert not is_undone(state, RUN)


def test_retry_after_a_blocked_file_reports_nothing_missing(tmp_path):
    root, state = setup(tmp_path)
    before = tree_state(root)
    inbox = root / "0_Inbox"
    first_src = inbox / "batch" / "sub" / "Payslip_2025.txt"
    second_src = inbox / "loose.txt"
    apply_all(root, state, [op_for(first_src), op_for(second_src)])
    second_src.write_text("a new file took the old name")
    first = undo_run(state)
    assert [reason for _, reason in first.skipped] == ["source path taken"]
    assert not is_undone(state, RUN)
    second_src.unlink()
    second = undo_run(state)
    assert second.skipped == []
    assert second.restored == [second_src]
    assert is_undone(state, RUN)
    assert tree_state(root) == before


def test_folder_holding_a_later_runs_file_is_kept_not_blocking(tmp_path):
    root, state = setup(tmp_path)
    src = root / "0_Inbox" / "loose.txt"
    apply_all(root, state, [op_for(src, leaf="archives_5y_factures", decided_by="owner")])
    folder = root / "4_Archives" / "5y_factures"
    later = folder / "later.txt"
    later.write_text("filed by a later run")
    report = undo_run(state, RUN)
    assert report.skipped == []
    assert folder in report.kept_dirs
    assert is_undone(state, RUN)
    assert later.exists()
    assert src.read_text() == "loose"
