"""OCR metadata extraction for intelligent file renaming.

This module extracts structured metadata (date, issuer, document type)
from OCR text to enable intelligent renaming of generic PDFs before
classification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from loguru import logger


if TYPE_CHECKING:
    from para_files.taxonomies.loader import TaxonomyLoader
    from para_files.taxonomies.models import DocumentTaxonomy

# Date extraction patterns (ordered by reliability)
_DATE_PATTERNS: list[tuple[str, str]] = [
    # ISO format (most reliable)
    (r"\b(\d{4})-(\d{2})-(\d{2})\b", "YMD"),
    # European formats (DD/MM/YYYY, DD.MM.YYYY)
    (r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", "DMY"),
    (r"\b(\d{1,2})[./](\d{1,2})[./](\d{2})\b", "DMY_SHORT"),
    # French text date (15 janvier 2024)
    (
        r"\b(\d{1,2})\s+"
        r"(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)"
        r"\s+(\d{4})\b",
        "FR_TEXT",
    ),
    # English text date (January 15, 2024)
    (
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)"
        r"\s+(\d{1,2}),?\s+(\d{4})\b",
        "EN_TEXT",
    ),
]

# Month mappings
_FRENCH_MONTHS: dict[str, int] = {
    "janvier": 1,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
}

_ENGLISH_MONTHS: dict[str, int] = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

# Document type detection patterns (keyword -> type)
_DOC_TYPE_PATTERNS: dict[str, list[str]] = {
    "facture": [
        "facture",
        "invoice",
        "rechnung",
        "n° facture",
        "facture n°",
        "montant dû",
        "total ttc",
        "net à payer",
    ],
    "salaire": [
        "bulletin de paie",
        "bulletin de salaire",
        "fiche de paie",
        "décompte de salaire",
        "payslip",
        "lohnabrechnung",
        "salaire brut",
        "salaire net",
        "rémunération",
        "syntec",
        "urssaf",
    ],
    "releve": [
        "relevé de compte",
        "relevé bancaire",
        "account statement",
        "kontoauszug",
        "extrait de compte",
    ],
    "contrat": [
        "contrat",
        "contract",
        "vertrag",
        "conditions générales",
        "entre les soussignés",
    ],
    "attestation": [
        "attestation",
        "certificat",
        "certificate",
        "bescheinigung",
        "nous certifions",
        "je soussigné",
    ],
    "quittance": [
        "quittance",
        "reçu",
        "receipt",
        "quittung",
        "accusé de réception",
    ],
    "don": [
        "reçu de don",
        "attestation de don",
        "merci pour votre don",
        "confirmation de don",
        "déductible fiscalement",
    ],
    "impot": [
        "déclaration d'impôt",
        "bordereau",
        "taxation",
        "vaudtax",
        "acompte",
    ],
    "assurance": [
        "police d'assurance",
        "attestation d'assurance",
        "prime d'assurance",
        "sinistre",
        "couverture",
    ],
    "courrier": [
        "cher monsieur",
        "chère madame",
        "dear",
        "sehr geehrte",
        "veuillez agréer",
        "cordialement",
    ],
}

# Confidence thresholds
_DATE_HEADER_BONUS = 0.2  # Bonus if date is in header (first 500 chars)
_ISSUER_MATCH_CONFIDENCE = 0.8
_DOC_TYPE_MATCH_CONFIDENCE = 0.6
_MIN_OVERALL_CONFIDENCE = 0.3

# Text analysis thresholds
_HEADER_LENGTH = 500
_MIN_TEXT_LENGTH = 20
_TWO_DIGIT_YEAR_THRESHOLD = 100
_MIN_COMPANY_NAME_LENGTH = 3


@dataclass
class OCRMetadata:
    """Extracted metadata from OCR text."""

    document_date: date | None = None
    issuer: str | None = None
    doc_type: str | None = None
    confidence: float = 0.0

    def has_enough_info(self) -> bool:
        """Check if we have enough info to rename."""
        # Need at least date or issuer with acceptable confidence
        has_date = self.document_date is not None
        has_issuer = self.issuer is not None
        return (has_date or has_issuer) and self.confidence >= _MIN_OVERALL_CONFIDENCE


def _extract_date(text: str) -> tuple[date | None, float]:
    """Extract document date from text.

    Looks for dates in common formats, preferring dates in the header area.

    Args:
        text: OCR text content

    Returns:
        Tuple of (extracted date or None, confidence score)
    """
    header = text[:_HEADER_LENGTH].lower()
    full_text = text.lower()

    for pattern, format_type in _DATE_PATTERNS:
        # First try header (more reliable)
        match = re.search(pattern, header, re.IGNORECASE)
        area = "header"

        if not match:
            match = re.search(pattern, full_text, re.IGNORECASE)
            area = "body"

        if match:
            try:
                extracted_date = _parse_date_match(match, format_type)
                if extracted_date:
                    # Validate date is reasonable (not too old, not in future)
                    today = datetime.now(tz=UTC).date()
                    if date(1990, 1, 1) <= extracted_date <= today:
                        confidence = 0.7 if area == "header" else 0.5
                        return extracted_date, confidence
            except (ValueError, TypeError):
                continue

    return None, 0.0


def _parse_date_match(match: re.Match[str], format_type: str) -> date | None:
    """Parse a regex match into a date object."""
    groups = match.groups()

    if format_type == "YMD":
        return date(int(groups[0]), int(groups[1]), int(groups[2]))

    if format_type == "DMY":
        day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
        return date(year, month, day)

    if format_type == "DMY_SHORT":
        day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
        # Assume 20xx for 2-digit years
        year = 2000 + year if year < _TWO_DIGIT_YEAR_THRESHOLD else year
        return date(year, month, day)

    if format_type == "FR_TEXT":
        day = int(groups[0])
        month = _FRENCH_MONTHS.get(groups[1].lower(), 0)
        year = int(groups[2])
        if month:
            return date(year, month, day)

    elif format_type == "EN_TEXT":
        month = _ENGLISH_MONTHS.get(groups[0].lower(), 0)
        day = int(groups[1])
        year = int(groups[2])
        if month:
            return date(year, month, day)

    return None


def _build_issuer_patterns(taxonomy: DocumentTaxonomy) -> list[tuple[str, str]]:
    """Build list of (pattern, issuer_name) from taxonomy."""
    patterns: list[tuple[str, str]] = []
    for issuer, _doc_type, _category in taxonomy.get_all_issuers():
        patterns.extend((p.lower(), issuer.name) for p in issuer.patterns)
    return patterns


def _search_pattern_in_text(
    patterns: list[tuple[str, str]], text: str, confidence: float
) -> tuple[str | None, float]:
    """Search for patterns in text and return first match with confidence."""
    for pattern, issuer_name in patterns:
        pattern_regex = r"\b" + re.escape(pattern) + r"\b"
        if re.search(pattern_regex, text, re.IGNORECASE):
            return issuer_name, confidence
    return None, 0.0


def _extract_issuer(text: str, taxonomy_loader: TaxonomyLoader | None) -> tuple[str | None, float]:
    """Extract issuer from text using taxonomy patterns."""
    if not taxonomy_loader:
        return None, 0.0

    taxonomy = taxonomy_loader.load_documents()
    if not taxonomy or not taxonomy.categories:
        return None, 0.0

    issuer_patterns = _build_issuer_patterns(taxonomy)

    # Search in header first (more reliable)
    header = text[:_HEADER_LENGTH].lower()
    result = _search_pattern_in_text(issuer_patterns, header, _ISSUER_MATCH_CONFIDENCE)
    if result[0]:
        return result

    # Then search in full text
    result = _search_pattern_in_text(issuer_patterns, text.lower(), _ISSUER_MATCH_CONFIDENCE * 0.8)
    if result[0]:
        return result

    # Fallback: try to detect company names from common suffixes
    company_pattern = (
        r"\b([A-Z][a-zA-ZÀ-ÿ]+(?:\s+[A-Z][a-zA-ZÀ-ÿ]+)*)\s+(?:SA|Sàrl|GmbH|AG|Inc|Ltd|SAS)\b"
    )
    match = re.search(company_pattern, text[:_HEADER_LENGTH])
    if match:
        company_name = match.group(1).strip()
        if len(company_name) >= _MIN_COMPANY_NAME_LENGTH:
            return company_name, 0.5

    return None, 0.0


def _extract_doc_type(text: str) -> tuple[str | None, float]:
    """Extract document type from text using keyword patterns.

    Args:
        text: OCR text content

    Returns:
        Tuple of (document type or None, confidence score)
    """
    text_lower = text.lower()
    header = text_lower[:500]

    # Count keyword matches for each type
    type_scores: dict[str, int] = {}

    for doc_type, keywords in _DOC_TYPE_PATTERNS.items():
        score = 0
        for keyword in keywords:
            # Check header first (weighted 2x)
            if keyword.lower() in header:
                score += 2
            elif keyword.lower() in text_lower:
                score += 1

        if score > 0:
            type_scores[doc_type] = score

    if type_scores:
        # Return type with highest score
        best_type = max(type_scores, key=lambda k: type_scores[k])
        best_score = type_scores[best_type]
        # Confidence based on number of matches
        confidence = min(0.3 + (best_score * 0.15), _DOC_TYPE_MATCH_CONFIDENCE)
        return best_type, confidence

    return None, 0.0


def extract_metadata(
    text: str,
    taxonomy_loader: TaxonomyLoader | None = None,
) -> OCRMetadata:
    """Extract structured metadata from OCR text.

    Args:
        text: OCR text content to analyze
        taxonomy_loader: Optional taxonomy loader for issuer matching

    Returns:
        OCRMetadata with extracted date, issuer, doc_type and confidence
    """
    if not text or len(text.strip()) < _MIN_TEXT_LENGTH:
        return OCRMetadata()

    # Extract each component
    doc_date, date_conf = _extract_date(text)
    issuer, issuer_conf = _extract_issuer(text, taxonomy_loader)
    doc_type, type_conf = _extract_doc_type(text)

    # Calculate overall confidence
    # Weight: date 0.4, issuer 0.4, type 0.2
    components = []
    if doc_date:
        components.append(date_conf * 0.4)
    if issuer:
        components.append(issuer_conf * 0.4)
    if doc_type:
        components.append(type_conf * 0.2)

    overall_confidence = sum(components) if components else 0.0

    logger.debug(
        f"OCR metadata extracted: date={doc_date}, issuer={issuer}, "
        f"type={doc_type}, confidence={overall_confidence:.2f}"
    )

    return OCRMetadata(
        document_date=doc_date,
        issuer=issuer,
        doc_type=doc_type,
        confidence=overall_confidence,
    )
