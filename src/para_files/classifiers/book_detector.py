"""Signal 1: Book detector classifier (96% confidence, 100% with ISBN).

Detects technical books through multi-signal analysis:
- ISBN extraction and lookup
- PDF metadata analysis
- Content structure patterns (chapters, ToC, etc.)
- File characteristics (size, page count)

Uses semantic matching to determine the appropriate technology category.
"""

from __future__ import annotations

import re

from loguru import logger

from para_files.classifiers.base import BaseClassifier
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
)
from para_files.utils.filename_sanitizer import sanitize_filename
from para_files.utils.isbn_lookup import BookInfo, find_matching_book_info
from para_files.utils.pdf_metadata import (
    PdfMetadata,
    contains_book_keywords,
    extract_pdf_metadata,
    is_book_creator,
)
from para_files.utils.thema_lookup import ThemaLookup, get_thema_lookup


# Patterns that indicate book structure
BOOK_STRUCTURE_PATTERNS = [
    re.compile(r"table\s+of\s+contents", re.IGNORECASE),
    re.compile(r"chapter\s+\d+", re.IGNORECASE),
    re.compile(r"part\s+[IVX]+", re.IGNORECASE),
    re.compile(r"ISBN[:\s-]*[\d-]+", re.IGNORECASE),
    re.compile(r"copyright\s+\d{4}", re.IGNORECASE),
    re.compile(r"all\s+rights\s+reserved", re.IGNORECASE),
    re.compile(r"published\s+by", re.IGNORECASE),
    re.compile(r"first\s+edition", re.IGNORECASE),
    re.compile(r"\b(preface|foreword|acknowledgments)\b", re.IGNORECASE),
    re.compile(r"printed\s+in", re.IGNORECASE),
]

# Minimum thresholds
MIN_PAGES_FOR_BOOK = 50
MIN_SIZE_MB_FOR_BOOK = 5.0
DETECTION_THRESHOLD = 0.7  # Strict threshold
SMART_RENAME_THRESHOLD = 0.9  # Minimum confidence to suggest renaming with title
MIN_FINANCIAL_PATTERN_MATCHES = 2  # Minimum pattern matches to identify financial document

# Patterns that indicate NON-book financial/bank documents
# These documents often contain number sequences that look like ISBNs but are account numbers
FINANCIAL_EXCLUSION_PATTERNS = [
    re.compile(r"\bIBAN\b", re.IGNORECASE),
    re.compile(r"\bBIC\b|\bSWIFT\b", re.IGNORECASE),
    re.compile(r"\b(BANQUE|BANK)\b", re.IGNORECASE),
    re.compile(r"\bRELEV[EÉ]\b", re.IGNORECASE),  # Relevé (bank statement)
    re.compile(r"\bAVIS\s+D.?[EÉ]CRITURES?\b", re.IGNORECASE),  # AVIS D'ECRITURES
    re.compile(r"\bDEBIT\s+NOTICE\b", re.IGNORECASE),
    re.compile(r"\bBANK\s+STATEMENT\b", re.IGNORECASE),
    re.compile(r"\bFACTURE\b", re.IGNORECASE),  # Invoice
    re.compile(r"\bSOLDE\s+(A\s+NOUVEAU|EN\s+CHF|EN\s+EUR)\b", re.IGNORECASE),
    re.compile(r"CH\d{2}\s*\d{4}\s*\d{4}", re.IGNORECASE),  # Swiss IBAN pattern
    re.compile(r"\bCLEARING\s*:\s*\d+\b", re.IGNORECASE),  # Bank clearing number
    # Visa/credit card statements
    re.compile(r"\bVISA\b", re.IGNORECASE),
    re.compile(r"\bMASTERCARD\b", re.IGNORECASE),
    re.compile(r"\bCARTE\s+(DE\s+)?CR[EÉ]DIT\b", re.IGNORECASE),
    # UBS specific patterns
    re.compile(r"\bUBS\b", re.IGNORECASE),
    re.compile(r"\bEXTRAIT\s+DE\s+COMPTE\b", re.IGNORECASE),
]

