"""OCR text extraction using Apple Vision Framework.

Uses macOS Vision Framework for on-device OCR with Apple Neural Engine.
Falls back gracefully when Vision Framework is not available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field


# Supported image extensions for OCR
OCR_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".heic",
        ".heif",
        ".tiff",
        ".tif",
        ".bmp",
        ".gif",
        ".webp",
    }
)

# Confidence threshold for text recognition
_MIN_CONFIDENCE = 0.5

# Preview text length
_PREVIEW_LENGTH = 500


class OCRResult(BaseModel):
    """Result of OCR text extraction."""

    text: str = Field(description="Extracted text content")
    confidence: float = Field(description="Average confidence score (0-1)")
    word_count: int = Field(description="Number of words extracted")
    language: str | None = Field(default=None, description="Detected language code")

    @property
    def preview(self) -> str:
        """Return first 500 characters as preview."""
        if len(self.text) <= _PREVIEW_LENGTH:
            return self.text
        return self.text[:_PREVIEW_LENGTH] + "..."


def is_vision_available() -> bool:
    """Check if Vision Framework is available (macOS only)."""
    available = False
    try:
        import Vision  # noqa: F401

        available = True
    except ImportError:
        pass
    return available


def _load_cg_image(image_path: Path) -> Any | None:
    """Load image as CGImage using Quartz.

    Args:
        image_path: Path to the image file.

    Returns:
        CGImage object or None if loading failed.
    """
    from Cocoa import NSURL
    from Quartz import (
        CGImageSourceCopyPropertiesAtIndex,
        CGImageSourceCreateImageAtIndex,
        CGImageSourceCreateWithURL,
    )

    image_url = NSURL.fileURLWithPath_(str(image_path))
    image_source = CGImageSourceCreateWithURL(image_url, None)

    if image_source is None:
        logger.debug("Failed to create image source for: {}", image_path)
        return None

    properties = CGImageSourceCopyPropertiesAtIndex(image_source, 0, None)
    if properties is None:
        logger.debug("Failed to get image properties for: {}", image_path)
        return None

    cg_image = CGImageSourceCreateImageAtIndex(image_source, 0, None)
    if cg_image is None:
        logger.debug("Failed to create CGImage for: {}", image_path)
        return None

    return cg_image


def _perform_ocr_request(cg_image: Any, image_path: Path) -> list[Any] | None:
    """Perform OCR request on a CGImage.

    Args:
        cg_image: The CGImage to process.
        image_path: Path for logging purposes.

    Returns:
        List of VNRecognizedTextObservation results or None.
    """
    import Vision

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(True)

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)

    success = handler.performRequests_error_([request], None)
    if not success:
        logger.debug("OCR request failed for: {}", image_path)
        return None

    results = request.results()
    if not results:
        logger.debug("No text found in image: {}", image_path)
        return None

    return list(results)


def _extract_text_from_results(
    results: list[Any],
) -> tuple[str, float] | None:
    """Extract text and confidence from OCR results.

    Args:
        results: List of VNRecognizedTextObservation objects.

    Returns:
        Tuple of (text, average_confidence) or None if no valid text.
    """
    text_parts = []
    confidences = []

    for observation in results:
        candidates = observation.topCandidates_(1)
        if candidates:
            candidate = candidates[0]
            conf = candidate.confidence()
            if conf >= _MIN_CONFIDENCE:
                text_parts.append(candidate.string())
                confidences.append(conf)

    if not text_parts:
        return None

    full_text = "\n".join(text_parts)
    avg_confidence = sum(confidences) / len(confidences)
    return full_text, avg_confidence


def _extract_text_vision(image_path: Path) -> tuple[str, float] | None:
    """Extract text using Vision Framework.

    Args:
        image_path: Path to the image file.

    Returns:
        Tuple of (extracted_text, average_confidence) or None if failed.
    """
    try:
        cg_image = _load_cg_image(image_path)
        if cg_image is None:
            return None

        results = _perform_ocr_request(cg_image, image_path)
        if results is None:
            return None

    except Exception:  # noqa: BLE001
        logger.exception("Vision Framework OCR failed for: {}", image_path)
        return None

    return _extract_text_from_results(results)


def extract_text(
    file_path: Path,
    max_chars: int = 10000,
) -> OCRResult | None:
    """Extract text from an image using OCR.

    Args:
        file_path: Path to the image file.
        max_chars: Maximum characters to extract.

    Returns:
        OCRResult if extraction succeeds, None otherwise.
    """
    if not is_vision_available():
        logger.debug("Vision Framework not available")
        return None

    # Check if file extension is supported
    ext = file_path.suffix.lower()
    if ext not in OCR_EXTENSIONS:
        logger.debug("Unsupported extension for OCR: {}", ext)
        return None

    if not file_path.exists():
        logger.debug("File does not exist: {}", file_path)
        return None

    result = _extract_text_vision(file_path)
    if result is None:
        return None

    text, confidence = result

    # Truncate if needed
    if len(text) > max_chars:
        text = text[:max_chars]

    return OCRResult(
        text=text,
        confidence=confidence,
        word_count=len(text.split()),
        language=None,  # Could be detected with VNRecognizeTextRequest
    )


def _extract_regions_from_results(
    results: list[Any],
) -> list[dict[str, Any]] | None:
    """Extract text regions with bounding boxes from OCR results.

    Args:
        results: List of VNRecognizedTextObservation objects.

    Returns:
        List of region dicts or None if no regions found.
    """
    regions = []
    for observation in results:
        candidates = observation.topCandidates_(1)
        if candidates:
            candidate = candidates[0]
            bbox = observation.boundingBox()
            regions.append(
                {
                    "text": candidate.string(),
                    "confidence": candidate.confidence(),
                    "bounds": {
                        "x": bbox.origin.x,
                        "y": bbox.origin.y,
                        "width": bbox.size.width,
                        "height": bbox.size.height,
                    },
                }
            )

    return regions if regions else None


def extract_text_with_regions(
    file_path: Path,
) -> list[dict[str, Any]] | None:
    """Extract text with bounding box regions.

    Returns text blocks with their positions for document analysis.

    Args:
        file_path: Path to the image file.

    Returns:
        List of dicts with 'text', 'confidence', 'bounds' keys, or None.
    """
    if not is_vision_available():
        return None

    ext = file_path.suffix.lower()
    if ext not in OCR_EXTENSIONS or not file_path.exists():
        return None

    try:
        cg_image = _load_cg_image(file_path)
        if cg_image is None:
            return None

        results = _perform_ocr_request(cg_image, file_path)
        if results is None:
            return None

    except Exception:  # noqa: BLE001
        logger.exception("Vision Framework region extraction failed for: {}", file_path)
        return None

    return _extract_regions_from_results(results)
