"""`init`: list missing leaf folders; create them with --apply."""

from __future__ import annotations

from typer.testing import CliRunner

from para_files.cli import app
from tests.core_helpers import setup_cli


runner = CliRunner()


def test_preview_then_create(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    preview = runner.invoke(app, ["init"])
    assert preview.exit_code == 0, preview.output
    assert "missing  4_Archives/10y_travail" in preview.output
    assert not (root / "4_Archives" / "10y_travail").exists()
    created = runner.invoke(app, ["init", "--apply"])
    assert created.exit_code == 0, created.output
    assert (root / "4_Archives" / "10y_travail").is_dir()
    assert runner.invoke(app, ["init"]).output.strip().endswith("every folder exists")


def test_new_root_given_explicitly(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    fresh = tmp_path / "NewPARA"
    result = runner.invoke(app, ["init", str(fresh), "--apply"])
    assert result.exit_code == 0, result.output
    assert (fresh / "0_Inbox").is_dir()
    assert (fresh / "3_Resources" / "livres").is_dir()


def test_bucket_is_refused(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    result = runner.invoke(app, ["init", str(root / "0_Inbox")])
    assert result.exit_code == 2
    assert "is a bucket" in result.output


def test_missing_root_names_the_variable(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    monkeypatch.delenv("PARA_FILES_PARA_ROOT", raising=False)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 2, result.output
    assert "PARA_FILES_PARA_ROOT" in result.output


def _folder_names(base):
    return sorted(path.relative_to(base).as_posix() for path in base.rglob("*"))


def test_init_apply_is_undoable(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    fresh = tmp_path / "NewPARA"
    (fresh / "0_Inbox").mkdir(parents=True)
    before = _folder_names(fresh)
    created = runner.invoke(app, ["init", str(fresh), "--apply"])
    assert created.exit_code == 0, created.output
    assert "undo with: para-files undo" in created.output
    assert (fresh / "3_Resources" / "livres").is_dir()
    undone = runner.invoke(app, ["undo"])
    assert undone.exit_code == 0, undone.output
    assert _folder_names(fresh) == before


def test_root_under_missing_parent_is_refused(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    missing = tmp_path / "nowhere" / "PARA"
    result = runner.invoke(app, ["init", str(missing), "--apply"])
    assert result.exit_code == 2, result.output
    assert "parent folder does not exist" in result.output
    assert not (tmp_path / "nowhere").exists()


def test_fresh_root_from_the_environment(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    fresh = tmp_path / "NewPARA"
    state = tmp_path / "init-state"
    monkeypatch.setenv("PARA_FILES_PARA_ROOT", str(fresh))
    monkeypatch.setenv("PARA_FILES_STATE_DIR", str(state))
    created = runner.invoke(app, ["init", "--apply"])
    assert created.exit_code == 0, created.output
    assert (fresh / "0_Inbox").is_dir()
    assert list((state / "journal").glob("*.jsonl"))
    run_id = created.output.split("para-files undo ")[1].split()[0]
    undone = runner.invoke(app, ["undo", run_id])
    assert undone.exit_code == 0, undone.output
    assert not (fresh / "3_Resources" / "livres").exists()
