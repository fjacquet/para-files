"""The cascade (spec §4.2, model first): evidence -> verdict -> band -> target directory.

Order: the secret guard; a verified ISBN book; a pinned rule; the model, given the other
rule, book and issuer matches as hints; when the model is off or silent, the first hint
(always yellow). Only model verdicts are cached: everything else is cheap to recompute.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Literal, Protocol

from loguru import logger

from para_files.core.books import BookMatch, Lookup, match_book
from para_files.core.cache import Cache
from para_files.core.evidence import Evidence, extract
from para_files.core.fallback import FallbackChoice, Hint
from para_files.core.issuers import IssuerMatch, match_issuer
from para_files.core.rules import match_rule
from para_files.core.settings import CoreSettings
from para_files.core.tree import Kind, Leaf, Rule, Tree, TreeConfig
from para_files.utils.isbn_lookup import lookup_isbn


Band = Literal["green", "yellow", "red"]
RULE_CONFIDENCE = 1.0
ISSUER_AGREED = 0.95
ISSUER_ALONE = 0.8
DATE_IN_NAME = re.compile(r"(?<!\d)((?:19|20)\d{2})(?:[-_. ]?(0[1-9]|1[0-2]))?(?!\d)")


class Fallback(Protocol):
    """The model signal as the cascade sees it."""

    def decide(
        self, evidence: Evidence, tree: Tree, hints: Sequence[Hint] = ()
    ) -> FallbackChoice | None:
        """Leaf choice for this evidence, or None."""


@dataclass(frozen=True)
class Verdict:
    """What decided; model verdicts are cached by content hash and config fingerprint."""

    leaf_id: str | None
    signal: str
    confidence: float
    summary: str
    isbn: str | None = None
    issuer: str | None = None
    thema: str | None = None
    suggested_name: str | None = None
    ranked: tuple[tuple[str, float], ...] = ()
    about: str | None = None


@dataclass(frozen=True)
class Decision:
    """One file's outcome: leaf, target (relative to the PARA root), band and why."""

    path: Path
    sha256: str
    leaf_id: str | None
    target_dir: str | None
    band: Band
    signal: str
    confidence: float
    evidence_summary: str
    kind: Kind | None = None
    suggested_name: str | None = None
    ranked: tuple[tuple[str, float], ...] = ()
    about: str | None = None
    issuer: str | None = None
    fill: tuple[tuple[str, str | None], ...] = ()


@dataclass(frozen=True)
class Step:
    """One line of `explain`: what a signal said, or why it said nothing."""

    name: str
    verdict: Verdict | None
    note: str | None = None


@dataclass
class Context:
    """Everything classify() needs, built once per run."""

    config: TreeConfig
    settings: CoreSettings
    cache: Cache
    fingerprint: str
    confirmed: Mapping[str, int] = field(default_factory=dict)
    fallback: Fallback | None = None
    lookup: Lookup = lookup_isbn


@dataclass(frozen=True)
class _Hints:
    """The non-deciding matches for one file, in cascade order, and the issuer among them."""

    seen: tuple[tuple[Hint, float], ...]
    issuer: IssuerMatch | None

    @property
    def hints(self) -> tuple[Hint, ...]:
        return tuple(hint for hint, _ in self.seen)

    def sources(self) -> str:
        return "; ".join(hint.source for hint in self.hints)


NO_VERDICT = Verdict(None, "none", 0.0, "no signal decided")


def _safe[T](name: str, evidence: Evidence, call: Callable[[], T | None]) -> T | None:
    """call(); a failing signal is logged and treated as silent."""
    try:
        return call()
    except Exception as exc:  # noqa: BLE001 - KeyboardInterrupt is not an Exception
        logger.warning("signal {} failed on {}: {}", name, evidence.name, exc)
        return None


def pin_decides(rule: Rule, evidence: Evidence) -> bool:
    """A pinned rule decides alone; `pin: exif` only when the file has an EXIF date."""
    return rule.pin is True or (rule.pin == "exif" and evidence.exif_date is not None)


def issuer_for(leaf_id: str, issuer: str | None, config: TreeConfig) -> str | None:
    """The issuer, if leaf_id is one of its leaves (then {issuer} may fill); else None."""
    found = config.issuers.issuers.get(issuer) if issuer else None
    return issuer if found is not None and leaf_id in found.leaves else None


def _isbn_verdict(book: BookMatch | None) -> Verdict | None:
    if book is None or book.isbn is None:
        return None
    return Verdict(
        book.leaf_id,
        "books",
        book.confidence,
        f"ISBN {book.isbn}",
        isbn=book.isbn,
        thema=book.thema,
        suggested_name=book.suggested_name,
    )


