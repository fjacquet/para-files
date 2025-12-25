"""Signal 1: Validated database classifier (100% confidence).

Looks up manual sender/issuer to category mappings from a validated database.
"""

from __future__ import annotations

import json
from pathlib import Path

from para_files.classifiers.base import BaseClassifier
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
)


class ValidatedDBClassifier(BaseClassifier):
    """Signal 1: Manual validated mappings (100% confidence).

    Uses a JSON database of manually validated sender→category mappings.
    This is the highest confidence signal because mappings are human-verified.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize with optional path to validated mappings database.

        Args:
            db_path: Path to JSON file with sender→category mappings.
        """
        self._db_path = db_path
        self._mappings: dict[str, str] = {}

        if db_path and db_path.exists():
            self._load_db(db_path)

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "validated_db"

    @property
    def source(self) -> ClassificationSource:
        """Return classification source."""
        return ClassificationSource.VALIDATED_DB

    @property
    def default_confidence(self) -> float:
        """Return default confidence (100%)."""
        return 1.0

    def _load_db(self, db_path: Path) -> None:
        """Load validated mappings from JSON file.

        Expected format:
        {
            "mappings": {
                "sender@example.com": "4_Archives/factures/2025/_Cloud/Example",
                "invoice@company.com": "4_Archives/factures/2025/_Cloud/Company"
            }
        }
        """
        with db_path.open(encoding="utf-8") as f:
            data = json.load(f)
            self._mappings = data.get("mappings", {})

    def add_mapping(self, sender: str, category: str) -> None:
        """Add a validated mapping.

        Args:
            sender: Sender identifier (email, issuer name, etc.).
            category: Target category path.
        """
        self._mappings[sender.lower()] = category

    def save_db(self, db_path: Path | None = None) -> None:
        """Save mappings to JSON file.

        Args:
            db_path: Path to save to (uses original path if not specified).
        """
        path = db_path or self._db_path
        if not path:
            msg = "No database path specified"
            raise ValueError(msg)

        with path.open("w", encoding="utf-8") as f:
            json.dump({"mappings": self._mappings}, f, indent=2, ensure_ascii=False)

    def classify(
        self,
        content: str,
        _metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        """Check if content matches a validated mapping.

        Searches for known senders/issuers in the content.

        Args:
            content: Text content to classify.
            _metadata: File metadata (unused by this classifier).

        Returns:
            ClassificationResult if a mapping is found, None otherwise.
        """
        content_lower = content.lower()

        # Check each validated sender
        for sender, category in self._mappings.items():
            if sender in content_lower:
                return ClassificationResult(
                    category=category,
                    confidence=Confidence(
                        value=self.default_confidence,
                        source=self.source,
                    ),
                    extracted_params={"validated_sender": sender},
                )

        return None
