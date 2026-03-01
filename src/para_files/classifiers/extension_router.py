"""Extension-based routing classifier for media, security, script, and exotic file types.

This classifier sits last in the pipeline (just before the LLM fallback) and acts as the
"catch-all before giving up" layer. It routes files deterministically based on their extension
when no other classifier could make a decision.
"""

from __future__ import annotations

from loguru import logger

from para_files.classifiers.base import BaseClassifier
from para_files.config import ExtensionRoutingConfig
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
)


# Mapping: extension (lowercase with dot) -> (config_attr_name, confidence)
EXTENSION_GROUPS: dict[str, tuple[str, float]] = {
    ".3gp": ("media_video_folder", 0.97),
    ".m4v": ("media_video_folder", 0.97),
    ".mp4": ("media_video_folder", 0.97),
    ".mov": ("media_video_folder", 0.97),
    ".m4a": ("media_audio_folder", 0.97),
    ".mp3": ("media_audio_folder", 0.97),
    ".gif": ("media_images_folder", 0.97),
    ".tif": ("media_images_folder", 0.97),
    ".tiff": ("media_images_folder", 0.97),
    ".psd": ("media_images_folder", 0.97),
    ".p7b": ("security_folder", 0.98),
    ".asc": ("security_folder", 0.98),
    ".kdbx": ("security_folder", 0.98),
    ".ps1": ("scripts_folder", 0.97),
    ".css": ("scripts_folder", 0.97),
    ".js": ("scripts_folder", 0.97),
    ".sh": ("scripts_folder", 0.97),
}


class ExtensionRouterClassifier(BaseClassifier):
    """Classifier that routes files deterministically based on their file extension.

    Acts as the catch-all layer just before LLM fallback. Known extensions are
    routed to appropriate permanent folders; unknown extensions go to misc.
    Files with no extension return None to let the pipeline decide.
    """

    def __init__(self, config: ExtensionRoutingConfig) -> None:
        """Initialise the classifier with folder-path configuration.

        Args:
            config: ExtensionRoutingConfig providing destination folder paths.
        """
        self._config = config

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "extension_router"

    @property
    def source(self) -> ClassificationSource:
        """Return the classification source enum value."""
        return ClassificationSource.EXTENSION_ROUTER

    @property
    def default_confidence(self) -> float:
        """Return the default confidence when this classifier matches."""
        return 0.97

    def classify(
        self,
        content: str,  # noqa: ARG002
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        """Classify a file based solely on its extension.

        Args:
            content: Text content (unused — routing is extension-only).
            metadata: File metadata providing the extension.

        Returns:
            ClassificationResult if the file has an extension (known or unknown),
            None if metadata is absent or the file has no extension.
        """
        if metadata is None:
            return None

        ext = metadata.extension.lower()

        if ext in EXTENSION_GROUPS:
            folder_attr, confidence = EXTENSION_GROUPS[ext]
            destination = getattr(self._config, folder_attr)
            logger.debug(
                "ExtensionRouter matched {ext} -> {dest} (confidence={conf})",
                ext=ext,
                dest=destination,
                conf=confidence,
            )
            return ClassificationResult(
                category=destination,
                confidence=Confidence(
                    value=confidence,
                    source=ClassificationSource.EXTENSION_ROUTER,
                ),
            )

        if ext:
            # File has an extension but it is not in the known groups — send to misc.
            destination = self._config.catchall_folder
            logger.debug(
                "ExtensionRouter catch-all for unknown extension {ext} -> {dest}",
                ext=ext,
                dest=destination,
            )
            return ClassificationResult(
                category=destination,
                confidence=Confidence(
                    value=0.80,
                    source=ClassificationSource.EXTENSION_ROUTER,
                ),
            )

        # No extension — let the pipeline decide.
        return None
