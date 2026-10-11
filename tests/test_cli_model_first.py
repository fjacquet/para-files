"""Model first, end to end: pinned rules skip the model, secrets never reach it, hints and
OCR text do, review answers are journaled, undo restores the tree, the cache saves calls."""

from __future__ import annotations

import json
from types import SimpleNamespace

from typer.testing import CliRunner

from para_files.cli import app
from para_files.core import sort as sort_module
from para_files.core.fallback import OpenRouterFallback
from para_files.core.journal import last_run_id, read_run
from para_files.utils.ocr import OCRResult
from tests.core_helpers import setup_cli


runner = CliRunner()


def put(root, rel, text):
    path = root / rel
    path.write_text(text)
    return path


def fake_model(calls):
    def complete(**kwargs):
        user = kwargs["messages"][1]["content"]
        calls.append(user)
        leaf = "archives_10y_banques" if "AcmeCard" in user else "resources_docs"
        content = json.dumps(
            {
                "about": "test document",
                "choices": [
                    {"leaf": leaf, "confidence": 0.8},
                    {"leaf": "archives_5y_factures", "confidence": 0.1},
                ],
            }
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    return complete


def test_model_first_end_to_end(tmp_path, monkeypatch, snapshot):
    calls: list[str] = []
    root = setup_cli(tmp_path, monkeypatch)
    monkeypatch.setattr(
        sort_module,
        "make_fallback",
        lambda _settings, **_kw: OpenRouterFallback("key", ["m1"], complete=fake_model(calls)),
    )
    monkeypatch.setattr(
        "para_files.utils.ocr.extract_text",
        lambda *_a, **_k: OCRResult(
            text="AcmeCard invoice 2026 scanned", confidence=0.9, word_count=4
        ),
    )
    put(root, "0_Inbox/Payslip_2026-01.txt", "salary")
    put(root, "0_Inbox/passwords.txt", "vpn\npassword: hunter22\n")
    put(root, "0_Inbox/acme_2026.md", "AcmeCard statement")
    (root / "0_Inbox/scan.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    before = snapshot(root)

    preview = runner.invoke(app, ["sort", "--json"])
    assert preview.exit_code == 0, preview.output
    plan = {d["path"]: d for d in json.loads(preview.output)["decisions"]}
    assert plan["0_Inbox/Payslip_2026-01.txt"]["signal"] == "rules"
    assert plan["0_Inbox/passwords.txt"]["signal"] == "secret"
    acme = plan["0_Inbox/acme_2026.md"]
    assert (acme["signal"], acme["band"]) == ("fallback", "yellow")
    assert acme["target"] == "4_Archives/10y_banques/acmecard/2026"
    assert acme["about"] == "test document"
    sent = "\n".join(calls)
    assert "Payslip_2026-01" not in sent
    assert "hunter22" not in sent
    assert "passwords.txt" not in sent
    assert "rule 'it_notes'" in sent
    assert "issuer 'acmecard'" in sent
    assert "AcmeCard invoice 2026 scanned" in sent
    asked = len(calls)

    again = runner.invoke(app, ["sort", "--json"])
    assert again.exit_code == 0, again.output
    assert len(calls) == asked

    # One yellow group (two files): a single Enter accepts it.
    applied = runner.invoke(app, ["sort", "--apply", "--review"], input="\n")
    assert applied.exit_code == 0, applied.output
    assert (root / "4_Archives/10y_travail/2026/Payslip_2026-01.txt").exists()
    assert (root / "4_Archives/10y_banques/acmecard/2026/acme_2026.md").exists()
    assert (root / "0_Inbox/passwords.txt").exists()
    entries = read_run(tmp_path / "state", last_run_id(tmp_path / "state"))
    owner = [e for e in entries if e["op"] == "move" and e["decided_by"] == "owner"]
    assert {e["leaf"] for e in owner} == {"archives_10y_banques"}

    undone = runner.invoke(app, ["undo"])
    assert undone.exit_code == 0, undone.output
    after = snapshot(root)
    assert after.keys() == before.keys()  # no leftover entries
    # Directory mtimes change when entries leave and come back; every file must be unchanged.
    files = [name for name in before if (root / name).is_file()]
    assert {name: after[name] for name in files} == {name: before[name] for name in files}
