"""The cascade: first signal wins; bands, caps, calibration and targets."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from para_files.core import decide
from para_files.core.cache import Cache
from para_files.core.decide import Context, Verdict, classify, target_dir
from para_files.core.evidence import Evidence
from para_files.core.fallback import FallbackChoice
from para_files.core.tree import IssuersFile, RulesFile, Tree, TreeConfig
from para_files.utils.isbn_lookup import BookInfo
from tests.core_helpers import make_config, make_settings


class FakeFallback:
    def __init__(self, leaf="archives_5y_factures", confidence=0.95):
        self.leaf, self.confidence, self.calls = leaf, confidence, []

    def decide(self, evidence, tree, hints=()):
        self.calls.append(evidence.name)
        if self.leaf is None:
            return None
        return FallbackChoice(self.leaf, self.confidence, "m1", ((self.leaf, self.confidence),))


def make_ctx(tmp_path, *, fallback=None, confirmed=None):
    settings = make_settings(tmp_path)
    return Context(
        config=make_config(),
        settings=settings,
        cache=Cache(settings.cache_path),
        fingerprint="fp",
        confirmed=confirmed or {},
        fallback=fallback,
        lookup=lambda _isbn: None,
    )


def inbox_file(ctx, name, text="x"):
    path = ctx.settings.para_root / "0_Inbox" / name
    path.write_text(text)
    return path


def test_rule_is_green_with_year(tmp_path):
    ctx = make_ctx(tmp_path)
    d = classify(inbox_file(ctx, "Payslip_2025-12-22.txt"), ctx)
    assert (d.leaf_id, d.signal, d.band, d.kind) == (
        "archives_10y_travail",
        "rules",
        "green",
        "record",
    )
    assert d.target_dir == "4_Archives/10y_travail/2025"


def test_unfillable_subkey_goes_to_leaf_root(tmp_path):
    ctx = make_ctx(tmp_path)
    assert classify(inbox_file(ctx, "Payslip.txt"), ctx).target_dir == "4_Archives/10y_travail"


def test_knowledge_is_capped_at_yellow(tmp_path):
    ctx = make_ctx(tmp_path)
    d = classify(inbox_file(ctx, "notes.md"), ctx)
    assert (d.leaf_id, d.band) == ("resources_it", "yellow")


def test_library_by_rule_is_capped_at_yellow(tmp_path):
    ctx = make_ctx(tmp_path)
    d = classify(inbox_file(ctx, "storage_whitepaper.txt"), ctx)
    assert (d.leaf_id, d.band) == ("resources_docs", "yellow")


def test_issuer_is_yellow_before_calibration(tmp_path):
    ctx = make_ctx(tmp_path)
    d = classify(inbox_file(ctx, "2026-01-23_acmecard_facture.txt", "AcmeCard"), ctx)
    assert (d.leaf_id, d.signal, d.band) == ("archives_10y_banques", "hint", "yellow")
    assert d.target_dir == "4_Archives/10y_banques/acmecard/2026"
    assert d.confidence == 0.95


def test_hint_stays_yellow_after_calibration(tmp_path):
    ctx = make_ctx(tmp_path, confirmed={"record": 100})
    d = classify(inbox_file(ctx, "2026-01-23_acmecard_facture.txt", "AcmeCard"), ctx)
    assert d.band == "yellow"


def test_issuer_without_keyword_stays_yellow_after_calibration(tmp_path):
    ctx = make_ctx(tmp_path, confirmed={"record": 100})
    d = classify(inbox_file(ctx, "abc_2025.txt", "hello"), ctx)
    assert (d.signal, d.confidence, d.band) == ("hint", 0.8, "yellow")


def test_fallback_bands(tmp_path):
    ctx = make_ctx(tmp_path, fallback=FakeFallback(confidence=0.95))
    assert classify(inbox_file(ctx, "random.txt", "hello"), ctx).band == "yellow"
    ctx.confirmed = {"record": 100}
    assert classify(inbox_file(ctx, "random2.txt", "hello 2"), ctx).band == "green"
    ctx.fallback = FakeFallback(confidence=0.1)
    assert classify(inbox_file(ctx, "random3.txt", "hello 3"), ctx).band == "red"


def test_secret_is_red_and_never_reaches_a_signal(tmp_path):
    fallback = FakeFallback()
    ctx = make_ctx(tmp_path, fallback=fallback)
    d = classify(inbox_file(ctx, "Payslip_passwords.txt"), ctx)
    assert (d.band, d.signal, d.leaf_id) == ("red", "secret", None)
    assert fallback.calls == []


def test_failing_signal_hands_over(tmp_path, monkeypatch):
    def boom(*_args):
        msg = "broken rules"
        raise RuntimeError(msg)

    monkeypatch.setattr(decide, "match_rule", boom)
    ctx = make_ctx(tmp_path, fallback=FakeFallback())
    d = classify(inbox_file(ctx, "Payslip_2025.txt"), ctx)
    assert d.signal == "fallback"


def test_keyboard_interrupt_propagates(tmp_path, monkeypatch):
    def stop(*_args):
        raise KeyboardInterrupt

    monkeypatch.setattr(decide, "match_rule", stop)
    ctx = make_ctx(tmp_path)
    with pytest.raises(KeyboardInterrupt):
        classify(inbox_file(ctx, "a.txt"), ctx)


def test_verdict_is_cached_but_band_is_recomputed(tmp_path):
    fallback = FakeFallback(confidence=0.95)
    ctx = make_ctx(tmp_path, fallback=fallback)
    path = inbox_file(ctx, "random.txt", "same")
    assert classify(path, ctx).band == "yellow"
    ctx.confirmed = {"record": 100}
    assert classify(path, ctx).band == "green"
    assert fallback.calls == ["random.txt"]


def test_no_leaf_is_red_and_not_cached(tmp_path):
    fallback = FakeFallback(leaf=None)
    ctx = make_ctx(tmp_path, fallback=fallback)
    path = inbox_file(ctx, "random.txt", "same")
    assert classify(path, ctx).band == "red"
    assert classify(path, ctx).band == "red"
    assert fallback.calls == ["random.txt", "random.txt"]


def test_target_from_exif_date():
    leaf = make_config().tree.leaves["archives_photos"]
    evidence = Evidence(
        path=Path("/x/IMG_1.jpg"),
        name="IMG_1.jpg",
        ext=".jpg",
        size=1,
        mtime=0.0,
        sha256="s",
        exif_date=datetime(2024, 5, 1),
    )
    verdict = Verdict("archives_photos", "rules", 1.0, "rule")
    assert target_dir(leaf, evidence, verdict) == "4_Archives/photos/2024/05"


def test_same_bytes_under_another_name_do_not_share_a_verdict(tmp_path):
    fallback = FakeFallback(confidence=0.95)
    ctx = make_ctx(tmp_path, fallback=fallback)
    payslip = inbox_file(ctx, "Payslip_2025.txt", "same")
    random_file = inbox_file(ctx, "random.txt", "same")
    assert classify(payslip, ctx).signal == "rules"
    assert classify(random_file, ctx).signal == "fallback"
    assert fallback.calls == ["random.txt"]


def _book_ctx(tmp_path, monkeypatch, *, ext, isbns=()):
    def fake_extract(path, **_kwargs):
        return Evidence(
            path=path, name=path.name, ext=ext, size=1, mtime=0.0, sha256="s", isbns=isbns
        )

    monkeypatch.setattr(decide, "extract", fake_extract)
    ctx = make_ctx(tmp_path)
    ctx.lookup = lambda _isbn: BookInfo(
        title="Python Cookbook", authors=["David Beazley"], publish_date="2013"
    )
    return ctx


def test_book_with_a_coherent_isbn_is_green(tmp_path, monkeypatch):
    ctx = _book_ctx(tmp_path, monkeypatch, ext=".pdf", isbns=("9781449340377",))
    d = classify(inbox_file(ctx, "Python Cookbook.pdf"), ctx)
    assert (d.leaf_id, d.signal, d.band) == ("resources_livres", "books", "green")
    assert d.evidence_summary == "ISBN 9781449340377"


def test_book_without_an_isbn_is_yellow(tmp_path, monkeypatch):
    ctx = _book_ctx(tmp_path, monkeypatch, ext=".epub")
    d = classify(inbox_file(ctx, "Python Cookbook.epub"), ctx)
    assert (d.leaf_id, d.signal, d.band) == ("resources_livres", "hint", "yellow")


def test_library_hint_through_an_issuer_stays_yellow(tmp_path):
    tree = Tree.model_validate(
        {
            "leaves": {
                "resources_vendor": {
                    "kind": "library",
                    "path": "3_Resources/docs",
                    "describe": "Vendor documentation",
                    "keywords": ["manual"],
                }
            }
        }
    )
    issuers = IssuersFile.model_validate(
        {"issuers": {"acmecorp": {"patterns": ["AcmeCorp"], "leaves": ["resources_vendor"]}}}
    )
    ctx = make_ctx(tmp_path, confirmed={"library": 100})
    ctx.config = TreeConfig(tree=tree, rules=RulesFile(), issuers=issuers)
    d = classify(inbox_file(ctx, "AcmeCorp manual.txt", "hello"), ctx)
    assert (d.leaf_id, d.signal, d.kind) == ("resources_vendor", "hint", "library")
    assert d.confidence == 0.95
    assert d.band == "yellow"


def test_thema_fills_the_library_subkey():
    leaf = make_config().tree.leaves["resources_livres"]
    evidence = Evidence(
        path=Path("/x/book.pdf"), name="book.pdf", ext=".pdf", size=1, mtime=0.0, sha256="s"
    )
    verdict = Verdict(
        "resources_livres", "books", 1.0, "ISBN", thema="U_Informatique/UB_Programmation"
    )
    assert target_dir(leaf, evidence, verdict) == (
        "3_Resources/livres/U_Informatique/UB_Programmation"
    )


def test_year_only_name_on_a_year_month_leaf_goes_to_the_leaf_root():
    leaf = make_config().tree.leaves["archives_photos"]
    evidence = Evidence(
        path=Path("/x/holiday_2024.jpg"),
        name="holiday_2024.jpg",
        ext=".jpg",
        size=1,
        mtime=0.0,
        sha256="s",
    )
    verdict = Verdict("archives_photos", "rules", 1.0, "rule")
    assert target_dir(leaf, evidence, verdict) == "4_Archives/photos"


class HintedFallback:
    """Records the hints it was given; answers a fixed leaf with an 'about'."""

    def __init__(self, leaf="archives_10y_banques", confidence=0.7):
        self.leaf, self.confidence, self.hints = leaf, confidence, []

    def decide(self, evidence, tree, hints=()):
        self.hints.append(list(hints))
        return FallbackChoice(
            self.leaf,
            self.confidence,
            "m1",
            ((self.leaf, self.confidence), ("archives_5y_factures", 0.2)),
            "a card statement",
        )


def with_rules(ctx, *extra):
    base = ctx.config
    existing = [rule.model_dump() for rule in base.rules.rules]
    rules = RulesFile.model_validate({"rules": [*extra, *existing]})
    ctx.config = TreeConfig(tree=base.tree, rules=rules, issuers=base.issuers)
    return ctx


def test_pinned_rule_is_green_and_the_model_is_not_asked(tmp_path):
    model = HintedFallback()
    ctx = make_ctx(tmp_path, fallback=model)
    d = classify(inbox_file(ctx, "Payslip_2025-12-22.txt"), ctx)
    assert (d.leaf_id, d.signal, d.band) == ("archives_10y_travail", "rules", "green")
    assert model.hints == []


def test_unpinned_rule_and_issuer_are_hints_and_the_issuer_fills_the_subkey(tmp_path):
    model = HintedFallback()
    ctx = with_rules(
        make_ctx(tmp_path, fallback=model),
        {"name": "broad", "leaf": "resources_docs", "globs": ["*card*"]},
    )
    d = classify(inbox_file(ctx, "acmecard_2026.txt", "AcmeCard statement"), ctx)
    assert (d.leaf_id, d.signal, d.band) == ("archives_10y_banques", "fallback", "yellow")
    assert d.target_dir == "4_Archives/10y_banques/acmecard/2026"
    assert d.about == "a card statement"
    assert d.ranked == (("archives_10y_banques", 0.7), ("archives_5y_factures", 0.2))
    sources = [hint.source for hint in model.hints[0]]
    assert sources[0].startswith("rule 'broad'")
    assert any(source.startswith("issuer 'acmecard'") for source in sources)


def test_model_off_gives_a_yellow_hint_even_when_calibrated(tmp_path):
    ctx = make_ctx(tmp_path, confirmed={"record": 1000, "library": 1000})
    d = classify(inbox_file(ctx, "statement.txt", "AcmeCard statement"), ctx)
    assert (d.leaf_id, d.signal, d.band) == ("archives_10y_banques", "hint", "yellow")
    assert "(model off)" in d.evidence_summary


def test_hint_verdicts_are_not_cached_but_model_verdicts_are(tmp_path):
    model = HintedFallback()
    ctx = make_ctx(tmp_path, fallback=model)
    path = inbox_file(ctx, "statement.txt", "AcmeCard statement")
    classify(path, ctx)
    classify(path, ctx)
    assert len(model.hints) == 1
    ctx.fallback = None
    other = inbox_file(ctx, "other.txt", "AcmeCard other")
    classify(other, ctx)
    assert ctx.cache.get_verdict(classify(other, ctx).sha256, "fp:other.txt") is None


def test_isbn_beats_a_pinned_rule(tmp_path):
    info = BookInfo(isbn_13="9780000000002", title="Payslip Handbook", authors=["A. Writer"])
    ctx = make_ctx(tmp_path)
    ctx.lookup = lambda _isbn: info
    path = inbox_file(ctx, "Payslip Handbook.pdf")
    evidence = Evidence(
        path=path,
        name=path.name,
        ext=".pdf",
        size=1,
        mtime=0.0,
        sha256="1" * 64,
        isbns=("9780000000002",),
    )
    verdict, steps = decide.choose(evidence, ctx)
    assert (verdict.signal, verdict.isbn) == ("books", "9780000000002")
    assert steps[0].name == "isbn book"


def test_photo_rule_pins_only_with_an_exif_date(tmp_path):
    ctx = make_ctx(tmp_path)
    base = {
        "path": Path("/x/IMG_1.jpg"),
        "name": "IMG_1.jpg",
        "ext": ".jpg",
        "size": 1,
        "mtime": 0.0,
        "sha256": "2" * 64,
    }
    with_date, _ = decide.choose(Evidence(**base, exif_date=datetime(2024, 5, 1)), ctx)
    without, _ = decide.choose(Evidence(**base), ctx)
    assert (with_date.signal, with_date.leaf_id) == ("rules", "archives_photos")
    assert (without.signal, without.leaf_id) == ("hint", "archives_photos")


def test_library_model_verdict_needs_an_issuer_to_be_green(tmp_path):
    model = HintedFallback(leaf="resources_docs", confidence=0.95)
    ctx = make_ctx(tmp_path, fallback=model, confirmed={"library": 1000})
    d = classify(inbox_file(ctx, "guide.txt", "storage guide"), ctx)
    assert (d.signal, d.band) == ("fallback", "yellow")


def test_secret_is_never_sent(tmp_path):
    model = HintedFallback()
    ctx = make_ctx(tmp_path, fallback=model)
    d = classify(inbox_file(ctx, "notes.txt", "vpn\npassword: hunter22\n"), ctx)
    assert (d.signal, d.band) == ("secret", "red")
    assert model.hints == []
