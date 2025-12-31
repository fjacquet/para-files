"""File utility functions for metadata extraction and content reading."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from para_files.types import FileMetadata


if TYPE_CHECKING:
    from para_files.utils.ocr import OCRResult
    from para_files.utils.pandoc import PandocResult


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
        FileMetadata with filename, extension, size, dates, and optional EXIF/PDF.
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

    # Extract PDF metadata for PDF files
    pdf_title = None
    pdf_author = None
    pdf_subject = None

    if file_path.suffix.lower() == ".pdf":
        from para_files.utils.pdf_metadata import extract_pdf_metadata

        pdf_meta = extract_pdf_metadata(file_path, max_pages_for_isbn=0)  # Skip ISBN scan
        if pdf_meta:
            pdf_title = pdf_meta.title
            pdf_author = pdf_meta.author
            pdf_subject = pdf_meta.subject

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
        pdf_title=pdf_title,
        pdf_author=pdf_author,
        pdf_subject=pdf_subject,
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


# Minimum chars to consider PDF as having extractable text (vs scanned)
_PDF_MIN_TEXT_THRESHOLD = 50


def _read_pdf_file(file_path: Path, max_chars: int) -> str:
    """Extract text from PDF file.

    Uses pypdf first, falls back to OCR for scanned PDFs.

    Args:
        file_path: Path to PDF file.
        max_chars: Maximum characters to extract.

    Returns:
        Extracted text or filename fallback.
    """
    # 1. Try pypdf first (fast, works for text-based PDFs)
    text = _extract_pdf_with_pypdf(file_path, max_chars)

    # 2. If text is too short, PDF is likely scanned - try OCR
    if len(text.strip()) < _PDF_MIN_TEXT_THRESHOLD:
        logger.debug(
            "PDF appears scanned (<%d chars), trying OCR: %s",
            _PDF_MIN_TEXT_THRESHOLD,
            file_path,
        )
        ocr_text = _ocr_pdf_first_page(file_path, max_chars)
        if ocr_text and len(ocr_text.strip()) > len(text.strip()):
            return ocr_text

    return text if text.strip() else f"Filename: {file_path.name}"


def _extract_pdf_with_pypdf(file_path: Path, max_chars: int) -> str:
    """Extract text from PDF using pypdf, with pdftotext fallback."""
    # Try pypdf first
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
        logger.debug("pypdf not installed: %s", file_path)
    except Exception:  # noqa: BLE001
        # pypdf can fail on various PDF formats - try pdftotext fallback
        logger.debug("pypdf failed, trying pdftotext: %s", file_path)

    # Fallback to pdftotext (poppler-utils)
    try:
        import subprocess

        result = subprocess.run(  # noqa: S603
            ["pdftotext", "-q", str(file_path), "-"],  # noqa: S607
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout[:max_chars]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.debug("pdftotext not available or timeout: %s", file_path)
    except Exception:  # noqa: BLE001
        logger.debug("pdftotext failed: %s", file_path)

    return ""


def _ocr_pdf_first_page(file_path: Path, max_chars: int) -> str:
    """OCR the first page of a PDF using pymupdf + Vision framework.

    Args:
        file_path: Path to PDF file.
        max_chars: Maximum characters to extract.

    Returns:
        OCR text or empty string on failure.
    """
    import tempfile

    try:
        import fitz  # pymupdf

        from para_files.utils.ocr import extract_text as ocr_extract
    except ImportError as e:
        logger.debug("pymupdf or OCR not available: %s", e)
        return ""

    try:
        # Open PDF and render first page to image
        doc = fitz.open(file_path)
        if len(doc) == 0:
            return ""

        page = doc[0]
        # Render at 2x resolution for better OCR
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)

        # Convert to PNG bytes for Vision OCR
        png_bytes = pix.tobytes("png")

        # Create temp file for OCR (Vision needs a file path)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(png_bytes)
            tmp_path = Path(tmp.name)

        try:
            result = ocr_extract(tmp_path, max_chars)
        finally:
            tmp_path.unlink(missing_ok=True)

    except Exception:
        logger.exception("OCR failed for PDF: %s", file_path)
        return ""

    if result and result.text:
        logger.debug("OCR extracted %d chars from PDF: %s", len(result.text), file_path)
        return result.text[:max_chars]

    return ""


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