# Patterns that indicate tax/government documents (often have ISBN-like reference numbers)
TAX_EXCLUSION_PATTERNS = [
    re.compile(r"\bD[EÉ]CLARATION\s+(EN\s+LIGNE\s+)?(DE\s+|DES\s+)?REVENUS?\b", re.IGNORECASE),
    re.compile(r"\bIMPOTS?\s+(SUR\s+)?(LE\s+)?REVENU\b", re.IGNORECASE),
    re.compile(r"\bFORMULAIRE\s+2042\b", re.IGNORECASE),
    re.compile(r"\bIR-Form-2042\b", re.IGNORECASE),
    re.compile(r"\bAVIS\s+D.?IMPOSITION\b", re.IGNORECASE),
    re.compile(r"\bimpots\.gouv\b", re.IGNORECASE),
    re.compile(r"\bREVENU\s+FISCAL\b", re.IGNORECASE),
    re.compile(r"\bTR[EÉ]SOR\s+PUBLIC\b", re.IGNORECASE),
    re.compile(r"\bDGFIP\b", re.IGNORECASE),  # Direction Générale des Finances Publiques
]

# Patterns that indicate insurance documents
INSURANCE_EXCLUSION_PATTERNS = [
    re.compile(r"\bGROUPE\s+MUTUEL\b", re.IGNORECASE),
    re.compile(r"\bGMA\b"),  # Case sensitive - GMA is specific
    re.compile(r"\bASSURANCE\s+(MALADIE|SANT[EÉ])\b", re.IGNORECASE),
    re.compile(r"\bREMBOURSEMENT\b", re.IGNORECASE),
    re.compile(r"\bD[EÉ]COMPTE\s+(DE\s+)?PRESTATIONS?\b", re.IGNORECASE),
    re.compile(r"\bZURICH\s+(ASSURANCE|INSURANCE)\b", re.IGNORECASE),
    re.compile(r"\bAXA\s+(ASSURANCE|WINTERTHUR)?\b", re.IGNORECASE),
    re.compile(r"\bSWICA\b", re.IGNORECASE),
    re.compile(r"\bCSS\s+(ASSURANCE)?\b", re.IGNORECASE),
    re.compile(r"\bHELSANA\b", re.IGNORECASE),
]

# Patterns that indicate transport/travel documents (tickets with ID numbers that look like ISBNs)
TRANSPORT_EXCLUSION_PATTERNS = [
    re.compile(r"\bTicket-ID\b", re.IGNORECASE),
    re.compile(r"\bBillet\s+de\s+parcours\b", re.IGNORECASE),  # Swiss train ticket
    re.compile(r"\bSchweizerische\s+Bundesbahnen\b", re.IGNORECASE),  # SBB
    re.compile(r"\b(CFF|SBB|FFS)\b"),  # Swiss Federal Railways
    re.compile(r"\bBoarding\s+Pass\b", re.IGNORECASE),
    re.compile(r"\bE-?Ticket\b", re.IGNORECASE),
    re.compile(r"\bItinerary\b", re.IGNORECASE),
    re.compile(r"\bFlight\s+(Number|No\.?|#)\b", re.IGNORECASE),
    re.compile(r"\bTrain\s+(Number|No\.?|#)\b", re.IGNORECASE),
    re.compile(r"\bReservation\s+(Number|No\.?|#|Code)\b", re.IGNORECASE),
    re.compile(r"\bConfirmation\s+(Number|No\.?|#|Code)\b", re.IGNORECASE),
    re.compile(r"\bPNR\b", re.IGNORECASE),  # Passenger Name Record
    re.compile(r"\bvon/de/da/from\b", re.IGNORECASE),  # Multilingual from/to on Swiss tickets
    re.compile(r"\bnach/a/a/to\b", re.IGNORECASE),
    # French train patterns (SNCF, TER, etc.)
    re.compile(r"\bMON\s+BILLET\b", re.IGNORECASE),
    re.compile(r"\bBILLET\s+REMI\b", re.IGNORECASE),
    re.compile(r"\bTER\s+\d+\b", re.IGNORECASE),  # TER train number
    re.compile(r"\bTGV\s+\d+\b", re.IGNORECASE),  # TGV train number
    re.compile(r"\bSNCF\b", re.IGNORECASE),
    re.compile(r"\bITIN[ÉE]RAIRE\s+(ALLER|RETOUR)\b", re.IGNORECASE),
    re.compile(r"\bAller\s+Simple\b", re.IGNORECASE),
    re.compile(r"\bAller[\s-]Retour\b", re.IGNORECASE),
    # Italian transport patterns
    re.compile(r"\bbiglietto\b", re.IGNORECASE),  # Italian: ticket
    re.compile(r"\bTrenitalia\b", re.IGNORECASE),
    # Museum/cultural event tickets (also have ticket IDs)
    re.compile(r"\bmuseo\b", re.IGNORECASE),  # Italian: museum
    re.compile(r"\bmus[ée]e\b", re.IGNORECASE),  # French: museum
    re.compile(r"\bvisit[ea]\b", re.IGNORECASE),  # Visit
    re.compile(r"\bsottomarino\b", re.IGNORECASE),  # Italian: submarine
]

