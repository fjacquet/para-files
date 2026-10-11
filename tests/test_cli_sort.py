"""`sort`: preview by default, --apply moves green, --review confirms yellow."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from para_files.cli import app
from para_files.core.journal import confirmed_counts, last_run_id, read_run
from tests.core_helpers import make_config, setup_cli


runner = CliRunner()


def put(root, rel, text="x"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_preview_moves_nothing(tmp_path, monkeypatch, snapshot):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/Payslip_2025-12.txt", "payslip")
    put(root, "0_Inbox/notes.md", "# notes")
    before = snapshot(root)
    result = runner.invoke(app, ["sort"])
    assert result.exit_code == 0, result.output
    assert "GREEN (1)" in result.output
    assert "YELLOW (1)" in result.output
    assert "Payslip_2025-12.txt  ->  4_Archives/10y_travail/2025" in result.output
    assert snapshot(root) == before


def test_apply_moves_green_only(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/Payslip_2025-12.txt", "payslip")
    notes = put(root, "0_Inbox/notes.md", "# notes")
    result = runner.invoke(app, ["sort", "--apply"])
    assert result.exit_code == 0, result.output
    assert (root / "4_Archives/10y_travail/2025/Payslip_2025-12.txt").exists()
    assert notes.exists()
    assert "1 moved" in result.output
    assert "undo with: para-files undo" in result.output


def test_review_accept_and_correct(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/a_notes.md", "# a")
    put(root, "0_Inbox/b_notes.md", "# b")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="o\n\narchives_5y\n")
    assert result.exit_code == 0, result.output
    assert (root / "3_Resources/IT/a_notes.md").exists()
    assert (root / "4_Archives/5y_factures/b_notes.md").exists()
    entries = read_run(tmp_path / "state", last_run_id(tmp_path / "state"))
    moves = [(e["leaf"], e["proposed_leaf"], e["decided_by"]) for e in entries if e["op"] == "move"]
    assert moves == [
        ("resources_it", "resources_it", "owner"),
        ("archives_5y_factures", "resources_it", "owner"),
    ]
    assert confirmed_counts(tmp_path / "state", make_config().tree) == {
        "knowledge": 1,
        "record": 1,
    }


def test_review_end_of_input_keeps_what_was_confirmed(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/a_notes.md", "# a")
    b = put(root, "0_Inbox/b_notes.md", "# b")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="o\n\n")
    assert result.exit_code == 0, result.output
    assert (root / "3_Resources/IT/a_notes.md").exists()
    assert b.exists()


def test_review_skip_unknown_and_stop(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    a = put(root, "0_Inbox/a_notes.md", "# a")
    b = put(root, "0_Inbox/b_notes.md", "# b")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="o\nnope\ns\nq\n")
    assert result.exit_code == 0, result.output
    assert "unknown or ambiguous leaf: 'nope'" in result.output
    assert a.exists()
    assert b.exists()


def test_review_needs_apply(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    result = runner.invoke(app, ["sort", "--review"])
    assert result.exit_code == 2
    assert "--review needs --apply" in result.output


def test_json_plan(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/Payslip_2025-12.txt", "payslip")
    put(root, "0_Inbox/passwords.txt", "x")
    result = runner.invoke(app, ["sort", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["summary"]["files"] == 2
    assert data["summary"]["green"] == 1
    assert data["summary"]["secrets"] == 1
    paths = {d["path"]: d for d in data["decisions"]}
    assert paths["0_Inbox/Payslip_2025-12.txt"]["target"] == "4_Archives/10y_travail/2025"
    assert "applied" not in data


def test_secrets_are_listed_and_never_moved(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    secret = put(root, "0_Inbox/passwords.txt", "x")
    result = runner.invoke(app, ["sort", "--apply"])
    assert result.exit_code == 0, result.output
    assert "SECRETS (1)" in result.output
    assert secret.exists()


def test_missing_path_is_an_error(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    result = runner.invoke(app, ["sort", str(tmp_path / "nowhere")])
    assert result.exit_code == 2
    assert "no such file or folder" in result.output


def test_review_confirmation_of_a_file_in_place_counts(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    notes = put(root, "3_Resources/IT/a_notes.md", "# a")
    result = runner.invoke(
        app, ["sort", str(root / "3_Resources" / "IT"), "--apply", "--review"], input="\n"
    )
    assert result.exit_code == 0, result.output
    assert notes.exists()
    tree = runner.invoke(app, ["tree"])
    assert tree.exit_code == 0, tree.output
    assert "knowledge     1 confirmed" in tree.output


def test_dot_folder_input_is_refused_and_nothing_moves(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    trashed = put(root, ".trash/r1/Payslip_2025.txt", "payslip")
    result = runner.invoke(app, ["sort", str(root / ".trash" / "r1"), "--apply"])
    assert result.exit_code == 2, result.output
    assert "dot-folders are never sorted" in result.output
    assert trashed.exists()
    assert not (root / "4_Archives").joinpath("10y_travail").exists()


def test_folder_outside_the_root_is_previewed(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    outside = tmp_path / "elsewhere"
    put(outside, "note.txt", "x")
    result = runner.invoke(app, ["sort", str(outside)])
    assert result.exit_code == 0, result.output


def test_sorting_a_bucket_keeps_its_leaf_folders(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    payslip = put(root, "3_Resources/IT/Payslip_2025.txt", "payslip")
    result = runner.invoke(app, ["sort", str(root / "3_Resources"), "--apply"])
    assert result.exit_code == 0, result.output
    assert not payslip.exists()
    assert (root / "4_Archives/10y_travail/2025/Payslip_2025.txt").exists()
    assert (root / "3_Resources/IT").is_dir()
    assert (root / "3_Resources").is_dir()


def test_apply_with_nothing_to_move_journals_nothing(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    result = runner.invoke(app, ["sort", "--apply"])
    assert result.exit_code == 0, result.output
    assert "nothing to move" in result.output
    assert "undo with" not in result.output
    assert not (tmp_path / "state" / "journal").exists()
    assert root.is_dir()


def test_json_apply_with_nothing_to_move_omits_applied(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    result = runner.invoke(app, ["sort", "--apply", "--json"])
    assert result.exit_code == 0, result.output
    assert "applied" not in json.loads(result.output)


def test_review_refuses_without_a_terminal(tmp_path, monkeypatch):
    from para_files.cli import review as review_cli

    root = setup_cli(tmp_path, monkeypatch)
    monkeypatch.setattr(review_cli, "stdin_is_tty", lambda: False)
    note = put(root, "0_Inbox/a_notes.md", "# a")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="\n")
    assert result.exit_code != 0
    assert "needs a terminal" in result.output
    assert note.exists()


def test_plan_groups_yellow_files_by_folder_and_counts_hints(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/a_notes.md", "# a")
    put(root, "0_Inbox/b_notes.md", "# b")
    put(root, "0_Inbox/statement.txt", "AcmeCard statement")
    result = runner.invoke(app, ["sort"])
    assert result.exit_code == 0, result.output
    assert "  resources_it (2)" in result.output
    assert "  archives_10y_banques (1)" in result.output
    assert "3 files decided by hints only (model off or did not answer)" in result.output


def test_json_has_ranked_about_and_by_signal(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/a_notes.md", "AcmeCard # a")
    result = runner.invoke(app, ["sort", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    decision = data["decisions"][0]
    assert decision["ranked"] == [["resources_it", 1.0], ["archives_10y_banques", 0.8]]
    assert decision["about"] is None
    assert data["summary"]["by_signal"] == {"hint": 1}


def test_review_accepts_a_whole_group(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    for name in ("a_notes.md", "b_notes.md", "c_notes.md"):
        put(root, f"0_Inbox/{name}", "# x")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="\n")
    assert result.exit_code == 0, result.output
    assert "resources_it -> 3_Resources/IT (3 files)" in result.output
    for name in ("a_notes.md", "b_notes.md", "c_notes.md"):
        assert (root / "3_Resources/IT" / name).exists()


def test_review_retargets_a_whole_group(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/a_notes.md", "# a")
    put(root, "0_Inbox/b_notes.md", "# b")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="archives_5y\n")
    assert result.exit_code == 0, result.output
    assert (root / "4_Archives/5y_factures/a_notes.md").exists()
    assert (root / "4_Archives/5y_factures/b_notes.md").exists()


def test_review_one_by_one_then_stop_keeps_what_was_confirmed(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/a_notes.md", "# a")
    b = put(root, "0_Inbox/b_notes.md", "# b")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="o\n\nq\n")
    assert result.exit_code == 0, result.output
    assert (root / "3_Resources/IT/a_notes.md").exists()
    assert b.exists()


def test_review_picks_a_ranked_alternative(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/acme_2026.md", "AcmeCard statement")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="2\n")
    assert result.exit_code == 0, result.output
    entries = read_run(tmp_path / "state", last_run_id(tmp_path / "state"))
    moves = [(e["leaf"], e["proposed_leaf"]) for e in entries if e["op"] == "move"]
    assert moves == [("archives_10y_banques", "resources_it")]
