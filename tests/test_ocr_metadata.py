"""Tests for OCR metadata extraction module."""

from __future__ import annotations

from datetime import date

from conftest import macos_only

from para_files.utils.ocr_metadata import OCRMetadata, extract_metadata


class TestOCRMetadata:
    """Tests for OCRMetadata dataclass."""

    def test_has_enough_info_with_date(self) -> None:
        """Test that metadata with date has enough info."""
        meta = OCRMetadata(document_date=date(2024, 1, 15), confidence=0.5)
        assert meta.has_enough_info() is True

    def test_has_enough_info_with_issuer(self) -> None:
        """Test that metadata with issuer has enough info."""
        meta = OCRMetadata(issuer="Swisscom", confidence=0.5)
        assert meta.has_enough_info() is True

    def test_has_enough_info_requires_minimum_confidence(self) -> None:
        """Test that metadata requires minimum confidence."""
        meta = OCRMetadata(document_date=date(2024, 1, 15), confidence=0.1)
        assert meta.has_enough_info() is False

    def test_has_enough_info_empty_metadata(self) -> None:
        """Test that empty metadata does not have enough info."""
        meta = OCRMetadata()
        assert meta.has_enough_info() is False


class TestExtractMetadataDate:
    """Tests for date extraction from OCR text."""

    def test_extracts_iso_date(self) -> None:
        """Test extraction of ISO format date (YYYY-MM-DD)."""
        text = "Document dated 2024-01-15 for processing."
        meta = extract_metadata(text)
        assert meta.document_date == date(2024, 1, 15)

    def test_extracts_european_date_slash(self) -> None:
        """Test extraction of European date with slash (DD/MM/YYYY)."""
        text = "Facture du 15/01/2024 pour votre abonnement."
        meta = extract_metadata(text)
        assert meta.document_date == date(2024, 1, 15)

    def test_extracts_european_date_dot(self) -> None:
        """Test extraction of European date with dot (DD.MM.YYYY)."""
        text = "Rechnung vom 15.01.2024 für Ihre Bestellung."
        meta = extract_metadata(text)
        assert meta.document_date == date(2024, 1, 15)

    def test_extracts_french_text_date(self) -> None:
        """Test extraction of French text date (15 janvier 2024)."""
        text = "Ce document a été établi le 15 janvier 2024."
        meta = extract_metadata(text)
        assert meta.document_date == date(2024, 1, 15)

    def test_extracts_english_text_date(self) -> None:
        """Test extraction of English text date (January 15, 2024)."""
        text = "This document was created on January 15, 2024."
        meta = extract_metadata(text)
        assert meta.document_date == date(2024, 1, 15)

    def test_prefers_header_date(self) -> None:
        """Test that date in header area is preferred."""
        # Date in header should be found
        text = "Date: 2024-06-01\n" + ("x" * 1000) + "2020-01-01"
        meta = extract_metadata(text)
        assert meta.document_date == date(2024, 6, 1)

    def test_rejects_future_dates(self) -> None:
        """Test that future dates are rejected."""
        text = "Date: 2099-12-31"
        meta = extract_metadata(text)
        # Date should be rejected as it's in the future
        assert meta.document_date is None

    def test_rejects_very_old_dates(self) -> None:
        """Test that very old dates are rejected."""
        text = "Date: 1950-01-01"
        meta = extract_metadata(text)
        # Date should be rejected as it's before 1990
        assert meta.document_date is None


class TestExtractMetadataDocType:
    """Tests for document type extraction from OCR text."""

    def test_detects_invoice(self) -> None:
        """Test detection of invoice document type."""
        text = "FACTURE N° 12345\nMontant total TTC: 150.00 CHF"
        meta = extract_metadata(text)
        assert meta.doc_type == "facture"

    def test_detects_payslip(self) -> None:
        """Test detection of payslip document type."""
        text = "BULLETIN DE PAIE\nSalaire brut: 5000.00 CHF"
        meta = extract_metadata(text)
        assert meta.doc_type == "salaire"

    def test_detects_bank_statement(self) -> None:
        """Test detection of bank statement document type."""
        text = "RELEVÉ DE COMPTE\nPériode du 01.01.2024 au 31.01.2024"
        meta = extract_metadata(text)
        assert meta.doc_type == "releve"

    def test_detects_contract(self) -> None:
        """Test detection of contract document type."""
        text = "CONTRAT DE LOCATION\nEntre les soussignés..."
        meta = extract_metadata(text)
        assert meta.doc_type == "contrat"

    def test_detects_certificate(self) -> None:
        """Test detection of certificate/attestation document type."""
        text = "ATTESTATION\nNous certifions que M. Dupont..."
        meta = extract_metadata(text)
        assert meta.doc_type == "attestation"


class TestExtractMetadataConfidence:
    """Tests for confidence scoring in metadata extraction."""

    def test_empty_text_returns_zero_confidence(self) -> None:
        """Test that empty text returns zero confidence."""
        meta = extract_metadata("")
        assert meta.confidence == 0.0

    def test_short_text_returns_zero_confidence(self) -> None:
        """Test that very short text returns zero confidence."""
        meta = extract_metadata("Too short")
        assert meta.confidence == 0.0

    def test_confidence_increases_with_more_data(self) -> None:
        """Test that confidence increases with more extracted data."""
        # Just date (need minimum text length)
        meta1 = extract_metadata("Document daté du 2024-01-15 pour votre information.")

        # Date + doc type
        meta2 = extract_metadata("FACTURE du 2024-01-15 - Montant total TTC: 100.00 CHF")

        # More data should generally lead to higher confidence
        assert meta1.confidence > 0
        assert meta2.confidence >= meta1.confidence


class TestExtractMetadataIntegration:
    """Integration tests for complete metadata extraction."""

    def test_extracts_complete_invoice_metadata(self) -> None:
        """Test extraction of complete invoice metadata."""
        text = """
        Swisscom SA
        FACTURE N° 12345
        Date: 15 janvier 2024

        Montant total TTC: 150.00 CHF
        Net à payer: 150.00 CHF
        """
        meta = extract_metadata(text)

        assert meta.document_date == date(2024, 1, 15)
        assert meta.doc_type == "facture"
        assert meta.confidence > 0.3

    def test_handles_mixed_language_content(self) -> None:
        """Test handling of mixed language content."""
        text = """
        Invoice / Facture / Rechnung
        Date: 2024-01-15
        Amount / Montant: 100.00 CHF
        """
        meta = extract_metadata(text)

        assert meta.document_date == date(2024, 1, 15)
        assert meta.doc_type == "facture"