# Patterns that indicate telecom/contract documents (IDs look like ISBNs)
TELECOM_EXCLUSION_PATTERNS = [
    re.compile(r"\bDocID\b", re.IGNORECASE),
    re.compile(r"\bContractID\b", re.IGNORECASE),
    re.compile(r"\bPortabilit[ée]\b", re.IGNORECASE),  # Phone number portability
    re.compile(r"\btransfert\s+du.*num[ée]ro\b", re.IGNORECASE),
    re.compile(r"\b(Sunrise|Swisscom|Salt|Wingo|UPC|Quickline)\b", re.IGNORECASE),
    re.compile(r"\babonnement\b", re.IGNORECASE),
    re.compile(r"\bop[ée]rateur\b", re.IGNORECASE),
    re.compile(r"\bcarte\s+pr[ée]pay[ée]e\b", re.IGNORECASE),
    re.compile(r"\bnum[ée]ro\s+de\s+t[ée]l[ée]phone\b", re.IGNORECASE),
    re.compile(r"\b07\d{8}\b"),  # Swiss mobile number format
]


def is_financial_document(content: str, filename: str) -> bool:
    """Check if document is a financial/bank document that should be excluded from book detection.

    Args:
        content: Text content to analyze.
        filename: Filename to check.

    Returns:
        True if the document appears to be a financial document.
    """
    # Check filename patterns
    filename_lower = filename.lower()
    financial_filename_patterns = [
        "facture",
        "invoice",
        "relevé",
        "releve",
        "statement",
        "debit",
        "credit",
        "banque",
        "bank",
        "bcv",
        "ubs",
        "postfinance",
        "raiffeisen",
        "visa-",  # Visa card statements
        "visa_",
        "visebpp",
        "extrait",
        "décompte",
        "decompte",
        "avis-",
        "0264",  # UBS account number prefix
    ]
    if any(pattern in filename_lower for pattern in financial_filename_patterns):
        return True

    # Check content for financial patterns (need multiple matches to be sure)
    matches = sum(1 for pattern in FINANCIAL_EXCLUSION_PATTERNS if pattern.search(content))
    return matches >= MIN_FINANCIAL_PATTERN_MATCHES


def is_tax_document(content: str, filename: str) -> bool:
    """Check if document is a tax/government document that should be excluded from book detection.

    Tax documents often contain reference numbers that look like ISBNs.

    Args:
        content: Text content to analyze.
        filename: Filename to check.

    Returns:
        True if the document appears to be a tax document.
    """
    # Check filename patterns
    filename_lower = filename.lower()
    tax_filename_patterns = [
        "declaration_en_ligne",
        "déclaration_en_ligne",
        "declaration_des_revenus",
        "déclaration_des_revenus",
        "ir-form",
        "ir_form",
        "2042",
        "impot",
        "impôt",
        "avis_d_impot",
        "avis_impot",
    ]
    if any(pattern in filename_lower for pattern in tax_filename_patterns):
        return True

    # Check content for tax patterns (single match is enough - these are specific)
    return any(pattern.search(content) for pattern in TAX_EXCLUSION_PATTERNS)


