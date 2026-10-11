"""Signal 1, rules: owner globs on the filename (spec §4.2). Case-insensitive, NFC."""

from __future__ import annotations

import fnmatch
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from para_files.core.tree import Rule


@dataclass(frozen=True)
class RuleMatch:
    """The rule and glob that matched, and the leaf they send the file to."""

    rule: str
    glob: str
    leaf_id: str


def _fold(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def match_rule(name: str, rules: Sequence[Rule]) -> RuleMatch | None:
    """First rule (file order) with a glob matching the filename."""
    folded = _fold(name)
    for rule in rules:
        for glob in rule.globs:
            if fnmatch.fnmatchcase(folded, _fold(glob)):
                return RuleMatch(rule.name, glob, rule.leaf)
    return None
