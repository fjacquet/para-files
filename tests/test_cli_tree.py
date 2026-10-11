"""`tree`: leaves with counts, settings without the key, calibration, warnings."""

from __future__ import annotations

from typer.testing import CliRunner

from para_files.cli import app
from para_files.core.journal import Journal, confirmation_stats
from tests.core_helpers import make_config, setup_cli


runner = CliRunner()


def test_tree_lists_leaves_settings_and_calibration(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-never-printed")
    with Journal(tmp_path / "state", "r1") as journal:
        journal.append(
            {
                "op": "move",
                "leaf": "archives_10y_travail",
                "proposed_leaf": "archives_10y_travail",
                "decided_by": "owner",
            }
        )
        journal.append(
            {
                "op": "move",
                "leaf": "archives_5y_factures",
                "proposed_leaf": "resources_it",
                "decided_by": "owner",
            }
        )
    result = runner.invoke(app, ["tree"])
    assert result.exit_code == 0, result.output
    assert "leaves (7):" in result.output
    assert "archives_10y_travail" in result.output
    assert "fallback       off" in result.output
    assert "record        2 confirmed, proposed right 1 (50%)" in result.output
    assert "sk-never-printed" not in result.output
    assert "warnings" not in result.output


def test_validate_prints_warnings(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    result = runner.invoke(app, ["tree", "--validate"])
    assert result.exit_code == 0, result.output
    assert "warnings (" in result.output
    assert "issuer 'abc': pattern 'ABC' has <= 3 characters" in result.output


def test_broken_config_is_an_error(tmp_path, monkeypatch):
    import os
    from pathlib import Path

    setup_cli(tmp_path, monkeypatch)
    (Path(os.environ["PARA_FILES_CONFIG_DIR"]) / "tree.yaml").write_text("leaves: {}\n")
    result = runner.invoke(app, ["tree"])
    assert result.exit_code == 2
    assert "tree.yaml" in result.output


def test_confirmation_stats(tmp_path):
    with Journal(tmp_path, "r1") as journal:
        journal.append(
            {
                "op": "move",
                "leaf": "resources_it",
                "proposed_leaf": "resources_it",
                "decided_by": "owner",
            }
        )
        journal.append({"op": "move", "leaf": "resources_it", "decided_by": "auto"})
    assert confirmation_stats(tmp_path, make_config().tree) == {"knowledge": (1, 1)}