def is_insurance_document(content: str, filename: str) -> bool:
    """Check if document is an insurance document that should be excluded from book detection.

    Insurance documents (GMA, health insurance) often have reference numbers that look like ISBNs.

    Args:
        content: Text content to analyze.
        filename: Filename to check.

    Returns:
        True if the document appears to be an insurance document.
    """
    # Check filename patterns
    filename_lower = filename.lower()
    insurance_filename_patterns = [
        "gma-",
        "gma_",
        "groupe_mutuel",
        "groupe-mutuel",
        "assurance",
        "remboursement",
        "zurich",
        "axa",
        "swica",
        "css",
        "helsana",
    ]
    if any(pattern in filename_lower for pattern in insurance_filename_patterns):
        return True

    # Check content for insurance patterns (single match is enough - these are specific)
    return any(pattern.search(content) for pattern in INSURANCE_EXCLUSION_PATTERNS)


def is_transport_document(content: str, filename: str) -> bool:
    """Check if document is a transport/travel document that should be excluded from book detection.

    Transport documents (train tickets, boarding passes) often have ticket IDs that
    look like ISBNs but are not books.

    Args:
        content: Text content to analyze.
        filename: Filename to check.

    Returns:
        True if the document appears to be a transport document.
    """
    # Check filename patterns
    filename_lower = filename.lower()
    transport_filename_patterns = [
        "ticket",
        "billet",
        "boarding",
        "flight",
        "train",
        "reservation",
        "itinerary",
        "voyage",
        "sbb",
        "cff",
        "sncf",
    ]
    if any(pattern in filename_lower for pattern in transport_filename_patterns):
        return True

    # Check content for transport patterns (single match is enough - these are specific)
    return any(pattern.search(content) for pattern in TRANSPORT_EXCLUSION_PATTERNS)


def is_telecom_document(content: str, filename: str) -> bool:
    """Check if document is a telecom/contract document that should be excluded from book detection.

    Telecom documents (portability forms, contracts) have DocIDs/ContractIDs that
    look like ISBNs but are not books.

    Args:
        content: Text content to analyze.
        filename: Filename to check.

    Returns:
        True if the document appears to be a telecom document.
    """
    # Check filename patterns
    filename_lower = filename.lower()
    telecom_filename_patterns = [
        "portability",
        "portabilite",
        "contrat",
        "contract",
        "abonnement",
        "subscription",
        "sunrise",
        "swisscom",
        "salt",
        "wingo",
    ]
    if any(pattern in filename_lower for pattern in telecom_filename_patterns):
        return True

    # Check content for telecom patterns (single match is enough - these are specific)
    return any(pattern.search(content) for pattern in TELECOM_EXCLUSION_PATTERNS)


def sanitize_title(title: str, max_length: int = 80) -> str:
    """Convert a book title to a valid filename.

    Uses the centralized filename sanitizer to handle all invalid characters.

    Args:
        title: Original title from PDF or ISBN lookup.
        max_length: Maximum filename length.

    Returns:
        Sanitized filename-safe string.
    """
    return sanitize_filename(title, replacement="_", max_length=max_length)


def score_book_structure(content: str) -> float:
    """Score content based on book structure patterns.

    Args:
        content: Text content to analyze.

    Returns:
        Score between 0.0 and 1.0 based on pattern matches.
    """
    matches = sum(1 for pattern in BOOK_STRUCTURE_PATTERNS if pattern.search(content))
    # 4+ patterns = max score of 1.0
    return min(matches / 4, 1.0)


