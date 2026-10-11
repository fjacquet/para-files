"""Signal 4: litellm to OpenRouter with ZDR on every request; secrets never sent."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from loguru import logger

from para_files.core import fallback
from para_files.core.breaker import CircuitBreaker
from para_files.core.evidence import Evidence
from para_files.core.fallback import (
    FallbackChoice,
    Hint,
    OpenRouterFallback,
    evidence_text,
    leaf_menu,
    make_fallback,
    messages,
    parse_reply,
)
from para_files.core.tree import Tree
from tests.core_helpers import make_config, make_settings


KEY = "sk-test-key"


def reply_content(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def reply(choices):
    return reply_content(json.dumps({"choices": choices}))


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


def ev(name="scan.pdf", preview="Monthly statement", secret=None, listing=(), **extra):
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
        **extra,
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
    breaker = CircuitBreaker(threshold=1)
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
    breaker = CircuitBreaker(threshold=1)
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
    assert leaf_menu(tree) == {"areas_it": "IT (contains: scripts) (2_Areas/IT)"}


def test_make_fallback(tmp_path):
    assert make_fallback(make_settings(tmp_path)) is None
    assert make_fallback(make_settings(tmp_path, fallback_enabled=True)) is None
    settings = make_settings(tmp_path, fallback_enabled=True, openrouter_api_key=KEY)
    assert isinstance(make_fallback(settings), OpenRouterFallback)


def test_leaf_keywords_are_listed_in_the_menu():
    complete = FakeComplete(reply([{"leaf": "archives_10y_travail", "confidence": 0.9}]))
    OpenRouterFallback(KEY, ["m1"], complete=complete).decide(ev(), make_config().tree)
    user = complete.calls[0]["messages"][1]["content"]
    line = (
        "- archives_10y_travail: Payslips and employment records [keywords: salaire, payslip] "
        "(4_Archives/10y_travail)"
    )
    assert line in user
    assert "- resources_it: IT notes (3_Resources/IT)\n" in user


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
        "resources_docs": "Vendor documentation [keywords: manual] (3_Resources/docs)",
        "areas_notes": "Notes (2_Areas/notes)",
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
    assert any("model m1 failed" in text for text in messages_seen)
    assert all(KEY not in text for text in messages_seen)


def test_litellm_debug_info_is_suppressed(monkeypatch):
    import sys
    import types

    from para_files.core import fallback

    fake = types.SimpleNamespace(suppress_debug_info=False, completion=lambda **_kw: "reply")
    monkeypatch.setitem(sys.modules, "litellm", fake)
    assert fallback.litellm_complete(model="m") == "reply"
    assert fake.suppress_debug_info is True


def test_prompt_has_type_metadata_isbn_date_and_the_whole_preview():
    text = evidence_text(
        ev(
            doc_meta={"title": "Storage Guide", "author": "A. Writer", "page_count": "12"},
            isbns=("9780000000001",),
            exif_date=datetime(2025, 3, 4),
            preview="A" * 3000,
        )
    )
    assert "Type: .pdf, 12 pages" in text
    assert "Title: Storage Guide" in text
    assert "Author: A. Writer" in text
    assert "ISBN found: 9780000000001" in text
    assert "Date taken: 2025-03-04" in text
    assert "A" * 3000 in text
    assert "may come from OCR" in text


def test_secret_metadata_and_hints_are_left_out(monkeypatch):
    monkeypatch.setattr(
        fallback, "secret_reason", lambda name, text="": "name" if "SECRET" in name else None
    )
    menu = leaf_menu(make_config().tree)
    hints = [
        Hint("rule 'invoices' (glob '*inv*')", "archives_5y_factures"),
        Hint("rule 'gone'", "no_such_leaf"),
        Hint("SECRET rule", "archives_5y_factures"),
    ]
    user = messages(menu, ev(doc_meta={"title": "SECRET plan"}), hints)[1]["content"]
    assert "rule 'invoices' (glob '*inv*') -> archives_5y_factures" in user
    assert "no_such_leaf" not in user
    assert "SECRET" not in user


def test_menu_shows_each_leaf_path():
    menu = leaf_menu(make_config().tree)
    assert menu["archives_5y_factures"].endswith("(4_Archives/5y_factures)")


def test_parse_reply_reads_about_and_choices():
    menu = leaf_menu(make_config().tree)
    content = (
        '{"about": "  Card   statement  ", '
        '"choices": [{"leaf": "archives_10y_banques", "confidence": 0.8}]}'
    )
    assert parse_reply(content, menu) == ([("archives_10y_banques", 0.8)], "Card statement")


def test_decide_sends_hints_and_returns_about():
    seen = {}

    def complete(**kwargs):
        seen.update(kwargs)
        return reply_content(
            json.dumps(
                {
                    "about": "AcmeCard statement",
                    "choices": [
                        {"leaf": "archives_10y_banques", "confidence": 0.7},
                        {"leaf": "archives_5y_factures", "confidence": 0.2},
                    ],
                }
            )
        )

    model = OpenRouterFallback("key", ["m1"], complete=complete)
    hint = Hint("issuer 'acmecard' (pattern 'AcmeCard')", "archives_10y_banques")
    choice = model.decide(ev(preview="AcmeCard"), make_config().tree, [hint])
    assert choice is not None
    assert (choice.leaf_id, choice.about) == ("archives_10y_banques", "AcmeCard statement")
    assert choice.ranked == (("archives_10y_banques", 0.7), ("archives_5y_factures", 0.2))
    assert "issuer 'acmecard'" in seen["messages"][1]["content"]
    assert seen["extra_body"]["provider"] == {"zdr": True, "data_collection": "deny"}
    schema = seen["response_format"]["json_schema"]["schema"]
    assert schema["required"] == ["about", "choices"]


def test_examples_are_picked_by_shared_words_and_never_secret(monkeypatch):
    from para_files.core.fallback import pick_examples
    from para_files.core.journal import Example

    monkeypatch.setattr(
        fallback, "secret_reason", lambda name, text="": "name" if "SECRET" in name else None
    )
    menu = leaf_menu(make_config().tree)
    examples = [
        Example("holiday_photo.jpg", "archives_photos", None),
        Example("acmecard_statement_2025.pdf", "archives_10y_banques", "resources_docs"),
        Example("SECRET_acmecard.pdf", "archives_10y_banques", None),
        Example("acmecard_gone.pdf", "no_such_leaf", None),
    ]
    picked = pick_examples(examples, "acmecard_statement_2026.pdf", menu, limit=2)
    assert [e.name for e in picked] == ["acmecard_statement_2025.pdf", "holiday_photo.jpg"]
    user = messages(menu, ev(name="acmecard_statement_2026.pdf"), (), picked)[1]["content"]
    assert (
        '"acmecard_statement_2025.pdf" -> archives_10y_banques '
        "(tool had proposed resources_docs)" in user
    )
    assert "SECRET" not in user


def test_examples_with_real_secret_check_and_secret_proposals_stay_out_of_the_prompt():
    from para_files.core.fallback import pick_examples
    from para_files.core.journal import Example

    menu = leaf_menu(make_config().tree)
    examples = [
        Example("passwords.txt", "archives_10y_banques", None),
        Example("acmecard_invoice.pdf", "archives_10y_banques", "no_such_leaf"),
    ]
    picked = pick_examples(examples, "acmecard_bill.pdf", menu)
    assert [e.name for e in picked] == ["acmecard_invoice.pdf"]
    user = messages(menu, ev(name="acmecard_bill.pdf"), (), picked)[1]["content"]
    assert "passwords.txt" not in user
    assert "no_such_leaf" not in user
    assert '- "acmecard_invoice.pdf" -> archives_10y_banques\n' in user
