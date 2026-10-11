"""Tests for scripts/bakeoff.py: privacy flags, secrets guard, parsing, scope (no network)."""

from __future__ import annotations

import json
import signal
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest


MENU = {"inv": "Invoices", "notes": "Notes"}


class FakePost:
    """Records requests and replays canned responses; never touches the network."""

    def __init__(self, *responses: httpx.Response) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def __call__(self, url: str, **kwargs) -> httpx.Response:
        self.calls.append({"url": url, **kwargs})
        response = self.responses.pop(0)
        response.request = httpx.Request("POST", url)
        return response


def _chat(content: str) -> httpx.Response:
    payload = {"choices": [{"message": {"content": content}}], "usage": {"cost": 0.001}}
    return httpx.Response(200, json=payload)


def _recording_post(calls: list[object]):
    """A post that records every call (a failure inside predict would hide an AssertionError)."""

    def post(*args: object, **kwargs: object) -> httpx.Response:
        calls.append((args, kwargs))
        msg = "a secret file must never be sent"
        raise AssertionError(msg)

    return post


@pytest.fixture
def bakeoff(load_script):
    return load_script("bakeoff")


@pytest.mark.parametrize(("ask", "model"), [("ask_gemini", "GEMINI"), ("ask_sonnet", "SONNET")])
def test_llm_request_enforces_zdr_and_low_reasoning(bakeoff, ask, model):
    post = FakePost(_chat('{"choices": [{"leaf": "notes", "confidence": 0.7}]}'))
    ranked, cost = getattr(bakeoff, ask)(post, "k", MENU, "a.pdf", "text")
    body = post.calls[0]["json"]
    assert body["model"] == getattr(bakeoff, model)
    assert body["provider"] == {"zdr": True, "data_collection": "deny"}
    assert body["reasoning"] == {"effort": "low"}
    assert body["max_tokens"] == 4000
    schema = body["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["choices"]["items"]["properties"]["leaf"]["enum"] == [
        "inv",
        "notes",
    ]
    assert ranked == [("notes", 0.7)]
    assert cost == pytest.approx(0.001)


def test_candidates_follow_owner_preference(bakeoff):
    assert list(bakeoff.CANDIDATES) == ["gemini", "sonnet", "jev"]


def test_jev_request_enforces_zdr_and_ranks_probabilities(bakeoff):
    answer = {
        "leaf": {
            "type": "choice",
            "choice": "notes",
            "probabilities": {"inv": 0.2, "notes": 0.7, "bogus": 0.1},
        }
    }
    post = FakePost(httpx.Response(200, json={"answers": answer, "usage": {"cost": 0.0002}}))
    ranked, _cost = bakeoff.ask_jev(post, "k", MENU, "a.pdf", "text")
    body = post.calls[0]["json"]
    assert body["provider"] == {"zdr": True, "data_collection": "deny"}
    assert body["questions"]["leaf"]["criteria"] == MENU
    assert ranked == [("notes", 0.7), ("inv", 0.2)]


def test_parse_choices_drops_unknown_and_duplicate_leaves(bakeoff):
    text = (
        'noise {"choices": [{"leaf": "zzz", "confidence": 0.9}, '
        '{"leaf": "inv", "confidence": 1.4}, {"leaf": "inv", "confidence": 0.2}]}'
    )
    assert bakeoff.parse_choices(text, MENU) == [("inv", 1.0)]
    assert bakeoff.parse_choices("not json", MENU) == []


def test_secret_named_file_is_never_sent(bakeoff, tmp_path: Path):
    calls: list[object] = []
    row = {
        "path": "0_Inbox/wallet_recovery_phrase.txt",
        "leaf": "notes",
        "kind": "knowledge",
        "scope": "b",
    }
    pred = bakeoff.predict(
        row, tmp_path, MENU, bakeoff.ask_jev, _recording_post(calls), "k", lambda _p: ""
    )
    assert (pred["band"], pred["signal"], pred["leaf"]) == ("red", "secret", None)
    assert calls == []


