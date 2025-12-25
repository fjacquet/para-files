"""File utility functions for metadata extraction and content reading."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from para_files.types import FileMetadata


if TYPE_CHECKING:
    from para_files.utils.ocr import OCRResult
    from para_files.utils.pandoc import PandocResult


logger = logging.getLogger(__name__)

# Text file extensions that can be read directly
TEXT_EXTENSIONS = frozenset(
    {
        ".txt",
        ".md",
        ".markdown",
        ".rst",
        ".py",
        ".js",
        ".ts",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".xml",
        ".html",
        ".htm",
        ".css",
        ".csv",
        ".log",
        ".ini",
        ".cfg",
        ".conf",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".sql",
        ".r",
        ".rb",
        ".php",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".go",
        ".rs",
        ".swift",
        ".kt",
        ".scala",
        ".clj",
        ".edn",
        ".ex",
        ".exs",
        ".erl",
        ".hrl",
        ".hs",
        ".ml",
        ".mli",
        ".elm",
        ".vue",
        ".svelte",
    }
)


def extract_file_metadata(file_path: Path, *, extract_exif: bool = True) -> FileMetadata:
    """Extract metadata from a file.

    Args:
        file_path: Path to the file.
        extract_exif: Whether to extract EXIF data (requires exiftool).

    Returns:
        FileMetadata with filename, extension, size, dates, and optional EXIF.
    """
    stat = file_path.stat()

    # Get modification time as datetime
    modified_at = datetime.fromtimestamp(stat.st_mtime, tz=UTC)

    # Get creation time if available (macOS)
    created_at = None
    if hasattr(stat, "st_birthtime"):
        created_at = datetime.fromtimestamp(stat.st_birthtime, tz=UTC)

    # Extract EXIF data if requested
    exif_date = None
    exif_gps_lat = None
    exif_gps_lon = None
    exif_camera = None

    if extract_exif:
        from para_files.utils.exiftool import extract_exif as get_exif

        exif = get_exif(file_path)
        if exif:
            exif_date = exif.best_date
            if exif.gps:
                exif_gps_lat = exif.gps.latitude
                exif_gps_lon = exif.gps.longitude
            if exif.make and exif.model:
                exif_camera = f"{exif.make} {exif.model}"
            elif exif.make:
                exif_camera = exif.make
            elif exif.model:
                exif_camera = exif.model

    return FileMetadata(
        path=file_path,
        filename=file_path.name,
        extension=file_path.suffix,
        size_bytes=stat.st_size,
        modified_at=modified_at,
        created_at=created_at,
        exif_date=exif_date,
        exif_gps_lat=exif_gps_lat,
        exif_gps_lon=exif_gps_lon,
        exif_camera=exif_camera,
    )


def read_content_preview(
    file_path: Path,
    max_chars: int = 2000,
) -> str:
    """Read content preview from a file.

    For text files, reads the first max_chars characters.
    For documents (docx, odt, epub, etc.), uses pandoc to extract text.
    For PDF files, uses pypdf.
    For binary files, returns the filename as content.

    Args:
        file_path: Path to the file.
        max_chars: Maximum characters to read.

    Returns:
        Content preview string.
    """
    extension = file_path.suffix.lower()

    # For text files, read content directly
    if extension in TEXT_EXTENSIONS:
        return _read_text_file(file_path, max_chars)

    # For PDF files, try to extract text with pypdf
    if extension == ".pdf":
        return _read_pdf_file(file_path, max_chars)

    # For document formats, try pandoc extraction
    from para_files.utils.pandoc import PANDOC_EXTENSIONS, extract_text

    if extension in PANDOC_EXTENSIONS:
        return _read_document_file(file_path, max_chars, extract_text)

    # For image files, try OCR extraction
    from para_files.utils.ocr import OCR_EXTENSIONS
    from para_files.utils.ocr import extract_text as extract_ocr_text

    if extension in OCR_EXTENSIONS:
        return _read_image_file(file_path, max_chars, extract_ocr_text)

    # For other files, use filename as content
    return f"Filename: {file_path.name}"


def _read_text_file(file_path: Path, max_chars: int) -> str:
    """Read text file content.

    Args:
        file_path: Path to text file.
        max_chars: Maximum characters to read.

    Returns:
        Text content.
    """
    try:
        with file_path.open(encoding="utf-8", errors="replace") as f:
            return f.read(max_chars)
    except OSError:
        logger.warning("Failed to read text file: %s", file_path)
        return f"Filename: {file_path.name}"


def _read_pdf_file(file_path: Path, max_chars: int) -> str:
    """Extract text from PDF file.

    Uses pypdf if available, otherwise returns filename.

    Args:
        file_path: Path to PDF file.
        max_chars: Maximum characters to extract.

    Returns:
        Extracted text or filename fallback.
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        text_parts = []
        chars_read = 0

        for page in reader.pages:
            page_text = page.extract_text() or ""
            remaining = max_chars - chars_read
            if remaining <= 0:
                break
            text_parts.append(page_text[:remaining])
            chars_read += len(page_text[:remaining])

        return "".join(text_parts)

    except ImportError:
        logger.debug("pypdf not installed, using filename for PDF: %s", file_path)
        return f"Filename: {file_path.name}"
    except (OSError, ValueError):
        logger.warning("Failed to extract PDF text: %s", file_path)
        return f"Filename: {file_path.name}"


def _read_document_file(
    file_path: Path,
    max_chars: int,
    extract_fn: Callable[[Path, int], PandocResult | None],
) -> str:
    """Extract text from document file using pandoc.

    Args:
        file_path: Path to document file.
        max_chars: Maximum characters to extract.
        extract_fn: Function to extract text (injected to avoid circular import).

    Returns:
        Extracted text or filename fallback.
    """
    result = extract_fn(file_path, max_chars)
    if result and result.text:
        return result.text

    logger.debug("pandoc extraction failed, using filename: %s", file_path)
    return f"Filename: {file_path.name}"


def _read_image_file(
    file_path: Path,
    max_chars: int,
    extract_fn: Callable[[Path, int], OCRResult | None],
) -> str:
    """Extract text from image file using OCR.

    Args:
        file_path: Path to image file.
        max_chars: Maximum characters to extract.
        extract_fn: Function to extract text (injected to avoid circular import).

    Returns:
        Extracted text or filename fallback.
    """
    result = extract_fn(file_path, max_chars)
    if result and result.text:
        return result.text

    logger.debug("OCR extraction failed, using filename: %s", file_path)
    return f"Filename: {file_path.name}"
