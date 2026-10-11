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