class BookDetector(BaseClassifier):
    """Signal 1: Technical book detector (96% confidence, 100% with ISBN).

    Detects books through multi-signal analysis:
    1. ISBN extraction and API lookup (100% confidence if found)
    2. PDF metadata (title, author, creator, pages)
    3. Content structure (chapters, ToC, ISBN mentions)
    4. File characteristics (size)

    Returns the technology-specific destination path if detected.
    """

    def __init__(
        self,
        technologies: list[str] | None = None,
        *,
        enable_isbn_lookup: bool = True,
        thema_lookup: ThemaLookup | None = None,
    ) -> None:
        """Initialize the book detector.

        Args:
            technologies: Deprecated, kept for compatibility. Use THEMA codes instead.
            enable_isbn_lookup: Whether to call ISBN lookup API.
            thema_lookup: Optional ThemaLookup instance. If None, uses global instance.
        """
        self._technologies = technologies or []  # Kept for compatibility
        self._enable_isbn_lookup = enable_isbn_lookup
        self._thema_lookup = thema_lookup or get_thema_lookup()

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "book_detector"

    @property
    def source(self) -> ClassificationSource:
        """Return classification source."""
        return ClassificationSource.BOOK_DETECTOR

    @property
    def default_confidence(self) -> float:
        """Return default confidence (96%, or 100% with ISBN)."""
        return 0.96

    def _detect_thema_code(  # noqa: C901, PLR0911
        self,
        content: str,
        book_info: BookInfo | None,
        pdf_meta: PdfMetadata | None,
        filename: str = "",
    ) -> str | None:
        """Detect THEMA classification code from available information.

        Tries multiple sources in order of reliability:
        1. ISBN subjects (most reliable - from publisher metadata)
        2. PDF subject field
        3. Book title/description
        4. Filename keywords

        Args:
            content: Book content.
            book_info: ISBN lookup result if available.
            pdf_meta: PDF metadata if available.
            filename: Filename for pattern-based detection.

        Returns:
            THEMA code (e.g., "UMZ") or None.
        """
        # Try ISBN subjects first (most reliable - from publisher)
        if book_info and book_info.subjects:
            code = self._thema_lookup.lookup_subjects(book_info.subjects)
            if code:
                logger.debug("Detected THEMA from ISBN subjects: {}", code)
                return code

        # Try book description (often contains subject keywords)
        if book_info and book_info.description:
            code = self._thema_lookup.lookup_from_text(book_info.description)
            if code:
                logger.debug("Detected THEMA from book description: {}", code)
                return code

        # Try PDF subject field
        if pdf_meta and pdf_meta.subject:
            code = self._thema_lookup.lookup_from_text(pdf_meta.subject)
            if code:
                logger.debug("Detected THEMA from PDF subject: {}", code)
                return code

        # Try PDF title
        if pdf_meta and pdf_meta.title:
            code = self._thema_lookup.lookup_from_text(pdf_meta.title)
            if code:
                logger.debug("Detected THEMA from PDF title: {}", code)
                return code

        # Try filename (least reliable but useful fallback)
        if filename:
            code = self._thema_lookup.lookup_from_text(filename)
            if code:
                logger.debug("Detected THEMA from filename: {}", code)
                return code

        # Try content if nothing else worked
        if content:
            # Limit content to first 2000 chars for performance
            code = self._thema_lookup.lookup_from_text(content[:2000])
            if code:
                logger.debug("Detected THEMA from content: {}", code)
                return code

        return None

    def classify(  # noqa: C901, PLR0911, PLR0912, PLR0915
        self,
        content: str,
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        """Detect if the file is a technical book.

        Args:
            content: Text content from the PDF.
            metadata: File metadata including path.

        Returns:
            ClassificationResult if book detected, None otherwise.
        """
        # Only process PDFs
        if metadata is None or metadata.extension.lower() != ".pdf":
            return None

        file_path = metadata.path
        if not file_path or not file_path.exists():
            return None

        # IMPORTANT: Exclude financial/bank documents to avoid false ISBN matches
        # Bank account numbers and other financial identifiers can look like ISBNs
        if is_financial_document(content, metadata.filename):
            logger.debug("Skipping book detection for financial document: {}", file_path.name)
            return None

        # Exclude tax/government documents (reference numbers look like ISBNs)
        if is_tax_document(content, metadata.filename):
            logger.debug("Skipping book detection for tax document: {}", file_path.name)
            return None

        # Exclude insurance documents (policy/claim numbers look like ISBNs)
        if is_insurance_document(content, metadata.filename):
            logger.debug("Skipping book detection for insurance document: {}", file_path.name)
            return None

        # Exclude transport/travel documents (ticket IDs look like ISBNs)
        if is_transport_document(content, metadata.filename):
            logger.debug("Skipping book detection for transport document: {}", file_path.name)
            return None

        # Exclude telecom/contract documents (DocIDs/ContractIDs look like ISBNs)
        if is_telecom_document(content, metadata.filename):
            logger.debug("Skipping book detection for telecom document: {}", file_path.name)
            return None

        # Extract PDF metadata
        pdf_meta = extract_pdf_metadata(file_path, max_pages_for_isbn=10)
        if pdf_meta is None:
            logger.debug("Could not extract PDF metadata from {}", file_path.name)
            return None

        score = 0.0
        signals: list[str] = []
        book_info: BookInfo | None = None
        suggested_name: str | None = None

        # Signal 1: ISBN (highest confidence)
        # Try all ISBNs found in the PDF to find one that matches the filename
        if pdf_meta.isbns:
            signals.append(f"isbns_found={len(pdf_meta.isbns)}")

            if self._enable_isbn_lookup:
                # Use shared function to find matching ISBN
                book_info, matched_isbn = find_matching_book_info(
                    pdf_meta.isbns,
                    metadata.filename,
                    require_coherence=True,
                )

                if book_info and matched_isbn:
                    signals.append(f"isbn={matched_isbn}")
                    signals.append("isbn_lookup=success")
                    score = 1.0
                    if book_info.title:
                        suggested_name = sanitize_title(book_info.title)
                else:
                    # No ISBN matched the filename - use first ISBN as fallback
                    # but don't trust the lookup metadata
                    signals.append(f"isbn={pdf_meta.isbn}")
                    signals.append("isbn_lookup=no_match")
                    score = 0.5  # Lower confidence - ISBN exists but doesn't match
                    logger.info(
                        "No ISBN matched filename '{}' out of {} candidates",
                        metadata.filename,
                        len(pdf_meta.isbns),
                    )
            else:
                # ISBN lookup disabled - just note presence
                signals.append(f"isbn={pdf_meta.isbn}")
                score = 0.9  # ISBN alone is strong indicator

        # Signal 2: PDF metadata (if not already at max score)
        if score < 1.0:
            # Page count
            if pdf_meta.page_count and pdf_meta.page_count >= MIN_PAGES_FOR_BOOK:
                score += 0.2
                signals.append(f"pages={pdf_meta.page_count}")

            # Creator tool (LaTeX, InDesign = likely book)
            if pdf_meta.creator and is_book_creator(pdf_meta.creator):
                score += 0.15
                signals.append("creator=book_tool")

            # Title keywords
            if pdf_meta.title and contains_book_keywords(pdf_meta.title):
                score += 0.2
                signals.append("title=book_keywords")

        # Signal 3: Content structure
        if score < 1.0:
            structure_score = score_book_structure(content)
            if structure_score > 0:
                score += structure_score * 0.3
                signals.append(f"structure={structure_score:.2f}")

        # Signal 4: File size
        if score < 1.0 and pdf_meta.file_size_mb >= MIN_SIZE_MB_FOR_BOOK:
            score += 0.15
            signals.append(f"size={pdf_meta.file_size_mb:.1f}MB")

        # Check against threshold
        if score < DETECTION_THRESHOLD:
            logger.debug(
                "Book score %.2f below threshold %.2f for %s",
                score,
                DETECTION_THRESHOLD,
                file_path.name,
            )
            return None

        # Detect THEMA classification code
        thema_code = self._detect_thema_code(
            content, book_info, pdf_meta, filename=metadata.filename
        )

        # Build category path using THEMA hierarchy
        if thema_code:
            signals.append(f"thema={thema_code}")
            code_info = self._thema_lookup.get_code_info(thema_code)
            if code_info:
                signals.append(f"thema_desc={code_info.CodeDescription[:30]}")
            category = self._thema_lookup.build_para_path(thema_code)
        else:
            # Fallback to generic books category
            thema_code = "U"  # Default to Computing/IT
            signals.append("thema=U(default)")
            category = "3_Resources/livres/Informatique"

        # Determine suggested name if not already set from ISBN
        if not suggested_name and score >= SMART_RENAME_THRESHOLD and pdf_meta.title:
            suggested_name = sanitize_title(pdf_meta.title)

        # Cap confidence
        confidence_value = min(score, 1.0) if score >= 1.0 else 0.92

        logger.info(
            "Detected book: {} → {} (confidence={:.2f}, signals={})",
            file_path.name,
            category,
            confidence_value,
            signals,
        )

        result = ClassificationResult(
            category=category,
            confidence=Confidence(
                value=confidence_value,
                source=self.source,
            ),
            route_name="livres",
            extracted_params={
                "thema_code": thema_code,
            },
        )

        # Store suggested name in extracted_params for smart rename
        if suggested_name:
            result.extracted_params["suggested_name"] = suggested_name

        return result