def test_secret_content_is_never_sent(bakeoff, tmp_path: Path):
    calls: list[object] = []
    row = {"path": "4_Archives/x/key.txt", "leaf": "inv", "kind": "record", "scope": "a"}
    pred = bakeoff.predict(
        row,
        tmp_path,
        MENU,
        bakeoff.ask_gemini,
        _recording_post(calls),
        "k",
        lambda _p: "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIE",
    )
    assert pred["signal"] == "secret"
    assert calls == []


def test_secret_folder_is_never_sent(bakeoff, tmp_path: Path):
    calls: list[object] = []
    row = {
        "path": "4_Archives/wallet_recovery_phrase/notes.txt",
        "leaf": "inv",
        "kind": "record",
        "scope": "a",
    }
    pred = bakeoff.predict(
        row, tmp_path, MENU, bakeoff.ask_gemini, _recording_post(calls), "k", lambda _p: "hi"
    )
    assert (pred["band"], pred["signal"]) == ("red", "secret")
    assert calls == []


def test_paths_outside_the_para_root_are_refused(bakeoff, tmp_path: Path):
    para = tmp_path / "PARA"
    para.mkdir()
    (tmp_path / "outside.pdf").write_text("x")
    (para / "4_Archives").mkdir()
    (para / "4_Archives/link.pdf").symlink_to(tmp_path / "outside.pdf")
    calls: list[object] = []
    for rel in (
        "../outside.pdf",
        "/etc/hosts",
        "4_Archives/../../outside.pdf",
        "4_Archives/link.pdf",
    ):
        row = {"path": rel, "leaf": "inv", "kind": "record", "scope": "a"}
        pred = bakeoff.predict(
            row, para, MENU, bakeoff.ask_gemini, _recording_post(calls), "k", lambda _p: "x"
        )
        assert (pred["band"], pred["signal"], pred["leaf"]) == ("red", "outside", None), rel
    assert calls == []


def test_empty_answer_is_a_red_row(bakeoff, tmp_path: Path):
    post = FakePost(httpx.Response(200, json={"answers": {"leaf": {"probabilities": {}}}}))
    row = {"path": "4_Archives/x/a.pdf", "leaf": "inv", "kind": "record", "scope": "a"}
    pred = bakeoff.predict(row, tmp_path, MENU, bakeoff.ask_jev, post, "k", lambda _p: "")
    assert (pred["band"], pred["leaf"], pred["error"]) == ("red", None, "empty answer")


def test_answered_row_is_yellow(bakeoff, tmp_path: Path):
    post = FakePost(_chat('{"choices": [{"leaf": "inv", "confidence": 0.8}]}'))
    row = {"path": "4_Archives/x/a.pdf", "leaf": "inv", "kind": "record", "scope": "a"}
    pred = bakeoff.predict(row, tmp_path, MENU, bakeoff.ask_gemini, post, "k", lambda _p: "x")
    assert (pred["band"], pred["leaf"]) == ("yellow", "inv")


def test_unreadable_file_is_still_predicted(bakeoff, tmp_path: Path):
    def unreadable(_path: Path) -> str:
        msg = "online-only file"
        raise PermissionError(msg)

    post = FakePost(_chat('{"choices": [{"leaf": "inv", "confidence": 0.8}]}'))
    row = {"path": "4_Archives/x/a.pdf", "leaf": "inv", "kind": "record", "scope": "a"}
    pred = bakeoff.predict(row, tmp_path, MENU, bakeoff.ask_gemini, post, "k", unreadable)
    assert pred["leaf"] == "inv"
    assert pred["top3"] == ["inv"]
    assert "(no text)" in post.calls[0]["json"]["messages"][1]["content"]


