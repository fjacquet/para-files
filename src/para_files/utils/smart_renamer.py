"""Smart file renaming based on OCR metadata.

This module builds descriptive filenames from extracted OCR metadata,
following the format: {YYYY-MM-DD}_{issuer}_{type}.pdf
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from para_files.utils.filename_sanitizer import sanitize_filename


if TYPE_CHECKING:
    from para_files.utils.ocr_metadata import OCRMetadata

# Maximum component lengths to avoid excessively long filenames
_MAX_ISSUER_LENGTH = 30
_MAX_TYPE_LENGTH = 20
_MAX_TOTAL_LENGTH = 100
_MAX_COLLISION_RETRIES = 100


def _normalize_issuer(issuer: str) -> str:
    """Normalize issuer name for filename use.

    Args:
        issuer: Raw issuer name

    Returns:
        Normalized, lowercase issuer name suitable for filenames
    """
    # Convert to lowercase
    normalized = issuer.lower()

    # Remove common suffixes that add no value
    suffixes_to_remove = [" sa", " sàrl", " gmbh", " ag", " inc", " ltd", " sas"]
    for suffix in suffixes_to_remove:
        normalized = normalized.removesuffix(suffix)

    # Truncate if too long
    if len(normalized) > _MAX_ISSUER_LENGTH:
        normalized = normalized[:_MAX_ISSUER_LENGTH].rstrip("-_ ")

    # Sanitize for filesystem
    return sanitize_filename(normalized)


def _normalize_doc_type(doc_type: str) -> str:
    """Normalize document type for filename use.

    Args:
        doc_type: Raw document type

    Returns:
        Normalized document type suitable for filenames
    """
    normalized = doc_type.lower()

    # Truncate if too long
    if len(normalized) > _MAX_TYPE_LENGTH:
        normalized = normalized[:_MAX_TYPE_LENGTH].rstrip("-_ ")

    return sanitize_filename(normalized)


def build_smart_name(
    metadata: OCRMetadata,
    original_path: Path,
    *,
    preserve_extension: bool = True,
) -> str:
    """Build a descriptive filename from OCR metadata.

    Format: {YYYY-MM-DD}_{issuer}_{type}.pdf

    Missing components are omitted (not replaced with placeholders).
    At minimum, needs date or issuer to generate a meaningful name.

    Args:
        metadata: Extracted OCR metadata
        original_path: Original file path (for extension and fallback)
        preserve_extension: Whether to preserve the original extension

    Returns:
        New filename or original filename if not enough metadata
    """
    if not metadata.has_enough_info():
        logger.debug(f"Insufficient metadata for smart rename: {original_path.name}")
        return original_path.name

    parts: list[str] = []

    # Date component (YYYY-MM-DD)
    if metadata.document_date:
        parts.append(metadata.document_date.strftime("%Y-%m-%d"))

    # Issuer component
    if metadata.issuer:
        normalized_issuer = _normalize_issuer(metadata.issuer)
        if normalized_issuer:
            parts.append(normalized_issuer)

    # Document type component
    if metadata.doc_type:
        normalized_type = _normalize_doc_type(metadata.doc_type)
        if normalized_type:
            parts.append(normalized_type)

    if not parts:
        return original_path.name

    # Build filename
    name = "_".join(parts)

    # Add extension
    extension = original_path.suffix.lower() if preserve_extension else ".pdf"

    full_name = name + extension

    # Truncate if too long (preserve extension)
    if len(full_name) > _MAX_TOTAL_LENGTH:
        max_name_len = _MAX_TOTAL_LENGTH - len(extension)
        name = name[:max_name_len].rstrip("-_ ")
        full_name = name + extension

    logger.debug(f"Smart rename: {original_path.name} → {full_name}")
    return full_name


def suggest_rename(
    metadata: OCRMetadata,
    original_path: Path,
) -> tuple[str | None, float]:
    """Suggest a new filename based on OCR metadata.

    This is a safer version that returns None if renaming isn't recommended.

    Args:
        metadata: Extracted OCR metadata
        original_path: Original file path

    Returns:
        Tuple of (suggested filename or None, confidence score)
    """
    if not metadata.has_enough_info():
        return None, 0.0

    new_name = build_smart_name(metadata, original_path)

    # Don't suggest if it's the same as original
    if new_name == original_path.name:
        return None, 0.0

    return new_name, metadata.confidence


def perform_rename(
    original_path: Path,
    new_name: str,
    *,
    dry_run: bool = False,
) -> Path | None:
    """Perform the actual file rename.

    Handles collisions by appending a numeric suffix.

    Args:
        original_path: Original file path
        new_name: New filename (just the name, not full path)
        dry_run: If True, don't actually rename, just return what would happen

    Returns:
        New path if renamed (or would be renamed), None if failed
    """
    if not original_path.exists():
        logger.warning(f"Cannot rename: file does not exist: {original_path}")
        return None

    new_path = original_path.parent / new_name

    # Handle collisions
    if new_path.exists() and new_path != original_path:
        stem = new_path.stem
        suffix = new_path.suffix
        counter = 1

        while new_path.exists():
            new_path = original_path.parent / f"{stem}_{counter}{suffix}"
            counter += 1

            if counter > _MAX_COLLISION_RETRIES:
                logger.warning(f"Too many collisions for: {new_name}")
                return None

    if dry_run:
        if new_path != original_path:
            logger.info(f"[DRY-RUN] Would rename: {original_path.name} → {new_path.name}")
        return new_path

    # Perform actual rename
    try:
        if new_path != original_path:
            original_path.rename(new_path)
            logger.info(f"Renamed: {original_path.name} → {new_path.name}")
    except OSError as e:
        logger.error(f"Failed to rename {original_path}: {e}")
        return None
    else:
        return new_path