def _pinned(evidence: Evidence, ctx: Context) -> Verdict | None:
    rules = [rule for rule in ctx.config.rules.rules if pin_decides(rule, evidence)]
    match = match_rule(evidence.name, rules)
    if match is None:
        return None
    summary = f"pinned rule {match.rule!r} glob {match.glob!r}"
    return Verdict(match.leaf_id, "rules", RULE_CONFIDENCE, summary)


def _hints(evidence: Evidence, ctx: Context, book: BookMatch | None) -> _Hints:
    seen: list[tuple[Hint, float]] = []
    rules = [rule for rule in ctx.config.rules.rules if not pin_decides(rule, evidence)]
    rule = _safe("rules", evidence, lambda: match_rule(evidence.name, rules))
    if rule is not None:
        seen.append((Hint(f"rule {rule.rule!r} (glob {rule.glob!r})", rule.leaf_id), 1.0))
    if book is not None and book.isbn is None:
        seen.append((Hint("book heuristics (no ISBN)", book.leaf_id), book.confidence))
    issuer = _safe(
        "issuers", evidence, lambda: match_issuer(evidence.name, evidence.text_preview, ctx.config)
    )
    if issuer is not None:
        agreed = ", leaf keyword agrees" if issuer.agreed else ""
        source = f"issuer {issuer.issuer!r} (pattern {issuer.pattern!r}{agreed})"
        confidence = ISSUER_AGREED if issuer.agreed else ISSUER_ALONE
        seen.append((Hint(source, issuer.leaf_id), confidence))
    return _Hints(tuple(seen), issuer)


def _model_verdict(choice: FallbackChoice, found: _Hints) -> Verdict:
    ranked = ", ".join(f"{leaf} {p:.2f}" for leaf, p in choice.ranked)
    hints = f"; hints: {found.sources()}" if found.seen else ""
    return Verdict(
        choice.leaf_id,
        "fallback",
        choice.confidence,
        f"{choice.model}: {ranked}{hints}",
        issuer=found.issuer.issuer if found.issuer else None,
        ranked=choice.ranked,
        about=choice.about or None,
    )


def _hint_verdict(found: _Hints, why: str) -> Verdict:
    first, confidence = found.seen[0]
    ranked: list[tuple[str, float]] = []
    for hint, value in found.seen:
        if hint.leaf_id not in {leaf for leaf, _ in ranked}:
            ranked.append((hint.leaf_id, value))
    return Verdict(
        first.leaf_id,
        "hint",
        confidence,
        f"{found.sources()} ({why})",
        issuer=found.issuer.issuer if found.issuer else None,
        ranked=tuple(ranked),
    )


def choose(
    evidence: Evidence, ctx: Context, *, ask_model: bool = True
) -> tuple[Verdict, list[Step]]:
    """The winning verdict and every step that led to it (what `explain` prints)."""
    steps: list[Step] = []
    book = _safe(
        "books", evidence, lambda: match_book(evidence, ctx.config.tree, ctx.cache, ctx.lookup)
    )
    isbn = _isbn_verdict(book)
    steps.append(Step("isbn book", isbn, None if isbn else "no verified ISBN"))
    if isbn is not None:
        return isbn, steps
    pinned = _safe("rules", evidence, lambda: _pinned(evidence, ctx))
    steps.append(Step("pinned rule", pinned, None if pinned else "no pinned rule matches"))
    if pinned is not None:
        return pinned, steps
    found = _hints(evidence, ctx, book)
    steps += [
        Step("hint", Verdict(hint.leaf_id, "hint", value, hint.source))
        for hint, value in found.seen
    ]
    if not found.seen:
        steps.append(Step("hint", None, "no rule, book or issuer matches"))
    fallback = ctx.fallback
    if fallback is None:
        why = "model off"
        steps.append(Step("model", None, "off (no key, or PARA_FILES_FALLBACK_ENABLED=false)"))
    elif not ask_model:
        why = "model not asked"
        steps.append(Step("model", None, "not asked (use --ask-model)"))
    else:
        why = "model did not answer"
        choice = _safe(
            "fallback", evidence, lambda: fallback.decide(evidence, ctx.config.tree, found.hints)
        )
        model = _model_verdict(choice, found) if choice is not None else None
        steps.append(Step("model", model, None if model else "no answer"))
        if model is not None:
            return model, steps
    return (_hint_verdict(found, why) if found.seen else NO_VERDICT), steps


def file_date(evidence: Evidence) -> tuple[str | None, str | None]:
    """(year, month) from EXIF, else from a date in the filename."""
    if evidence.exif_date is not None:
        return f"{evidence.exif_date.year:04d}", f"{evidence.exif_date.month:02d}"
    match = DATE_IN_NAME.search(evidence.name)
    return (match.group(1), match.group(2)) if match else (None, None)


