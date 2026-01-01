"""Tests for smart file renaming module."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from para_files.utils.ocr_metadata import OCRMetadata
from para_files.utils.smart_renamer import (
    build_smart_name,
    perform_rename,
    suggest_rename,
)


class TestBuildSmartName:
    """Tests for build_smart_name function."""

    def test_builds_name_with_all_components(self, tmp_path: Path) -> None:
        """Test building name with date, issuer, and type."""
        original = tmp_path / "scan_001.pdf"
        metadata = OCRMetadata(
            document_date=date(2024, 1, 15),
            issuer="Swisscom",
            doc_type="facture",
            confidence=0.8,
        )

        result = build_smart_name(metadata, original)
        assert result == "2024-01-15_swisscom_facture.pdf"

    def test_builds_name_with_date_only(self, tmp_path: Path) -> None:
        """Test building name with date only."""
        original = tmp_path / "scan_001.pdf"
        metadata = OCRMetadata(
            document_date=date(2024, 1, 15),
            confidence=0.5,
        )

        result = build_smart_name(metadata, original)
        assert result == "2024-01-15.pdf"

    def test_builds_name_with_issuer_only(self, tmp_path: Path) -> None:
        """Test building name with issuer only."""
        original = tmp_path / "scan_001.pdf"
        metadata = OCRMetadata(
            issuer="Migros",
            confidence=0.5,
        )

        result = build_smart_name(metadata, original)
        assert result == "migros.pdf"

    def test_removes_company_suffixes(self, tmp_path: Path) -> None:
        """Test that company suffixes (SA, GmbH, etc.) are removed."""
        original = tmp_path / "scan_001.pdf"
        metadata = OCRMetadata(
            issuer="Swisscom SA",
            confidence=0.5,
        )

        result = build_smart_name(metadata, original)
        assert result == "swisscom.pdf"

    def test_truncates_long_issuer(self, tmp_path: Path) -> None:
        """Test that long issuer names are truncated."""
        original = tmp_path / "scan_001.pdf"
        metadata = OCRMetadata(
            issuer="A" * 50,  # Very long name
            confidence=0.5,
        )

        result = build_smart_name(metadata, original)
        # Should be truncated to 30 chars + .pdf
        assert len(result) <= 35

    def test_returns_original_name_if_not_enough_info(self, tmp_path: Path) -> None:
        """Test that original name is returned if not enough metadata."""
        original = tmp_path / "scan_001.pdf"
        metadata = OCRMetadata(confidence=0.1)  # Low confidence, no data

        result = build_smart_name(metadata, original)
        assert result == "scan_001.pdf"

    def test_preserves_extension(self, tmp_path: Path) -> None:
        """Test that file extension is preserved."""
        original = tmp_path / "scan_001.PDF"  # Uppercase extension
        metadata = OCRMetadata(
            document_date=date(2024, 1, 15),
            confidence=0.5,
        )

        result = build_smart_name(metadata, original)
        assert result == "2024-01-15.pdf"  # Lowercased


class TestSuggestRename:
    """Tests for suggest_rename function."""

    def test_suggests_rename_with_sufficient_metadata(self, tmp_path: Path) -> None:
        """Test that rename is suggested with sufficient metadata."""
        original = tmp_path / "scan_001.pdf"
        metadata = OCRMetadata(
            document_date=date(2024, 1, 15),
            issuer="Swisscom",
            confidence=0.6,
        )

        new_name, confidence = suggest_rename(metadata, original)

        assert new_name == "2024-01-15_swisscom.pdf"
        assert confidence == 0.6

    def test_returns_none_with_insufficient_metadata(self, tmp_path: Path) -> None:
        """Test that None is returned with insufficient metadata."""
        original = tmp_path / "scan_001.pdf"
        metadata = OCRMetadata(confidence=0.1)

        new_name, confidence = suggest_rename(metadata, original)

        assert new_name is None
        assert confidence == 0.0

    def test_returns_none_if_same_as_original(self, tmp_path: Path) -> None:
        """Test that None is returned if new name equals original."""
        original = tmp_path / "2024-01-15_swisscom.pdf"
        metadata = OCRMetadata(
            document_date=date(2024, 1, 15),
            issuer="Swisscom",
            confidence=0.6,
        )

        new_name, confidence = suggest_rename(metadata, original)

        assert new_name is None
        assert confidence == 0.0


class TestPerformRename:
    """Tests for perform_rename function."""

    def test_renames_file_successfully(self, tmp_path: Path) -> None:
        """Test successful file rename."""
        original = tmp_path / "scan_001.pdf"
        original.write_text("test content")

        new_path = perform_rename(original, "facture_swisscom.pdf")

        assert new_path is not None
        assert new_path.name == "facture_swisscom.pdf"
        assert new_path.exists()
        assert not original.exists()

    def test_handles_collision_with_suffix(self, tmp_path: Path) -> None:
        """Test that collisions are handled with numeric suffix."""
        original = tmp_path / "scan_001.pdf"
        original.write_text("original")

        # Create a file that would collide
        collision = tmp_path / "facture.pdf"
        collision.write_text("existing")

        new_path = perform_rename(original, "facture.pdf")

        assert new_path is not None
        assert new_path.name == "facture_1.pdf"
        assert new_path.exists()
        assert collision.exists()  # Original collision file still exists

    def test_dry_run_does_not_rename(self, tmp_path: Path) -> None:
        """Test that dry_run mode does not actually rename."""
        original = tmp_path / "scan_001.pdf"
        original.write_text("test content")

        new_path = perform_rename(original, "facture.pdf", dry_run=True)

        assert new_path is not None
        assert new_path.name == "facture.pdf"
        assert original.exists()  # Original still exists
        assert not new_path.exists()  # New file not created

    def test_returns_none_if_file_does_not_exist(self, tmp_path: Path) -> None:
        """Test that None is returned if source file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.pdf"

        result = perform_rename(nonexistent, "new_name.pdf")

        assert result is None

    def test_handles_rename_to_same_path(self, tmp_path: Path) -> None:
        """Test renaming to the same name (no-op)."""
        original = tmp_path / "test.pdf"
        original.write_text("content")

        result = perform_rename(original, "test.pdf")

        assert result == original
        assert original.exists()
