"""The cascade (spec §4.2): evidence -> first deciding signal -> band -> target directory."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from loguru import logger

from para_files.core.books import Lookup, match_book
from para_files.core.cache import Cache
from para_files.core.evidence import Evidence, extract
from para_files.core.fallback import FallbackChoice
from para_files.core.issuers import match_issuer
from para_files.core.rules import match_rule
from para_files.core.settings import CoreSettings
from para_files.core.tree import Kind, Leaf, Tree, TreeConfig
from para_files.utils.isbn_lookup import lookup_isbn


Band = Literal["green", "yellow", "red"]
RULE_CONFIDENCE = 1.0
ISSUER_AGREED = 0.95
ISSUER_ALONE = 0.8
DATE_IN_NAME = re.compile(r"(?<!\d)((?:19|20)\d{2})(?:[-_. ]?(0[1-9]|1[0-2]))?(?!\d)")


class Fallback(Protocol):
    """Signal 4 as the cascade sees it."""

    def decide(self, evidence: Evidence, tree: Tree) -> FallbackChoice | None:
        """Leaf choice for this evidence, or None."""


@dataclass(frozen=True)
class Verdict:
    """What the winning signal said; cached by content hash and config fingerprint."""

    leaf_id: str | None
    signal: str
    confidence: float
    summary: str
    isbn: str | None = None
    issuer: str | None = None
    thema: str | None = None
    suggested_name: str | None = None


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


def _rules(evidence: Evidence, ctx: Context) -> Verdict | None:
    match = match_rule(evidence.name, ctx.config.rules.rules)
    if match is None:
        return None
    return Verdict(
        match.leaf_id, "rules", RULE_CONFIDENCE, f"rule {match.rule!r} glob {match.glob!r}"
    )


def _books(evidence: Evidence, ctx: Context) -> Verdict | None:
    match = match_book(evidence, ctx.config.tree, ctx.cache, ctx.lookup)
    if match is None:
        return None
    summary = f"ISBN {match.isbn}" if match.isbn else "book heuristics (no ISBN)"
    return Verdict(
        match.leaf_id,
        "books",
        match.confidence,
        summary,
        isbn=match.isbn,
        thema=match.thema,
        suggested_name=match.suggested_name,
    )


def _issuers(evidence: Evidence, ctx: Context) -> Verdict | None:
    match = match_issuer(evidence.name, evidence.text_preview, ctx.config)
    if match is None:
        return None
    summary = f"issuer {match.issuer!r} pattern {match.pattern!r}"
    return Verdict(
        match.leaf_id,
        "issuers",
        ISSUER_AGREED if match.agreed else ISSUER_ALONE,
        summary + (" + leaf keyword" if match.agreed else ""),
        issuer=match.issuer,
    )


def _fallback(evidence: Evidence, ctx: Context) -> Verdict | None:
    if ctx.fallback is None:
        return None
    choice = ctx.fallback.decide(evidence, ctx.config.tree)
    if choice is None:
        return None
    ranked = ", ".join(f"{leaf} {p:.2f}" for leaf, p in choice.ranked)
    return Verdict(choice.leaf_id, "fallback", choice.confidence, f"{choice.model}: {ranked}")


SIGNALS: tuple[tuple[str, Callable[[Evidence, Context], Verdict | None]], ...] = (
    ("rules", _rules),
    ("books", _books),
    ("issuers", _issuers),
    ("fallback", _fallback),
)
NO_VERDICT = Verdict(None, "none", 0.0, "no signal decided")


def run_signals(evidence: Evidence, ctx: Context) -> Verdict:
    """First signal with a verdict wins; a failing signal hands over to the next one."""
    for name, signal in SIGNALS:
        try:
            verdict = signal(evidence, ctx)
        except Exception as exc:  # noqa: BLE001 - KeyboardInterrupt is not an Exception
            logger.warning("signal {} failed on {}: {}", name, evidence.name, exc)
            continue
        if verdict is not None:
            return verdict
    return NO_VERDICT


def file_date(evidence: Evidence) -> tuple[str | None, str | None]:
    """(year, month) from EXIF, else from a date in the filename."""
    if evidence.exif_date is not None:
        return f"{evidence.exif_date.year:04d}", f"{evidence.exif_date.month:02d}"
    match = DATE_IN_NAME.search(evidence.name)
    return (match.group(1), match.group(2)) if match else (None, None)


def target_dir(leaf: Leaf, evidence: Evidence, verdict: Verdict) -> str:
    """Leaf path plus its filled subkey; any unfillable placeholder -> the leaf root."""
    if not leaf.subkey:
        return leaf.path
    year, month = file_date(evidence)
    values = {
        "{year}": year,
        "{month}": month,
        "{issuer}": verdict.issuer,
        "{thema}": verdict.thema,
    }
    parts = [values[placeholder] for placeholder in leaf.subkey.split("/")]
    filled = [part for part in parts if part]
    if len(filled) != len(parts):
        return leaf.path
    return "/".join([leaf.path, *filled])


def _cap(band: Band, kind: Kind, verdict: Verdict) -> Band:
    if band != "green":
        return band
    if kind == "knowledge":
        return "yellow"
    if kind == "library" and verdict.isbn is None and verdict.signal != "issuers":
        return "yellow"
    return band


def band_for(verdict: Verdict, kind: Kind, ctx: Context) -> Band:
    """Band from the signal, its confidence and the calibration state, then the kind caps."""
    settings = ctx.settings
    if verdict.leaf_id is None:
        return "red"
    if verdict.signal == "fallback" and verdict.confidence < settings.fallback_red:
        return "red"
    band: Band
    if verdict.signal == "rules":
        band = "green"
    elif verdict.signal == "books":
        band = "green" if verdict.isbn else "yellow"
    else:
        threshold = (
            settings.issuers_green if verdict.signal == "issuers" else settings.fallback_green
        )
        calibrated = ctx.confirmed.get(kind, 0) >= settings.calibration_min
        band = "green" if calibrated and verdict.confidence >= threshold else "yellow"
    return _cap(band, kind, verdict)


def _verdict(evidence: Evidence, ctx: Context) -> Verdict:
    if evidence.secret is not None:
        return Verdict(None, "secret", 0.0, f"secret ({evidence.secret}): never sent, never moved")
    cached = ctx.cache.get_verdict(evidence.sha256, ctx.fingerprint)
    if cached is not None:
        return Verdict(**cached)
    verdict = run_signals(evidence, ctx)
    if verdict.leaf_id is not None:
        ctx.cache.put_verdict(evidence.sha256, ctx.fingerprint, asdict(verdict))
    return verdict


def classify(path: Path, ctx: Context) -> Decision:
    """Extract, decide, band and place one file. Pure: nothing on disk changes."""
    evidence = extract(path, root=ctx.settings.para_root, preview_chars=ctx.settings.preview_chars)
    verdict = _verdict(evidence, ctx)
    leaf = ctx.config.tree.leaves.get(verdict.leaf_id) if verdict.leaf_id else None
    if leaf is None:
        return Decision(
            path=evidence.path,
            sha256=evidence.sha256,
            leaf_id=None,
            target_dir=None,
            band="red",
            signal=verdict.signal,
            confidence=verdict.confidence,
            evidence_summary=verdict.summary,
        )
    return Decision(
        path=evidence.path,
        sha256=evidence.sha256,
        leaf_id=verdict.leaf_id,
        target_dir=target_dir(leaf, evidence, verdict),
        band=band_for(verdict, leaf.kind, ctx),
        signal=verdict.signal,
        confidence=verdict.confidence,
        evidence_summary=verdict.summary,
        kind=leaf.kind,
        suggested_name=verdict.suggested_name,
    )
