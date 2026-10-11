"""`clean`: preview by default, --apply journals, refuses paths outside the root."""

from __future__ import annotations

from typer.testing import CliRunner

from para_files.cli import app
from tests.core_helpers import setup_cli


runner = CliRunner()


def test_preview_then_apply(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    junk = root / "2_Areas" / "a" / ".DS_Store"
    junk.parent.mkdir(parents=True)
    junk.write_text("junk")
    preview = runner.invoke(app, ["clean"])
    assert preview.exit_code == 0, preview.output
    assert "2_Areas/a/.DS_Store" in preview.output
    assert "preview only" in preview.output
    assert junk.exists()
    applied = runner.invoke(app, ["clean", "--apply"])
    assert applied.exit_code == 0, applied.output
    assert not junk.exists()
    assert "undo with: para-files undo" in applied.output


def test_outside_root_is_refused(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    result = runner.invoke(app, ["clean", str(outside)])
    assert result.exit_code == 2
    assert "only works inside the PARA root" in result.output


def test_dot_folder_is_refused(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    git = root / ".git"
    git.mkdir()
    (git / "config").write_text("x")
    result = runner.invoke(app, ["clean", str(git)])
    assert result.exit_code == 2
    assert "dot-folders" in result.output
    assert (git / "config").exists()


def test_bucket_and_leaf_folders_survive_apply(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    leaf = root / "4_Archives" / "10y_travail"
    leaf.mkdir(parents=True)
    scratch = root / "3_Resources" / "scratch"
    scratch.mkdir(parents=True)
    applied = runner.invoke(app, ["clean", "--apply"])
    assert applied.exit_code == 0, applied.output
    assert leaf.is_dir()
    assert (root / "3_Resources").is_dir()
    assert (root / "1_Projets").is_dir()
    assert not scratch.exists()
