"""`undo`: reverse the last run, or a named one; errors are readable."""

from __future__ import annotations

from typer.testing import CliRunner

from para_files.cli import app
from tests.core_helpers import setup_cli


runner = CliRunner()


def test_sort_then_undo_restores_the_inbox(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    payslip = root / "0_Inbox" / "Payslip_2025-12.txt"
    payslip.write_text("payslip")
    assert runner.invoke(app, ["sort", "--apply"]).exit_code == 0
    assert not payslip.exists()
    result = runner.invoke(app, ["undo"])
    assert result.exit_code == 0, result.output
    assert "1 restored" in result.output
    assert payslip.read_text() == "payslip"
    assert not (root / "4_Archives" / "10y_travail").exists()


def test_nothing_to_undo(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    result = runner.invoke(app, ["undo"])
    assert result.exit_code == 1
    assert "no run to undo" in result.output


def test_unknown_run(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    result = runner.invoke(app, ["undo", "20200101-000000"])
    assert result.exit_code == 1
    assert "no journal for run 20200101-000000" in result.output
