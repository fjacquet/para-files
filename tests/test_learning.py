"""Tests for the learning module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from para_files.learning.feedback_tracker import CorrectionRecord, FeedbackTracker
from para_files.learning.pattern_extractor import PatternExtractor, PatternSuggestion


class TestCorrectionRecord:
    """Tests for CorrectionRecord dataclass."""

    def test_create_record(self) -> None:
        """Test creating a correction record."""
        record = CorrectionRecord(
            file_path="/path/to/file.pdf",
            filename="file.pdf",
            original_category="4_Archives/divers",
            corrected_category="4_Archives/10y_fiscalite/2024",
            original_confidence=0.75,
        )
        assert record.file_path == "/path/to/file.pdf"
        assert record.filename == "file.pdf"
        assert record.original_category == "4_Archives/divers"
        assert record.corrected_category == "4_Archives/10y_fiscalite/2024"
        assert record.original_confidence == 0.75
        assert record.source == "unknown"

    def test_to_dict(self) -> None:
        """Test converting record to dictionary."""
        record = CorrectionRecord(
            file_path="/path/to/file.pdf",
            filename="file.pdf",
            original_category=None,
            corrected_category="4_Archives/10y_fiscalite/2024",
            original_confidence=0.0,
        )
        data = record.to_dict()
        assert data["file_path"] == "/path/to/file.pdf"
        assert data["filename"] == "file.pdf"
        assert data["original_category"] is None
        assert data["corrected_category"] == "4_Archives/10y_fiscalite/2024"

    def test_from_dict(self) -> None:
        """Test creating record from dictionary."""
        data = {
            "file_path": "/path/to/file.pdf",
            "filename": "file.pdf",
            "original_category": "divers",
            "corrected_category": "fiscalite",
            "original_confidence": 0.5,
            "content_preview": "Some content",
            "metadata": {"author": "Test"},
            "timestamp": "2024-01-01T12:00:00",
            "source": "semantic",
        }
        record = CorrectionRecord.from_dict(data)
        assert record.file_path == "/path/to/file.pdf"
        assert record.metadata == {"author": "Test"}
        assert record.source == "semantic"


class TestFeedbackTracker:
    """Tests for FeedbackTracker."""

    def test_record_correction(self, tmp_path: Path) -> None:
        """Test recording a correction."""
        feedback_file = tmp_path / "feedback.json"
        tracker = FeedbackTracker(feedback_file)

        record = tracker.record_correction(
            file_path=Path("/test/file.pdf"),
            original_category="divers",
            corrected_category="fiscalite",
            original_confidence=0.5,
            source="semantic",
        )

        assert record.file_path == "/test/file.pdf"
        assert record.corrected_category == "fiscalite"
        assert feedback_file.exists()

    def test_get_corrections(self, tmp_path: Path) -> None:
        """Test retrieving corrections."""
        feedback_file = tmp_path / "feedback.json"
        tracker = FeedbackTracker(feedback_file)

        # Record some corrections
        tracker.record_correction(
            file_path=Path("/test/file1.pdf"),
            original_category="divers",
            corrected_category="fiscalite",
        )
        tracker.record_correction(
            file_path=Path("/test/file2.pdf"),
            original_category="divers",
            corrected_category="sante",
        )

        corrections = tracker.get_corrections()
        assert len(corrections) == 2

        # Filter by category
        fiscal_corrections = tracker.get_corrections(category="fiscalite")
        assert len(fiscal_corrections) == 1
        assert fiscal_corrections[0].file_path == "/test/file1.pdf"

    def test_persistence(self, tmp_path: Path) -> None:
        """Test that corrections persist across instances."""
        feedback_file = tmp_path / "feedback.json"

        # First tracker instance
        tracker1 = FeedbackTracker(feedback_file)
        tracker1.record_correction(
            file_path=Path("/test/file.pdf"),
            original_category="divers",
            corrected_category="fiscalite",
        )

        # New tracker instance should load existing data
        tracker2 = FeedbackTracker(feedback_file)
        corrections = tracker2.get_corrections()
        assert len(corrections) == 1
        assert corrections[0].corrected_category == "fiscalite"

    def test_get_correction_stats(self, tmp_path: Path) -> None:
        """Test getting correction statistics."""
        feedback_file = tmp_path / "feedback.json"
        tracker = FeedbackTracker(feedback_file)

        tracker.record_correction(
            file_path=Path("/test/file1.pdf"),
            original_category="divers",
            corrected_category="fiscalite",
            source="semantic",
        )
        tracker.record_correction(
            file_path=Path("/test/file2.pdf"),
            original_category="divers",
            corrected_category="fiscalite",
            source="semantic",
        )
        tracker.record_correction(
            file_path=Path("/test/file3.pdf"),
            original_category="sante",
            corrected_category="fiscalite",
            source="rules",
        )

        stats = tracker.get_correction_stats()
        assert stats["total_corrections"] == 3
        assert stats["unique_files"] == 3
        assert stats["categories_corrected_to"]["fiscalite"] == 3
        assert stats["sources_corrected"]["semantic"] == 2
        assert stats["sources_corrected"]["rules"] == 1

    def test_clear(self, tmp_path: Path) -> None:
        """Test clearing feedback history."""
        feedback_file = tmp_path / "feedback.json"
        tracker = FeedbackTracker(feedback_file)

        tracker.record_correction(
            file_path=Path("/test/file.pdf"),
            original_category="divers",
            corrected_category="fiscalite",
        )

        assert feedback_file.exists()
        tracker.clear()

        assert not feedback_file.exists()
        assert len(tracker.get_corrections()) == 0


class TestPatternSuggestion:
    """Tests for PatternSuggestion dataclass."""

    def test_to_dict(self) -> None:
        """Test converting suggestion to dictionary."""
        suggestion = PatternSuggestion(
            pattern_type="issuer",
            pattern="SwissLife",
            category="4_Archives/10y_assurances",
            confidence=0.8,
            occurrences=5,
            examples=["SwissLife-2024.pdf"],
        )
        data = suggestion.to_dict()
        assert data["pattern_type"] == "issuer"
        assert data["pattern"] == "SwissLife"
        assert data["confidence"] == 0.8


class TestPatternExtractor:
    """Tests for PatternExtractor."""

    def _create_tracker_with_corrections(
        self,
        tmp_path: Path,
        corrections: list[dict[str, Any]],
    ) -> FeedbackTracker:
        """Helper to create a tracker with preset corrections."""
        feedback_file = tmp_path / "feedback.json"
        tracker = FeedbackTracker(feedback_file)

        for corr in corrections:
            tracker.record_correction(
                file_path=Path(corr.get("file_path", "/test/file.pdf")),
                original_category=corr.get("original_category"),
                corrected_category=corr["corrected_category"],
                content_preview=corr.get("content_preview", ""),
                metadata=corr.get("metadata", {}),
            )

        return tracker

    def test_extract_issuer_patterns(self, tmp_path: Path) -> None:
        """Test extracting issuer patterns from corrections."""
        corrections = [
            {
                "file_path": "/test/SwissLife-2024.pdf",
                "corrected_category": "assurances",
                "metadata": {"author": "SwissLife"},
            },
            {
                "file_path": "/test/SwissLife-2023.pdf",
                "corrected_category": "assurances",
                "metadata": {"author": "SwissLife"},
            },
        ]
        tracker = self._create_tracker_with_corrections(tmp_path, corrections)
        extractor = PatternExtractor(tracker)

        suggestions = extractor.extract_issuer_patterns(min_occurrences=2)
        assert len(suggestions) >= 1
        issuer_patterns = [s.pattern for s in suggestions]
        assert "SwissLife" in issuer_patterns

    def test_extract_keyword_patterns(self, tmp_path: Path) -> None:
        """Test extracting keyword patterns from corrections."""
        corrections = [
            {
                "file_path": "/test/facture1.pdf",
                "corrected_category": "factures",
                "content_preview": "Facture numéro 12345 pour services rendus",
            },
            {
                "file_path": "/test/facture2.pdf",
                "corrected_category": "factures",
                "content_preview": "Facture client entreprise ABC",
            },
            {
                "file_path": "/test/facture3.pdf",
                "corrected_category": "factures",
                "content_preview": "Facture mensuelle abonnement",
            },
        ]
        tracker = self._create_tracker_with_corrections(tmp_path, corrections)
        extractor = PatternExtractor(tracker)

        suggestions = extractor.extract_keyword_patterns(min_occurrences=2)
        keywords = [s.pattern for s in suggestions]
        assert "facture" in keywords

    def test_extract_filename_patterns(self, tmp_path: Path) -> None:
        """Test extracting filename patterns from corrections."""
        corrections = [
            {
                "file_path": "/test/2024-01-01_facture.pdf",
                "corrected_category": "factures",
            },
            {
                "file_path": "/test/2024-02-15_facture.pdf",
                "corrected_category": "factures",
            },
            {
                "file_path": "/test/2024-03-20_facture.pdf",
                "corrected_category": "factures",
            },
        ]
        tracker = self._create_tracker_with_corrections(tmp_path, corrections)
        extractor = PatternExtractor(tracker)

        suggestions = extractor.extract_filename_patterns(min_occurrences=2)
        # Should find date pattern
        pattern_types = [s.pattern_type for s in suggestions]
        assert "filename_pattern" in pattern_types or "filename_prefix" in pattern_types

    def test_get_all_suggestions(self, tmp_path: Path) -> None:
        """Test getting all suggestions at once."""
        corrections = [
            {
                "file_path": "/test/SwissLife-2024.pdf",
                "corrected_category": "assurances",
                "metadata": {"author": "SwissLife"},
                "content_preview": "Assurance vie police numéro 12345",
            },
            {
                "file_path": "/test/SwissLife-2023.pdf",
                "corrected_category": "assurances",
                "metadata": {"author": "SwissLife"},
                "content_preview": "Assurance habitation contrat",
            },
        ]
        tracker = self._create_tracker_with_corrections(tmp_path, corrections)
        extractor = PatternExtractor(tracker)

        all_suggestions = extractor.get_all_suggestions(min_occurrences=2)
        assert "issuers" in all_suggestions
        assert "keywords" in all_suggestions
        assert "filenames" in all_suggestions

    def test_empty_corrections(self, tmp_path: Path) -> None:
        """Test pattern extraction with no corrections."""
        feedback_file = tmp_path / "feedback.json"
        tracker = FeedbackTracker(feedback_file)
        extractor = PatternExtractor(tracker)

        assert extractor.extract_issuer_patterns() == []
        assert extractor.extract_keyword_patterns() == []
        assert extractor.extract_filename_patterns() == []

    def test_similarity_score(self, tmp_path: Path) -> None:
        """Test string similarity calculation."""
        feedback_file = tmp_path / "feedback.json"
        tracker = FeedbackTracker(feedback_file)
        extractor = PatternExtractor(tracker)

        # Identical strings
        assert extractor.similarity_score("SwissLife", "SwissLife") == 1.0

        # Case insensitive
        assert extractor.similarity_score("swisslife", "SWISSLIFE") == 1.0

        # Similar strings
        score = extractor.similarity_score("SwissLife", "Swiss Life")
        assert score > 0.8

        # Different strings
        score = extractor.similarity_score("SwissLife", "AXA")
        assert score < 0.5
