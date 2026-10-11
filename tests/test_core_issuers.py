"""Signal 3: issuer patterns; short ones match whole words only."""

from __future__ import annotations

import unicodedata

from para_files.core.issuers import IssuerMatch, found, match_issuer
from para_files.core.tree import IssuersFile, RulesFile, Tree, TreeConfig
from tests.core_helpers import make_config


def test_short_pattern_needs_a_whole_word():
    assert not found("ABC", "nabcd subscription")
    assert found("ABC", "abc_releve_2025.pdf")
    assert found("ABC", "statement from ABC.")


def test_long_pattern_is_a_substring():
    assert found("AcmeCard", "2026-01-23_acmecardfacture.pdf")


def test_keyword_agreement_picks_the_leaf():
    config = make_config()
    match = match_issuer("2026-01-23_acmecard_invoice.pdf", "", config)
    assert match == IssuerMatch("acmecard", "AcmeCard", "archives_5y_factures", agreed=True)


def test_tie_goes_to_the_first_leaf():
    config = make_config()
    match = match_issuer("acmecard_facture.pdf", "", config)
    assert match.leaf_id == "archives_10y_banques"
    assert match.agreed


def test_no_keyword_is_not_agreed():
    match = match_issuer("abc_2025.pdf", "", make_config())
    assert match == IssuerMatch("abc", "ABC", "archives_10y_banques", agreed=False)


def test_pattern_found_in_preview():
    match = match_issuer("scan_0001.pdf", "Your AcmeCard monthly statement", make_config())
    assert match.issuer == "acmecard"
    assert match.leaf_id == "archives_10y_banques"


def test_longest_pattern_wins():
    match = match_issuer("abc and acmecard.example notice", "", make_config())
    assert match.pattern == "acmecard.example"


def _accent_config() -> TreeConfig:
    """One accented issuer pattern; the banks leaf has an accented keyword."""
    return TreeConfig(
        tree=Tree.model_validate(
            {
                "leaves": {
                    "archives_10y_banques": {
                        "kind": "record",
                        "retention": "10y",
                        "path": "4_Archives/10y_banques",
                        "describe": "Statements",
                        "keywords": ["relevé"],
                    },
                    "archives_5y_factures": {
                        "kind": "record",
                        "retention": "5y",
                        "path": "4_Archives/5y_factures",
                        "describe": "Invoices",
                        "keywords": ["facture"],
                    },
                }
            }
        ),
        rules=RulesFile(),
        issuers=IssuersFile.model_validate(
            {
                "issuers": {
                    "societe": {
                        "patterns": ["Société Générique"],
                        "leaves": ["archives_10y_banques", "archives_5y_factures"],
                    }
                }
            }
        ),
    )


def test_nfd_filename_matches_nfc_pattern():
    name = unicodedata.normalize("NFD", "Société Générique relevé.pdf")
    match = match_issuer(name, "", _accent_config())
    assert match is not None
    assert match.issuer == "societe"
    assert match.pattern == "Société Générique"


def test_nfd_keyword_counts_toward_agreement():
    name = unicodedata.normalize("NFD", "relevé.pdf")
    match = match_issuer(name, "Société Générique", _accent_config())
    assert match == IssuerMatch("societe", "Société Générique", "archives_10y_banques", agreed=True)


def test_no_issuer():
    assert match_issuer("holiday.txt", "nothing here", make_config()) is None
