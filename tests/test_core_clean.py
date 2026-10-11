"""core.clean: junk and duplicates to .trash, empty folders removed, all undoable."""

from __future__ import annotations

import pytest

from para_files.core.clean import CleanPlan, apply_clean, is_junk, kept_folders, plan_clean
from para_files.core.journal import Journal
from para_files.core.undo import undo_run
from tests.core_helpers import make_config, make_para_root


def put(root, rel, text="x"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def tree_state(root):
    return {
        p.relative_to(root).as_posix(): (p.read_bytes() if p.is_file() else None)
        for p in root.rglob("*")
    }


def test_is_junk():
    assert is_junk(".DS_Store")
    assert is_junk("Thumbs.db")
    assert is_junk("~$report.docx")
    assert is_junk("._photo.jpg")
    assert not is_junk("report.docx")


def test_plan_finds_junk_empty_folders_and_duplicates(tmp_path):
    root = make_para_root(tmp_path)
    junk = put(root, "2_Areas/a/.DS_Store")
    put(root, "2_Areas/a/b/Thumbs.db")
    keep = put(root, "3_Resources/x/report.pdf", "same")
    copy = put(root, "3_Resources/y/report copy.pdf", "same")
    put(root, "3_Resources/y/other.pdf", "different")
    put(root, ".trash/20261011-100000/old.txt")
    plan = plan_clean([root], root=root, duplicates=True)
    assert junk in plan.junk
    assert root / ".trash/20261011-100000/old.txt" not in plan.junk
    assert plan.duplicates == [(copy, keep)]
    assert plan.empty_dirs[:2] == [root / "2_Areas/a/b", root / "2_Areas/a"]


def test_duplicates_only_when_asked_and_never_secrets(tmp_path):
    root = make_para_root(tmp_path)
    put(root, "3_Resources/x/a.txt", "password: hunter22\n")
    put(root, "3_Resources/y/b.txt", "password: hunter22\n")
    assert plan_clean([root], root=root, duplicates=False).duplicates == []
    assert plan_clean([root], root=root, duplicates=True).duplicates == []


def test_apply_then_undo_restores_everything(tmp_path):
    root = make_para_root(tmp_path)
    put(root, "2_Areas/a/.DS_Store", "junk")
    put(root, "3_Resources/x/report.pdf", "same")
    put(root, "3_Resources/y/report copy.pdf", "same")
    (root / "1_Projets" / "empty").mkdir()
    before = tree_state(root)
    plan = plan_clean([root], root=root, duplicates=True)
    with Journal(tmp_path / "state", "20261011-100000") as journal:
        report = apply_clean(plan, root=root, journal=journal)
    assert len(report.trashed) == 2
    assert not (root / "2_Areas/a").exists()
    assert not (root / "1_Projets/empty").exists()
    assert (root / ".trash/20261011-100000/3_Resources/y/report copy.pdf").exists()
    undo_run(tmp_path / "state", "20261011-100000")
    assert tree_state(root) == before


def test_plan_refuses_dot_folder_base(tmp_path):
    root = make_para_root(tmp_path)
    put(root, ".git/config", "x")
    with pytest.raises(ValueError, match="dot-folder"):
        plan_clean([root / ".git"], root=root, duplicates=False)


def test_plan_refuses_base_outside_root(tmp_path):
    root = make_para_root(tmp_path)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    with pytest.raises(ValueError, match="PARA root"):
        plan_clean([outside], root=root, duplicates=False)


def test_apply_skips_planted_outside_source(tmp_path):
    root = make_para_root(tmp_path)
    outside = put(tmp_path, "elsewhere/notes.txt", "keep me")
    plan = CleanPlan(junk=[outside])
    with Journal(tmp_path / "state", "20261011-100000") as journal:
        report = apply_clean(plan, root=root, journal=journal)
    assert report.trashed == []
    assert (outside, "outside the PARA root") in report.skipped
    assert outside.read_text() == "keep me"


def test_duplicate_changed_after_planning_is_skipped(tmp_path):
    root = make_para_root(tmp_path)
    keep = put(root, "3_Resources/x/report.pdf", "same")
    copy = put(root, "3_Resources/y/report copy.pdf", "same")
    plan = plan_clean([root], root=root, duplicates=True)
    assert plan.duplicates == [(copy, keep)]
    copy.write_text("edited after the preview")
    with Journal(tmp_path / "state", "20261011-100000") as journal:
        report = apply_clean(plan, root=root, journal=journal)
    assert report.trashed == []
    assert [reason for _, reason in report.skipped] == ["no longer identical"]
    assert copy.read_text() == "edited after the preview"


def test_duplicate_with_missing_original_is_skipped(tmp_path):
    root = make_para_root(tmp_path)
    keep = put(root, "3_Resources/x/report.pdf", "same")
    copy = put(root, "3_Resources/y/report copy.pdf", "same")
    plan = plan_clean([root], root=root, duplicates=True)
    keep.unlink()
    with Journal(tmp_path / "state", "20261011-100000") as journal:
        report = apply_clean(plan, root=root, journal=journal)
    assert report.trashed == []
    assert [reason for _, reason in report.skipped] == ["original missing"]
    assert copy.exists()


def test_secret_named_junk_is_not_planned(tmp_path):
    root = make_para_root(tmp_path)
    secret = put(root, "2_Areas/a/._passwords.txt", "x")
    junk = put(root, "2_Areas/a/.DS_Store", "x")
    plan = plan_clean([root], root=root, duplicates=False)
    assert secret not in plan.junk
    assert junk in plan.junk


def test_kept_folders_are_buckets_and_leaves(tmp_path):
    root = make_para_root(tmp_path)
    put(root, "3_Resources/x/keep.txt")
    kept = kept_folders(root, make_config())
    assert root / "3_Resources" in kept
    assert root / "3_Resources" / "IT" in kept
    assert root / "3_Resources" / "x" not in kept
    assert root / ".trash" not in kept


def test_folder_holding_only_secret_junk_is_not_empty(tmp_path):
    root = make_para_root(tmp_path)
    secret = put(root, "2_Areas/vault/._passwords.txt", "x")
    plan = plan_clean([root], root=root, duplicates=False)
    assert secret.exists()
    assert root / "2_Areas/vault" not in plan.empty_dirs
    assert secret not in plan.junk


def test_inbox_copy_is_trashed_and_the_filed_one_kept(tmp_path):
    root = make_para_root(tmp_path)
    inbox = put(root, "0_Inbox/invoice.pdf", "same")
    filed = put(root, "2_Areas/x/invoice.pdf", "same")
    plan = plan_clean([root], root=root, duplicates=True)
    assert plan.duplicates == [(inbox, filed)]


def test_copy_suffix_is_trashed_and_the_plain_name_kept(tmp_path):
    root = make_para_root(tmp_path)
    plain = put(root, "2_Areas/x/a.pdf", "same")
    copy = put(root, "2_Areas/x/a (2).pdf", "same")
    plan = plan_clean([root], root=root, duplicates=True)
    assert plan.duplicates == [(copy, plain)]


def test_overlapping_inputs_never_pair_a_file_with_itself(tmp_path):
    root = make_para_root(tmp_path)
    put(root, "2_Areas/A/B/x.pdf", "same")
    put(root, "2_Areas/A/y.pdf", "same")
    put(root, "2_Areas/A/B/.DS_Store")
    area = root / "2_Areas" / "A"
    plan = plan_clean([area, area / "B"], root=root, duplicates=True)
    assert len(plan.duplicates) == 1
    copy, kept = plan.duplicates[0]
    assert copy != kept
    assert len(plan.junk) == 1
    assert len(plan.empty_dirs) == len(set(plan.empty_dirs))
