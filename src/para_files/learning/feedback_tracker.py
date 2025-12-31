"""Feedback tracker for learning from user corrections.

This module tracks classification corrections to enable pattern learning
and continuous improvement of the classification system.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger


# Default feedback file location
DEFAULT_FEEDBACK_FILE = Path.home() / ".config" / "para-files" / "feedback_history.json"


@dataclass
class CorrectionRecord:
    """Record of a classification correction.

    Attributes:
        file_path: Original file path.
        filename: Filename for pattern extraction.
        original_category: What the system classified as.
        corrected_category: What the user corrected to.
        original_confidence: Confidence of original classification.
        content_preview: First N characters of content for pattern analysis.
        metadata: Extracted file metadata (author, title, etc.).
        timestamp: When the correction was made.
        source: Which classifier made the original classification.
    """

    file_path: str
    filename: str
    original_category: str | None
    corrected_category: str
    original_confidence: float
    content_preview: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    source: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CorrectionRecord:
        """Create from dictionary."""
        return cls(**data)


class FeedbackTracker:
    """Track user corrections for learning.

    Stores correction history in a JSON file for later analysis
    by the pattern extractor.
    """

    def __init__(self, feedback_file: Path | None = None) -> None:
        """Initialize the feedback tracker.

        Args:
            feedback_file: Path to the feedback history file.
        """
        self._feedback_file = feedback_file or DEFAULT_FEEDBACK_FILE
        self._corrections: list[CorrectionRecord] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Load corrections from file if not already loaded."""
        if self._loaded:
            return

        if self._feedback_file.exists():
            try:
                with self._feedback_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._corrections = [
                        CorrectionRecord.from_dict(record) for record in data.get("corrections", [])
                    ]
                logger.debug("Loaded %d correction records", len(self._corrections))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load feedback history: %s", e)
                self._corrections = []
        else:
            self._corrections = []

        self._loaded = True

    def _save(self) -> None:
        """Save corrections to file."""
        self._feedback_file.parent.mkdir(parents=True, exist_ok=True)
        with self._feedback_file.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": "1.0",
                    "corrections": [c.to_dict() for c in self._corrections],
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        logger.debug("Saved %d correction records", len(self._corrections))

    def record_correction(  # noqa: PLR0913
        self,
        file_path: Path,
        original_category: str | None,
        corrected_category: str,
        *,
        original_confidence: float = 0.0,
        content_preview: str = "",
        metadata: dict[str, Any] | None = None,
        source: str = "unknown",
    ) -> CorrectionRecord:
        """Record a classification correction.

        Args:
            file_path: Path to the file.
            original_category: Original classification (None if unclassified).
            corrected_category: User's corrected classification.
            original_confidence: Confidence of original classification.
            content_preview: Preview of file content.
            metadata: File metadata.
            source: Which classifier made the original classification.

        Returns:
            The created correction record.
        """
        self._ensure_loaded()

        record = CorrectionRecord(
            file_path=str(file_path),
            filename=file_path.name,
            original_category=original_category,
            corrected_category=corrected_category,
            original_confidence=original_confidence,
            content_preview=content_preview[:500] if content_preview else "",
            metadata=metadata or {},
            source=source,
        )

        self._corrections.append(record)
        self._save()

        logger.info(
            "Recorded correction: %s -> %s (was: %s)",
            file_path.name,
            corrected_category,
            original_category or "unclassified",
        )

        return record

    def get_corrections(
        self,
        *,
        category: str | None = None,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[CorrectionRecord]:
        """Get correction records with optional filtering.

        Args:
            category: Filter by corrected category.
            since: Filter to corrections after this datetime.
            limit: Maximum number of records to return.

        Returns:
            List of correction records.
        """
        self._ensure_loaded()

        results = self._corrections

        if category:
            results = [c for c in results if c.corrected_category == category]

        if since:
            since_iso = since.isoformat()
            results = [c for c in results if c.timestamp >= since_iso]

        if limit:
            results = results[-limit:]

        return results

    def get_corrections_by_original(
        self,
        original_category: str | None,
    ) -> list[CorrectionRecord]:
        """Get all corrections from a specific original classification.

        Useful for finding patterns in misclassifications.

        Args:
            original_category: The original (wrong) category.

        Returns:
            List of corrections from that category.
        """
        self._ensure_loaded()
        return [c for c in self._corrections if c.original_category == original_category]

    def get_correction_stats(self) -> dict[str, Any]:
        """Get statistics about corrections.

        Returns:
            Dictionary with correction statistics.
        """
        self._ensure_loaded()

        if not self._corrections:
            return {
                "total_corrections": 0,
                "unique_files": 0,
                "categories_corrected_to": {},
                "sources_corrected": {},
            }

        categories: dict[str, int] = {}
        sources: dict[str, int] = {}

        for c in self._corrections:
            categories[c.corrected_category] = categories.get(c.corrected_category, 0) + 1
            sources[c.source] = sources.get(c.source, 0) + 1

        return {
            "total_corrections": len(self._corrections),
            "unique_files": len({c.file_path for c in self._corrections}),
            "categories_corrected_to": categories,
            "sources_corrected": sources,
        }

    def clear(self) -> None:
        """Clear all correction records."""
        self._corrections = []
        self._loaded = True
        if self._feedback_file.exists():
            self._feedback_file.unlink()
        logger.info("Cleared feedback history")
