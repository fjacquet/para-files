"""core.clean: junk and duplicates to .trash, empty folders removed, all undoable."""

from __future__ import annotations

from para_files.core.clean import apply_clean, is_junk, plan_clean
from para_files.core.journal import Journal
from para_files.core.undo import undo_run
from tests.core_helpers import make_para_root


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
    put(root, ".trash/r1/old.txt")
    plan = plan_clean([root], root=root, duplicates=True)
    assert junk in plan.junk
    assert root / ".trash/r1/old.txt" not in plan.junk
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
    with Journal(tmp_path / "state", "r1") as journal:
        report = apply_clean(plan, root=root, journal=journal)
    assert len(report.trashed) == 2
    assert not (root / "2_Areas/a").exists()
    assert not (root / "1_Projets/empty").exists()
    assert (root / ".trash/r1/3_Resources/y/report copy.pdf").exists()
    undo_run(tmp_path / "state", "r1")
    assert tree_state(root) == before