def test_malformed_reply_becomes_error_row(bakeoff, tmp_path: Path):
    post = FakePost(httpx.Response(200, json=["not", "a", "dict"]))
    row = {"path": "4_Archives/x/a.pdf", "leaf": "inv", "kind": "record", "scope": "a"}
    pred = bakeoff.predict(row, tmp_path, MENU, bakeoff.ask_gemini, post, "k", lambda _p: "")
    assert pred["leaf"] is None
    assert pred["band"] == "red"
    assert "error" in pred


def test_rate_limit_is_retried(bakeoff, monkeypatch):
    monkeypatch.setattr(bakeoff.time, "sleep", lambda _seconds: None)
    post = FakePost(
        httpx.Response(429, headers={"Retry-After": "1"}),
        _chat('{"choices": [{"leaf": "inv", "confidence": 0.5}]}'),
    )
    ranked, _cost = bakeoff.ask_gemini(post, "k", MENU, "a.pdf", "")
    assert ranked == [("inv", 0.5)]
    assert len(post.calls) == 2


def test_select_scope(bakeoff):
    golden = [
        {"path": "a.pdf", "leaf": "inv", "kind": "record"},
        {"path": "b.pdf", "leaf": "inv", "kind": "record"},
        {"path": "c.pdf", "leaf": "notes", "kind": "knowledge"},
    ]
    baseline = [{"path": "a.pdf", "band": "green"}, {"path": "b.pdf", "band": "red"}]
    scoped = {row["path"]: row["scope"] for row in bakeoff.select_scope(golden, baseline)}
    assert scoped == {"b.pdf": "a", "c.pdf": "b"}


def test_interrupt_keeps_done_predictions_and_skips_pending(bakeoff, tmp_path: Path):
    calls: list[str] = []

    def run(row: dict) -> dict:
        calls.append(row["path"])
        if row["path"] == "b":
            time.sleep(0.2)  # the main thread collects "a" and waits on "b"
            # Ctrl+C lands on the main thread, blocked on "b" (not on this worker)
            signal.pthread_kill(threading.main_thread().ident, signal.SIGINT)
            time.sleep(0.5)  # the main thread cancels "c" before this worker takes it
        return {"path": row["path"]}

    out = tmp_path / "p.jsonl"
    rows = [{"path": "a"}, {"path": "b"}, {"path": "c"}]
    with pytest.raises(KeyboardInterrupt):
        bakeoff.predict_all(rows, run, 1, out)
    time.sleep(1.0)  # long enough for a worker that was not cancelled to start "c"
    assert [json.loads(line)["path"] for line in out.read_text().splitlines()] == ["a"]
    assert "c" not in calls


def test_parse_choices_rejects_boolean_and_non_finite_confidence(bakeoff):
    booleans = '{"choices": [{"leaf": "inv", "confidence": true}]}'
    assert bakeoff.parse_choices(booleans, MENU) == []
    nan = '{"choices": [{"leaf": "inv", "confidence": NaN}]}'
    assert bakeoff.parse_choices(nan, MENU) == []
    infinite = '{"choices": [{"leaf": "inv", "confidence": Infinity}]}'
    assert bakeoff.parse_choices(infinite, MENU) == []


def test_failed_reply_keeps_its_cost(bakeoff, tmp_path: Path):
    post = FakePost(httpx.Response(200, json={"usage": {"cost": 0.004}}))  # no choices
    row = {"path": "4_Archives/x/a.pdf", "leaf": "inv", "kind": "record", "scope": "a"}
    pred = bakeoff.predict(row, tmp_path, MENU, bakeoff.ask_gemini, post, "k", lambda _p: "x")
    assert pred["cost"] == pytest.approx(0.004)
    assert pred["band"] == "red"
    assert "error" in pred


def test_http_error_keeps_its_cost(bakeoff, tmp_path: Path):
    body = {"usage": {"cost": 0.002}, "error": "bad request"}
    post = FakePost(httpx.Response(400, json=body))
    row = {"path": "4_Archives/x/a.pdf", "leaf": "inv", "kind": "record", "scope": "a"}
    pred = bakeoff.predict(row, tmp_path, MENU, bakeoff.ask_gemini, post, "k", lambda _p: "x")
    assert pred["cost"] == pytest.approx(0.002)
    assert "error" in pred


