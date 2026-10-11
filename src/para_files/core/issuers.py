"""Signal 3, issuers: an issuer pattern in the name or preview, leaf by keyword agreement.

Patterns of SHORT characters or fewer match only as whole words, so "ABC" never fires inside
"nabcd" (spec §4.1 warns about them; this is the fix).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from para_files.core.tree import TreeConfig


SHORT = 3


@dataclass(frozen=True)
class IssuerMatch:
    """Which issuer and pattern matched, the chosen leaf, and whether a leaf keyword agreed."""

    issuer: str
    pattern: str
    leaf_id: str
    agreed: bool


def _fold(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def found(pattern: str, text: str) -> bool:
    """Pattern in text (text already folded or not); short patterns as whole words."""
    needle, haystack = _fold(pattern), _fold(text)
    if len(needle) > SHORT:
        return needle in haystack
    return re.search(rf"(?<![^\W_]){re.escape(needle)}(?![^\W_])", haystack) is not None


def match_issuer(name: str, preview: str, config: TreeConfig) -> IssuerMatch | None:
    """Longest matching issuer pattern; then the issuer leaf with the most keyword hits."""
    text = _fold(f"{name}\n{preview}")
    best: tuple[str, str] | None = None
    for issuer_name, issuer in config.issuers.issuers.items():
        for pattern in issuer.patterns:
            if found(pattern, text) and (best is None or len(pattern) > len(best[1])):
                best = (issuer_name, pattern)
    if best is None:
        return None
    issuer_name, pattern = best
    scores = [
        (sum(found(keyword, text) for keyword in config.tree.leaves[leaf_id].keywords), leaf_id)
        for leaf_id in config.issuers.issuers[issuer_name].leaves
    ]
    top = max(score for score, _ in scores)
    leaf_id = next(leaf for score, leaf in scores if score == top)
    return IssuerMatch(issuer_name, pattern, leaf_id, agreed=top > 0)