def placeholders(evidence: Evidence, verdict: Verdict) -> tuple[tuple[str, str | None], ...]:
    """The subkey values this file can give, whatever the leaf: date and Thema folders."""
    year, month = file_date(evidence)
    return (("{year}", year), ("{month}", month), ("{thema}", verdict.thema))


def fill_subkey(leaf: Leaf, fill: Sequence[tuple[str, str | None]]) -> str:
    """Leaf path plus its subkey filled from fill; any unfillable placeholder -> the leaf root."""
    if not leaf.subkey:
        return leaf.path
    values = dict(fill)
    parts = [values.get(placeholder) for placeholder in leaf.subkey.split("/")]
    filled = [part for part in parts if part]
    if len(filled) != len(parts):
        return leaf.path
    return "/".join([leaf.path, *filled])


def target_dir(leaf: Leaf, evidence: Evidence, verdict: Verdict) -> str:
    """Leaf path plus its filled subkey (verdict.issuer already fitted to the leaf)."""
    return fill_subkey(leaf, (*placeholders(evidence, verdict), ("{issuer}", verdict.issuer)))


def _cap(band: Band, kind: Kind, verdict: Verdict) -> Band:
    if band != "green":
        return band
    if kind == "knowledge":
        return "yellow"
    if kind == "library" and verdict.isbn is None and verdict.issuer is None:
        return "yellow"
    return band


def band_for(verdict: Verdict, kind: Kind, ctx: Context) -> Band:
    """Band from the signal, its confidence and the calibration state, then the kind caps.

    verdict.issuer must already be fitted to the leaf (see decision_for).
    """
    settings = ctx.settings
    if verdict.leaf_id is None:
        return "red"
    if verdict.signal == "fallback" and verdict.confidence < settings.fallback_red:
        return "red"
    band: Band
    if verdict.signal in {"rules", "books"}:
        band = "green"
    elif verdict.signal == "fallback":
        calibrated = ctx.confirmed.get(kind, 0) >= settings.calibration_min
        band = "green" if calibrated and verdict.confidence >= settings.fallback_green else "yellow"
    else:
        band = "yellow"
    return _cap(band, kind, verdict)


def _from_cache(data: dict[str, Any]) -> Verdict:
    ranked = tuple((str(leaf), float(p)) for leaf, p in data.pop("ranked", ()))
    return Verdict(**data, ranked=ranked)


def _verdict(evidence: Evidence, ctx: Context) -> Verdict:
    if evidence.secret is not None:
        return Verdict(None, "secret", 0.0, f"secret ({evidence.secret}): never sent, never moved")
    # Rules and issuers read the filename, so the name is part of the cache key.
    key = f"{ctx.fingerprint}:{evidence.name}"
    # Only a run with the model on may reuse a model verdict; with it off, the cascade
    # decides from pins, ISBNs and hints alone.
    cached = ctx.cache.get_verdict(evidence.sha256, key) if ctx.fallback is not None else None
    if cached is not None:
        return _from_cache(cached)
    verdict, _ = choose(evidence, ctx)
    if verdict.signal == "fallback":
        ctx.cache.put_verdict(evidence.sha256, key, asdict(verdict))
    return verdict


def decision_for(evidence: Evidence, verdict: Verdict, ctx: Context) -> Decision:
    """Band and target for a verdict on this evidence."""
    leaf = ctx.config.tree.leaves.get(verdict.leaf_id) if verdict.leaf_id else None
    if leaf is None or verdict.leaf_id is None:
        return Decision(
            path=evidence.path,
            sha256=evidence.sha256,
            leaf_id=None,
            target_dir=None,
            band="red",
            signal=verdict.signal,
            confidence=verdict.confidence,
            evidence_summary=verdict.summary,
            about=verdict.about,
        )
    fitted = replace(verdict, issuer=issuer_for(verdict.leaf_id, verdict.issuer, ctx.config))
    return Decision(
        path=evidence.path,
        sha256=evidence.sha256,
        leaf_id=verdict.leaf_id,
        target_dir=target_dir(leaf, evidence, fitted),
        band=band_for(fitted, leaf.kind, ctx),
        signal=verdict.signal,
        confidence=verdict.confidence,
        evidence_summary=verdict.summary,
        kind=leaf.kind,
        suggested_name=verdict.suggested_name,
        ranked=verdict.ranked,
        about=verdict.about,
        issuer=verdict.issuer,
        fill=placeholders(evidence, verdict),
    )


def classify(path: Path, ctx: Context) -> Decision:
    """Extract, decide, band and place one file. Pure: nothing on disk changes."""
    evidence = extract(path, root=ctx.settings.para_root, preview_chars=ctx.settings.preview_chars)
    return decision_for(evidence, _verdict(evidence, ctx), ctx)
