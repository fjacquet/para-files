"""Tests for generic filename detection module."""

from __future__ import annotations

from pathlib import Path

import pytest

from para_files.utils.filename_detector import (
    get_generic_pattern_match,
    is_generic_filename,
)


class TestIsGenericFilename:
    """Tests for is_generic_filename function."""

    @pytest.mark.parametrize(
        "filename",
        [
            # Scanner output patterns
            "scan.pdf",
            "scan_001.pdf",
            "scan-123.pdf",
            "SCAN_456.pdf",
            "numérisation.pdf",
            "numérisation_001.pdf",
            "scanned.pdf",
            "scanned_001.pdf",
            # Camera/phone patterns
            "IMG_1234.pdf",
            "IMG-5678.pdf",
            "DSC_0001.pdf",
            "DSC-1234.pdf",
            "DCIM_1234.pdf",
            "photo.pdf",
            "photo_001.pdf",
            "image.pdf",
            "image_001.pdf",
            # Generic document names
            "document.pdf",
            "document_001.pdf",
            "doc_123.pdf",
            "file.pdf",
            "file_001.pdf",
            "pdf.pdf",
            "pdf_001.pdf",
            "nouveau_document.pdf",
            "new_document.pdf",
            # Timestamp-only names
            "20240101.pdf",
            "20240101120000.pdf",
            # Hex hash names
            "abcdef12.pdf",
            "1234abcd5678.pdf",
            # UUID-like names
            "12345678-1234-1234-1234-123456789abc.pdf",
            # Copy patterns
            "copy.pdf",
            "copy_001.pdf",
            "copie.pdf",
            "copie_001.pdf",
            # Untitled patterns
            "untitled.pdf",
            "untitled_001.pdf",
            "sans_titre.pdf",
            # Number-only names
            "1.pdf",
            "123.pdf",
            "9999.pdf",
            # Download patterns
            "download.pdf",
            "download_001.pdf",
            "téléchargement.pdf",
            # Attachment patterns
            "attachment.pdf",
            "attachment_001.pdf",
            "pièce_jointe.pdf",
            # Too short names
            "a.pdf",
            "ab.pdf",
            "abc.pdf",
        ],
    )
    def test_detects_generic_filenames(self, filename: str) -> None:
        """Test that generic filenames are detected."""
        assert is_generic_filename(filename) is True, f"Expected {filename} to be generic"

    @pytest.mark.parametrize(
        "filename",
        [
            # Descriptive names
            "facture_swisscom_2024.pdf",
            "bulletin_salaire_janvier_2024.pdf",
            "contrat_location.pdf",
            "rapport_annuel_2023.pdf",
            "cv_jean_dupont.pdf",
            "attestation_assurance.pdf",
            "2024-01-15_swisscom_facture.pdf",
            # Books or technical documents
            "python_programming_guide.pdf",
            "kubernetes_in_action.pdf",
            "docker_best_practices.pdf",
            # Long enough generic-looking but descriptive
            "manual_user_guide.pdf",
            "invoice_amazon.pdf",
        ],
    )
    def test_does_not_flag_descriptive_filenames(self, filename: str) -> None:
        """Test that descriptive filenames are not flagged."""
        assert is_generic_filename(filename) is False, f"Expected {filename} to be descriptive"

    def test_only_processes_pdf_files(self) -> None:
        """Test that non-PDF files are not processed."""
        assert is_generic_filename("scan_001.jpg") is False
        assert is_generic_filename("document.docx") is False
        assert is_generic_filename("image.png") is False

    def test_accepts_path_objects(self) -> None:
        """Test that Path objects are accepted."""
        assert is_generic_filename(Path("scan_001.pdf")) is True
        assert is_generic_filename(Path("facture_swisscom.pdf")) is False


class TestGetGenericPatternMatch:
    """Tests for get_generic_pattern_match function."""

    def test_returns_pattern_description(self) -> None:
        """Test that matching pattern description is returned."""
        assert get_generic_pattern_match("scan_001.pdf") == "scanner output"
        assert get_generic_pattern_match("IMG_1234.pdf") == "camera photo"
        assert get_generic_pattern_match("document.pdf") == "generic document"

    def test_returns_none_for_descriptive_names(self) -> None:
        """Test that None is returned for descriptive names."""
        assert get_generic_pattern_match("facture_swisscom.pdf") is None
        assert get_generic_pattern_match("bulletin_salaire.pdf") is None

    def test_returns_none_for_non_pdf(self) -> None:
        """Test that None is returned for non-PDF files."""
        assert get_generic_pattern_match("scan_001.jpg") is None

    def test_returns_too_short_for_short_names(self) -> None:
        """Test that 'too short' is returned for very short names."""
        assert get_generic_pattern_match("abc.pdf") == "too short"
        assert get_generic_pattern_match("x.pdf") == "too short"
