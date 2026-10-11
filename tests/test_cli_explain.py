"""`explain`: evidence, every signal's verdict, the decision, what to edit; no side effects."""

from __future__ import annotations

from typer.testing import CliRunner

from para_files.cli import app
from para_files.core import decide
from para_files.core.evidence import extract
from tests.core_helpers import setup_cli


runner = CliRunner()


def test_rule_match_is_explained(tmp_path, monkeypatch, snapshot):
    root = setup_cli(tmp_path, monkeypatch)
    path = root / "0_Inbox" / "Payslip_2025-12.txt"
    path.write_text("AcmeCard payslip")
    before = snapshot(root)
    result = runner.invoke(app, ["explain", str(path)])
    assert result.exit_code == 0, result.output
    assert "pinned rule  archives_10y_travail (1.00): pinned rule 'payslips'" in result.output
    assert "hint         archives_10y_banques" not in result.output
    assert "decision: green, archives_10y_travail -> 4_Archives/10y_travail/2025" in result.output
    assert "edit or unpin this rule in rules.yaml" in result.output
    assert snapshot(root) == before


def test_nothing_matches(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    path = root / "0_Inbox" / "random.txt"
    path.write_text("hello")
    result = runner.invoke(app, ["explain", str(path)])
    assert result.exit_code == 0, result.output
    assert "decision: red, no leaf -> stays in place" in result.output
    assert "add a rule (rules.yaml) or an issuer (issuers.yaml)" in result.output


def test_secret_shows_only_the_reason(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    path = root / "0_Inbox" / "notes.txt"
    path.write_text("vpn\npassword: hunter22\n")
    result = runner.invoke(app, ["explain", str(path)])
    assert result.exit_code == 0, result.output
    assert "secret (credential_value): never sent, never moved" in result.output
    assert "hunter22" not in result.output
    assert "steps" not in result.output


def test_choose_reports_errors_and_skips_the_model(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    path = root / "0_Inbox" / "a.txt"
    path.write_text("x")

    def boom(*_args):
        msg = "broken rules"
        raise RuntimeError(msg)

    monkeypatch.setattr(decide, "match_rule", boom)
    from para_files.cli.common import context_or_exit, settings_or_exit

    ctx = context_or_exit(settings_or_exit())
    verdict, steps = decide.choose(extract(path, root=root), ctx, ask_model=False)
    assert verdict.signal == "none"
    assert [(step.name, step.note) for step in steps] == [
        ("isbn book", "no verified ISBN"),
        ("pinned rule", "no pinned rule matches"),
        ("hint", "no rule, book or issuer matches"),
        ("model", "off (no key, or PARA_FILES_FALLBACK_ENABLED=false)"),
    ]
