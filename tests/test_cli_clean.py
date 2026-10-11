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
