"""Tests for scripts/bakeoff.py: privacy flags, secrets guard, parsing, scope (no network)."""

from __future__ import annotations

import json
import signal
import threading
import time
from pathlib import Path

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


def _never(*_args, **_kwargs):
    msg = "a secret file must never be sent"
    raise AssertionError(msg)


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
    row = {
        "path": "0_Inbox/wallet_recovery_phrase.txt",
        "leaf": "notes",
        "kind": "knowledge",
        "scope": "b",
    }
    pred = bakeoff.predict(row, tmp_path, MENU, bakeoff.ask_jev, _never, "k", lambda _p: "")
    assert (pred["band"], pred["signal"], pred["leaf"]) == ("red", "secret", None)


def test_secret_content_is_never_sent(bakeoff, tmp_path: Path):
    row = {"path": "4_Archives/x/key.txt", "leaf": "inv", "kind": "record", "scope": "a"}
    pred = bakeoff.predict(
        row,
        tmp_path,
        MENU,
        bakeoff.ask_gemini,
        _never,
        "k",
        lambda _p: "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIE",
    )
    assert pred["signal"] == "secret"


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