def test_evidence_preview_is_capped_at_2000_characters(bakeoff):
    assert bakeoff.evidence_text("a.pdf", "x" * 5000).count("x") == 2000


def test_retry_after_is_capped_at_sixty_seconds(bakeoff, monkeypatch):
    delays: list[float] = []
    monkeypatch.setattr(bakeoff.time, "sleep", delays.append)
    post = FakePost(
        httpx.Response(429, headers={"Retry-After": "3600"}),
        _chat('{"choices": [{"leaf": "inv", "confidence": 0.5}]}'),
    )
    bakeoff.ask_gemini(post, "k", MENU, "a.pdf", "")
    assert delays == [60.0]


def test_interrupt_keeps_every_finished_prediction(bakeoff, tmp_path: Path):
    main_thread = threading.main_thread().ident

    def run(row: dict) -> dict:
        if row["path"] == "a":
            time.sleep(0.3)  # the main thread waits on "a"; "b" finishes first
            signal.pthread_kill(main_thread, signal.SIGINT)
            time.sleep(0.5)
        return {"path": row["path"]}

    out = tmp_path / "p.jsonl"
    with pytest.raises(KeyboardInterrupt):
        bakeoff.predict_all([{"path": "a"}, {"path": "b"}], run, 2, out)
    assert [json.loads(line)["path"] for line in out.read_text().splitlines()] == ["b"]


def test_worker_error_cancels_pending_and_keeps_finished(bakeoff, tmp_path: Path):
    calls: list[str] = []

    def run(row: dict) -> dict:
        calls.append(row["path"])
        if row["path"] == "b":
            msg = "boom"
            raise RuntimeError(msg)
        if row["path"] == "c":
            time.sleep(0.5)
        return {"path": row["path"]}

    out = tmp_path / "p.jsonl"
    with pytest.raises(RuntimeError, match="boom"):
        bakeoff.predict_all([{"path": p} for p in "abcd"], run, 1, out)
    time.sleep(1.0)
    assert [json.loads(line)["path"] for line in out.read_text().splitlines()] == ["a"]
    assert "d" not in calls


CONFIG_TREE = Path(__file__).resolve().parents[1] / "examples"
FAKE_KEY = "sk-or-TEST-FAKE-KEY-000"


def _config_dir(tmp_path: Path) -> Path:
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    for name in ("tree.yaml", "rules.yaml", "issuers.yaml"):
        (cfg / name).write_text((CONFIG_TREE / name).read_text(encoding="utf-8"), "utf-8")
    return cfg


def _para_with_invoice(tmp_path: Path) -> Path:
    para = tmp_path / "PARA"
    invoice = para / "4_Archives/5y_factures/Telephonie/facture.txt"
    invoice.parent.mkdir(parents=True)
    invoice.write_text("Facture Swisscom 2024", encoding="utf-8")
    return para


def _golden_and_baseline(cfg: Path) -> None:
    row = {"path": "4_Archives/5y_factures/Telephonie/facture.txt", "leaf": "telecom_invoices"}
    golden = {**row, "kind": "record"}
    baseline = {**row, "leaf": None, "band": "red", "signal": "rules", "confidence": 0.0}
    (cfg / "golden.jsonl").write_text(f"\n{json.dumps(golden)}\n   \n", encoding="utf-8")
    (cfg / "pred_baseline.jsonl").write_text(f"{json.dumps(baseline)}\n\n", encoding="utf-8")


@pytest.fixture
def fake_openrouter(monkeypatch):
    fake = FakePost(_chat('{"choices": [{"leaf": "telecom_invoices", "confidence": 0.9}]}'))
    monkeypatch.setattr(httpx, "post", fake)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    return fake


