"""Signal 1: filename globs, case-insensitive, first rule wins."""

from __future__ import annotations

import unicodedata

from para_files.core.rules import RuleMatch, match_rule
from para_files.core.tree import Rule


RULES = (
    Rule(name="payslips", leaf="travail", globs=("*payslip*", "*compte de salaire*")),
    Rule(name="pdfs", leaf="docs", globs=("*.pdf",)),
)


def test_first_matching_rule_wins():
    assert match_rule("Payslip_2025-12.pdf", RULES) == RuleMatch("payslips", "*payslip*", "travail")


def test_case_insensitive():
    assert match_rule("REPORT.PDF", RULES) == RuleMatch("pdfs", "*.pdf", "docs")


def test_nfd_name_matches_nfc_glob():
    name = unicodedata.normalize("NFD", "2025.11 - Décompte de salaire.pdf")
    assert match_rule(name, RULES).rule == "payslips"


def test_no_match():
    assert match_rule("notes.txt", RULES) is None
