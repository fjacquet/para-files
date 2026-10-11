"""Signal 4: litellm to OpenRouter with ZDR on every request; secrets never sent."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from loguru import logger

from para_files.circuit_breaker import OllamaCircuitBreaker
from para_files.core.evidence import Evidence
from para_files.core.fallback import (
    FallbackChoice,
    OpenRouterFallback,
    leaf_menu,
    make_fallback,
)
from para_files.core.tree import Tree
from tests.core_helpers import make_config, make_settings


KEY = "sk-test-key"


def reply(choices):
    content = json.dumps({"choices": choices})
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeComplete:
    """Stands in for litellm.completion: records calls, returns or raises in turn."""

    def __init__(self, *outcomes):
        self.outcomes, self.calls = list(outcomes), []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def ev(name="scan.pdf", preview="Monthly statement", secret=None, listing=()):
    return Evidence(
        path=Path("/private/somewhere") / name,
        name=name,
        ext=".pdf",
        size=1,
        mtime=0.0,
        sha256="s",
        secret=secret,
        text_preview=preview,
        archive_listing=listing,
    )


def test_request_carries_zdr_and_low_reasoning():
    complete = FakeComplete(reply([{"leaf": "archives_10y_banques", "confidence": 0.8}]))
    fallback = OpenRouterFallback(KEY, ["google/m1", "anthropic/m2"], complete=complete)
    choice = fallback.decide(ev(), make_config().tree)
    assert choice == FallbackChoice(
        "archives_10y_banques", 0.8, "google/m1", (("archives_10y_banques", 0.8),)
    )
    call = complete.calls[0]
    assert call["model"] == "openrouter/google/m1"
    assert call["extra_body"] == {
        "provider": {"zdr": True, "data_collection": "deny"},
        "reasoning": {"effort": "low"},
    }
    assert call["api_key"] == KEY
    assert call["temperature"] == 0
    sent = json.dumps(call["messages"])
    assert KEY not in sent
    assert "/private/somewhere" not in sent
    schema = call["response_format"]["json_schema"]["schema"]
    leaf = schema["properties"]["choices"]["items"]["properties"]["leaf"]
    assert set(leaf["enum"]) == set(make_config().tree.leaves)


def test_secret_evidence_is_never_sent():
    complete = FakeComplete()
    fallback = OpenRouterFallback(KEY, ["m1"], complete=complete)
    secret_evidence = ev(secret="name")  # noqa: S106 - a reason, not a password
    assert fallback.decide(secret_evidence, make_config().tree) is None
    assert complete.calls == []


def test_backup_model_after_an_error():
    complete = FakeComplete(
        RuntimeError("HTTP 500"),
        reply([{"leaf": "archives_5y_factures", "confidence": 0.6}]),
    )
    choice = OpenRouterFallback(KEY, ["m1", "m2"], complete=complete).decide(
        ev(), make_config().tree
    )
    assert choice.model == "m2"
    assert [call["model"] for call in complete.calls] == ["openrouter/m1", "openrouter/m2"]


def test_all_models_fail_records_a_breaker_failure():
    breaker = OllamaCircuitBreaker(threshold=1)
    complete = FakeComplete(RuntimeError("HTTP 500"), RuntimeError("HTTP 502"))
    fallback = OpenRouterFallback(KEY, ["m1", "m2"], complete=complete, breaker=breaker)
    assert fallback.decide(ev(), make_config().tree) is None
    assert breaker.is_open
    assert fallback.decide(ev(), make_config().tree) is None
    assert len(complete.calls) == 2


def test_malformed_reply_moves_on():
    complete = FakeComplete(
        SimpleNamespace(choices=[]),
        reply([{"leaf": "resources_docs", "confidence": 0.5}]),
    )
    choice = OpenRouterFallback(KEY, ["m1", "m2"], complete=complete).decide(
        ev(), make_config().tree
    )
    assert choice.model == "m2"


def test_unknown_or_malformed_choices_are_dropped():
    complete = FakeComplete(
        reply(
            [
                {"leaf": "nope", "confidence": 0.9},
                {"leaf": ["x"], "confidence": 0.9},
                {"leaf": "resources_it", "confidence": True},
                {"leaf": "archives_photos", "confidence": 1e400},
                {"leaf": "resources_docs", "confidence": 1.7},
            ]
        )
    )
    choice = OpenRouterFallback(KEY, ["m1"], complete=complete).decide(ev(), make_config().tree)
    assert choice == FallbackChoice("resources_docs", 1.0, "m1", (("resources_docs", 1.0),))


def test_empty_reply_from_primary_moves_on_to_backup():
    complete = FakeComplete(
        reply([]),
        reply([{"leaf": "resources_docs", "confidence": 0.4}]),
    )
    choice = OpenRouterFallback(KEY, ["m1", "m2"], complete=complete).decide(
        ev(), make_config().tree
    )
    assert choice.model == "m2"
    assert [call["model"] for call in complete.calls] == ["openrouter/m1", "openrouter/m2"]


def test_empty_replies_from_all_models_give_none_and_a_breaker_failure():
    breaker = OllamaCircuitBreaker(threshold=1)
    complete = FakeComplete(reply([]), reply([]))
    fallback = OpenRouterFallback(KEY, ["m1", "m2"], complete=complete, breaker=breaker)
    assert fallback.decide(ev(), make_config().tree) is None
    assert breaker.is_open


def test_secret_leaf_never_reaches_the_model():
    tree = Tree.model_validate(
        {
            "leaves": {
                "resources_docs": {
                    "kind": "library",
                    "path": "3_Resources/docs",
                    "describe": "Vendor documentation",
                },
                "areas_passwords": {
                    "kind": "knowledge",
                    "path": "2_Areas/passwords",
                    "describe": "Stored logins",
                },
            }
        }
    )
    complete = FakeComplete(reply([{"leaf": "resources_docs", "confidence": 0.7}]))
    OpenRouterFallback(KEY, ["m1"], complete=complete).decide(ev(), tree)
    call = complete.calls[0]
    schema = call["response_format"]["json_schema"]["schema"]
    leaf = schema["properties"]["choices"]["items"]["properties"]["leaf"]
    assert "areas_passwords" not in leaf["enum"]
    assert leaf["enum"] == ["resources_docs"]
    assert "areas_passwords" not in call["messages"][1]["content"]


def test_archive_entries_are_sent():
    complete = FakeComplete(reply([{"leaf": "resources_docs", "confidence": 0.5}]))
    fallback = OpenRouterFallback(KEY, ["m1"], complete=complete)
    fallback.decide(ev(listing=("guide/readme.txt",)), make_config().tree)
    assert "guide/readme.txt" in complete.calls[0]["messages"][1]["content"]


def test_menu_drops_secret_leaves_and_parts():
    tree = Tree.model_validate(
        {
            "leaves": {
                "areas_it": {
                    "kind": "knowledge",
                    "path": "2_Areas/IT",
                    "describe": "IT (contains: credentials, scripts)",
                },
                "areas_passwords": {
                    "kind": "knowledge",
                    "path": "2_Areas/passwords",
                    "describe": "p",
                },
            }
        }
    )
    assert leaf_menu(tree) == {"areas_it": "IT (contains: scripts)"}


def test_make_fallback(tmp_path):
    assert make_fallback(make_settings(tmp_path)) is None
    assert make_fallback(make_settings(tmp_path, fallback_enabled=True)) is None
    settings = make_settings(tmp_path, fallback_enabled=True, openrouter_api_key=KEY)
    assert isinstance(make_fallback(settings), OpenRouterFallback)


def test_leaf_keywords_are_listed_in_the_menu():
    complete = FakeComplete(reply([{"leaf": "archives_10y_travail", "confidence": 0.9}]))
    OpenRouterFallback(KEY, ["m1"], complete=complete).decide(ev(), make_config().tree)
    user = complete.calls[0]["messages"][1]["content"]
    line = "- archives_10y_travail: Payslips and employment records [keywords: salaire, payslip]"
    assert line in user
    assert "- resources_it: IT notes\n" in user


def test_secret_named_keyword_is_never_listed():
    tree = Tree.model_validate(
        {
            "leaves": {
                "resources_docs": {
                    "kind": "library",
                    "path": "3_Resources/docs",
                    "describe": "Vendor documentation",
                    "keywords": ["manual", "api_key", "password reset"],
                },
                "areas_notes": {
                    "kind": "knowledge",
                    "path": "2_Areas/notes",
                    "describe": "Notes",
                    "keywords": ["token"],
                },
            }
        }
    )
    assert leaf_menu(tree) == {
        "resources_docs": "Vendor documentation [keywords: manual]",
        "areas_notes": "Notes",
    }
    complete = FakeComplete(reply([{"leaf": "resources_docs", "confidence": 0.7}]))
    OpenRouterFallback(KEY, ["m1"], complete=complete).decide(ev(), tree)
    sent = json.dumps(complete.calls[0]["messages"])
    assert "api_key" not in sent
    assert "password reset" not in sent
    assert "token" not in sent


def test_logged_errors_never_carry_the_key():
    messages_seen: list[str] = []
    sink_id = logger.add(lambda message: messages_seen.append(str(message)), level="WARNING")
    try:
        complete = FakeComplete(RuntimeError("provider rejected the request"), reply([]))
        fallback = OpenRouterFallback(KEY, ["m1", "m2"], complete=complete)
        fallback.decide(ev(), make_config().tree)
    finally:
        logger.remove(sink_id)
    assert any("fallback m1 failed" in text for text in messages_seen)
    assert all(KEY not in text for text in messages_seen)