def test_main_writes_rows_without_the_key(bakeoff, tmp_path: Path, monkeypatch, fake_openrouter):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    cfg, para = _config_dir(tmp_path), _para_with_invoice(tmp_path)
    _golden_and_baseline(cfg)
    assert (
        bakeoff.main(["--candidate", "gemini", "--para-root", str(para), "--config-dir", str(cfg)])
        == 0
    )
    rows = (cfg / "pred_gemini.jsonl").read_text(encoding="utf-8")
    assert FAKE_KEY not in rows
    assert json.loads(rows.splitlines()[0])["leaf"] == "telecom_invoices"
    assert fake_openrouter.calls[0]["headers"]["Authorization"] == f"Bearer {FAKE_KEY}"


def test_key_falls_back_to_the_config_dir_env_file(
    bakeoff, tmp_path: Path, monkeypatch, fake_openrouter
):
    cfg, para = _config_dir(tmp_path), _para_with_invoice(tmp_path)
    _golden_and_baseline(cfg)
    (cfg / ".env").write_text(f"PARA_FILES_LLM_API_KEY={FAKE_KEY}\n", encoding="utf-8")
    assert (
        bakeoff.main(["--candidate", "gemini", "--para-root", str(para), "--config-dir", str(cfg)])
        == 0
    )
    assert fake_openrouter.calls[0]["headers"]["Authorization"] == f"Bearer {FAKE_KEY}"


def test_baseline_option_and_blank_lines(bakeoff, tmp_path: Path, monkeypatch, fake_openrouter):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    cfg, para = _config_dir(tmp_path), _para_with_invoice(tmp_path)
    _golden_and_baseline(cfg)
    alt = tmp_path / "alt_baseline.jsonl"
    alt.write_text('{"path": "4_Archives/5y_factures/Telephonie/facture.txt", "band": "green"}\n\n')
    argv = ["--candidate", "gemini", "--para-root", str(para), "--config-dir", str(cfg)]
    assert bakeoff.main([*argv, "--baseline", str(alt)]) == 0
    assert (cfg / "pred_gemini.jsonl").read_text(encoding="utf-8") == ""  # green: out of scope


def test_secret_subfolder_is_dropped_from_the_menu_sent(bakeoff):
    tree = SimpleNamespace(
        leaves={
            "inv": SimpleNamespace(
                path="4_Archives/inv",
                describe="Invoices (contains: wallet_passwords, Telephonie)",
            )
        }
    )
    post = FakePost(_chat('{"choices": [{"leaf": "inv", "confidence": 0.8}]}'))
    bakeoff.ask_gemini(post, "k", bakeoff.leaf_menu(tree), "a.pdf", "text")
    sent = json.dumps(post.calls[0]["json"], ensure_ascii=False)
    assert "wallet_passwords" not in sent
    assert "Telephonie" in sent


def test_secret_named_leaf_is_left_out_of_the_request(bakeoff):
    tree = SimpleNamespace(
        leaves={
            "archives_wallet_passwords": SimpleNamespace(
                path="4_Archives/wallet_passwords", describe="Wallet passwords"
            ),
            "notes": SimpleNamespace(path="3_Resources/notes", describe="Notes"),
        }
    )
    post = FakePost(_chat('{"choices": [{"leaf": "notes", "confidence": 0.8}]}'))
    bakeoff.ask_gemini(post, "k", bakeoff.leaf_menu(tree), "a.pdf", "text")
    body = post.calls[0]["json"]
    sent = json.dumps(body, ensure_ascii=False)
    enum = body["response_format"]["json_schema"]["schema"]["properties"]["choices"]["items"]
    assert enum["properties"]["leaf"]["enum"] == ["notes"]
    assert "archives_wallet_passwords" not in sent
    assert "wallet" not in sent.lower()
    assert "Notes" in sent


