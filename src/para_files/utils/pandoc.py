"""Pandoc integration for extracting text from documents.

Uses pandoc CLI for converting various document formats to plain text.
Falls back gracefully when pandoc is not installed.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field


# Preview length constants
_PREVIEW_LENGTH = 500

# Mapping of file extensions to pandoc input formats
PANDOC_FORMATS: dict[str, str] = {
    # Word processing
    ".docx": "docx",
    ".odt": "odt",
    ".rtf": "rtf",
    # Presentations
    ".pptx": "pptx",
    # eBooks
    ".epub": "epub",
    ".fb2": "fb2",
    # Markup
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "rst",
    ".tex": "latex",
    ".latex": "latex",
    # Web
    ".html": "html",
    ".htm": "html",
    ".xhtml": "html",
    # Data
    ".ipynb": "ipynb",
    # Wiki
    ".mediawiki": "mediawiki",
    ".wiki": "mediawiki",
    ".org": "org",
    # Other
    ".docbook": "docbook",
    ".man": "man",
    ".t2t": "t2t",
    ".textile": "textile",
    ".twiki": "twiki",
    ".opml": "opml",
}

# Extensions that pandoc can handle
PANDOC_EXTENSIONS = frozenset(PANDOC_FORMATS.keys())

# Explicit allowlist of extensions permitted to reach the subprocess.
# Must be a subset of PANDOC_FORMATS keys (no .md/.markdown/.tex/.latex/.xhtml
# /.ipynb/.mediawiki/.wiki/.docbook/.man/.t2t/.twiki — those are handled by
# PANDOC_FORMATS but excluded from the subprocess allowlist intentionally).
ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".docx",
        ".doc",
        ".rtf",
        ".odt",
        ".html",
        ".htm",
        ".epub",
        ".pptx",
        ".fb2",
        ".textile",
        ".rst",
        ".org",
        ".opml",
        ".muse",
        ".native",
        ".json",
        ".csv",
        ".tsv",
        ".bib",
    }
)


class PandocResult(BaseModel):
    """Result of pandoc text extraction."""

    text: str = Field(description="Extracted plain text content")
    format: str = Field(description="Detected input format")
    char_count: int = Field(description="Number of characters extracted")
    word_count: int = Field(description="Approximate word count")

    @property
    def preview(self) -> str:
        """Return first 500 characters as preview."""
        if len(self.text) <= _PREVIEW_LENGTH:
            return self.text
        return self.text[:_PREVIEW_LENGTH] + "..."


def is_pandoc_available() -> bool:
    """Check if pandoc is installed and accessible."""
    return shutil.which("pandoc") is not None


def get_pandoc_format(file_path: Path) -> str | None:
    """Get the pandoc input format for a file extension.

    Args:
        file_path: Path to the file.

    Returns:
        Pandoc format name, or None if unsupported.
    """
    ext = file_path.suffix.lower()
    return PANDOC_FORMATS.get(ext)


def _run_pandoc_to_plain(file_path: Path, fmt: str) -> str | None:
    """Run pandoc and return plain text output."""
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        logger.warning("Rejected file with unsupported extension for pandoc: {}", file_path.suffix)
        return None

    pandoc_args = [
        "pandoc",
        "--from",
        fmt,
        "--to",
        "plain",
        "--wrap",
        "none",
        str(file_path),
    ]
    try:
        result = subprocess.run(  # noqa: S603
            pandoc_args,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode != 0:
            logger.debug("pandoc failed: {}", result.stderr)
            return None

    except subprocess.TimeoutExpired:
        logger.warning("pandoc timed out for: {}", file_path)
        return None
    except (subprocess.SubprocessError, FileNotFoundError, OSError, UnicodeDecodeError) as e:
        logger.exception("Failed to extract text with pandoc from: {} ({})", file_path, e)
        return None

    return result.stdout or None


def extract_text(
    file_path: Path,
    max_chars: int = 10000,
) -> PandocResult | None:
    """Extract plain text from a document using pandoc.

    Args:
        file_path: Path to the document file.
        max_chars: Maximum characters to extract.

    Returns:
        PandocResult if extraction succeeds, None otherwise.
    """
    if not is_pandoc_available():
        logger.debug("pandoc not available")
        return None

    fmt = get_pandoc_format(file_path)
    if fmt is None or not file_path.exists():
        logger.debug("Unsupported format or file missing: {}", file_path)
        return None

    text = _run_pandoc_to_plain(file_path, fmt)
    if not text:
        return None

    # Truncate if needed
    if len(text) > max_chars:
        text = text[:max_chars]

    return PandocResult(
        text=text,
        format=fmt,
        char_count=len(text),
        word_count=len(text.split()),
    )


def extract_metadata(file_path: Path) -> dict[str, str] | None:
    """Extract document metadata using pandoc.

    Extracts title, author, date, and other YAML front matter.

    Args:
        file_path: Path to the document file.

    Returns:
        Dictionary of metadata fields, or None if extraction fails.
    """
    if not is_pandoc_available():
        return None

    fmt = get_pandoc_format(file_path)
    if fmt is None or not file_path.exists() or file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            logger.warning(
                "Rejected file with unsupported extension for pandoc: {}", file_path.suffix
            )
        return None

    # Template to extract metadata fields
    template = (
        "$if(title)$title: $title$\n$endif$"
        "$if(author)$author: $for(author)$$author$$sep$, $endfor$\n$endif$"
        "$if(date)$date: $date$\n$endif$"
        "$if(subtitle)$subtitle: $subtitle$\n$endif$"
        "$if(subject)$subject: $subject$\n$endif$"
        "$if(keywords)$keywords: $for(keywords)$$keywords$$sep$, $endfor$\n$endif$"
    )

    pandoc_args = [
        "pandoc",
        "--from",
        fmt,
        "--to",
        "plain",
        "--template",
        "-",
        str(file_path),
    ]
    try:
        result = subprocess.run(  # noqa: S603
            pandoc_args,
            input=template,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode != 0:
            return None

    except subprocess.TimeoutExpired:
        logger.warning("pandoc metadata extraction timed out for: {}", file_path)
        return None
    except (subprocess.SubprocessError, FileNotFoundError, OSError, UnicodeDecodeError) as e:
        logger.exception("Failed to extract metadata with pandoc from: {} ({})", file_path, e)
        return None

    # Parse the output into a dictionary
    metadata: dict[str, str] = {}
    for line in result.stdout.strip().split("\n"):
        if ": " in line:
            key, value = line.split(": ", 1)
            metadata[key.strip()] = value.strip()

    return metadata or None
