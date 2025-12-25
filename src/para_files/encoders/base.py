"""Abstract base class for encoders."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEncoder(ABC):
    """Abstract base encoder for semantic routing."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return encoder name."""

    @abstractmethod
    def __call__(self, texts: list[str]) -> list[list[float]]:
        """Encode texts to embeddings.

        Args:
            texts: List of texts to encode.

        Returns:
            List of embedding vectors.
        """