@pytest.mark.parametrize("leaf", [["inv"], {"leaf": "inv"}], ids=["list", "dict"])
def test_unhashable_leaf_raises_the_reply_error(bakeoff, leaf):
    content = json.dumps({"choices": [{"leaf": leaf, "confidence": 0.8}]})
    with pytest.raises(bakeoff.ReplyError):
        bakeoff.parse_choices(content, MENU)


@pytest.mark.parametrize("leaf", [["inv"], {"leaf": "inv"}], ids=["list", "dict"])
def test_unhashable_leaf_keeps_the_reply_cost(bakeoff, tmp_path: Path, leaf):
    content = json.dumps({"choices": [{"leaf": leaf, "confidence": 0.8}]})
    reply = {"choices": [{"message": {"content": content}}], "usage": {"cost": 0.002}}
    post = FakePost(httpx.Response(200, json=reply))
    row = {"path": "4_Archives/x/a.pdf", "leaf": "inv", "kind": "record", "scope": "a"}
    pred = bakeoff.predict(row, tmp_path, MENU, bakeoff.ask_gemini, post, "k", lambda _p: "x")
    assert pred["cost"] == pytest.approx(0.002)
    assert pred["leaf"] is None
    assert "malformed" in pred["error"]


@pytest.mark.parametrize(
    "content",
    [
        '{"choices": "inv"}',
        '{"choices": ["inv"]}',
        '{"choices": [{"leaf": "inv", "confidence": ' + "9" * 400 + "}]}",
    ],
    ids=["non-list-choices", "non-dict-item", "integer-overflow"],
)
def test_malformed_choices_raise_the_reply_error(bakeoff, content):
    with pytest.raises(bakeoff.ReplyError):
        bakeoff.parse_choices(content, MENU)


def test_malformed_choices_keep_the_reply_cost(bakeoff, tmp_path: Path):
    reply = {"choices": [{"message": {"content": '{"choices": "inv"}'}}], "usage": {"cost": 0.002}}
    post = FakePost(httpx.Response(200, json=reply))
    row = {"path": "4_Archives/x/a.pdf", "leaf": "inv", "kind": "record", "scope": "a"}
    pred = bakeoff.predict(row, tmp_path, MENU, bakeoff.ask_gemini, post, "k", lambda _p: "x")
    assert pred["cost"] == pytest.approx(0.002)
    assert pred["leaf"] is None
    assert "malformed" in pred["error"]


def test_key_order_is_env_then_cwd_dotenv_then_config_dotenv(bakeoff, tmp_path: Path, monkeypatch):
    fake_openrouter = FakePost(*(_chat('{"choices": []}') for _ in range(3)))
    monkeypatch.setattr(httpx, "post", fake_openrouter)
    cfg, para = _config_dir(tmp_path), _para_with_invoice(tmp_path)
    _golden_and_baseline(cfg)
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    (work / ".env").write_text("PARA_FILES_LLM_API_KEY=sk-or-TEST-CWD-KEY\n", encoding="utf-8")
    (cfg / ".env").write_text("PARA_FILES_LLM_API_KEY=sk-or-TEST-CONFIG-KEY\n", encoding="utf-8")
    argv = ["--candidate", "gemini", "--para-root", str(para), "--config-dir", str(cfg)]
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("PARA_FILES_LLM_API_KEY", FAKE_KEY)
    assert bakeoff.main(argv) == 0
    assert fake_openrouter.calls[-1]["headers"]["Authorization"] == f"Bearer {FAKE_KEY}"
    monkeypatch.delenv("PARA_FILES_LLM_API_KEY")
    assert bakeoff.main(argv) == 0
    assert fake_openrouter.calls[-1]["headers"]["Authorization"] == "Bearer sk-or-TEST-CWD-KEY"
    (work / ".env").unlink()
    assert bakeoff.main(argv) == 0
    assert fake_openrouter.calls[-1]["headers"]["Authorization"] == "Bearer sk-or-TEST-CONFIG-KEY"
