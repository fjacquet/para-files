"""Abstract base classifier for the 5-signal pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod

from para_files.types import ClassificationResult, ClassificationSource, FileMetadata


class BaseClassifier(ABC):
    """Abstract base for all classification signals.

    Each classifier in the pipeline implements this interface,
    returning a ClassificationResult if it can classify the content,
    or None if it cannot (allowing the next classifier to try).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return classifier name for logging/debugging."""

    @property
    @abstractmethod
    def source(self) -> ClassificationSource:
        """Return the classification source enum value."""

    @property
    @abstractmethod
    def default_confidence(self) -> float:
        """Return the default confidence when this classifier matches."""

    @abstractmethod
    def classify(
        self,
        content: str,
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        """Attempt to classify content.

        Args:
            content: Text content to classify (may be filename, file content, etc.).
            metadata: Optional file metadata for additional context.

        Returns:
            ClassificationResult if classification is possible, None otherwise.
        """
