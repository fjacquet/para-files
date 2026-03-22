"""CHM metadata extraction for book detection.

Extracts metadata and ISBN from Microsoft Compiled HTML Help (.chm) files.
Uses 7z to decompress and extract HTML content for ISBN scanning.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from para_files.utils.pdf_metadata import extract_all_isbns


# Minimum title length to be considered valid
MIN_TITLE_LENGTH = 3


@dataclass
class ChmMetadata:
    """Metadata extracted from a CHM file."""

    title: str | None = None
    isbn: str | None = None  # First ISBN found
    isbns: list[str] = field(default_factory=list)  # All ISBNs found
    file_size_mb: float = 0.0


def _find_7z_binary() -> str | None:
    """Find the 7z binary path."""
    for name in ["7z", "7zz", "7za"]:
        path = shutil.which(name)
        if path:
            return path
    return None


def _extract_chm_to_temp(chm_path: Path, temp_dir: Path) -> bool:
    """Extract CHM contents to a temporary directory.

    Args:
        chm_path: Path to the CHM file.
        temp_dir: Temporary directory to extract to.

    Returns:
        True if extraction succeeded.
    """
    binary = _find_7z_binary()
    if not binary:
        logger.warning("7z not found - cannot extract CHM files")
        return False

    if chm_path.suffix.lower() != ".chm":
        logger.warning("Rejected non-CHM file for CHM extraction: {}", chm_path.suffix)
        return False

    try:
        result = subprocess.run(  # noqa: S603
            [binary, "x", "-y", f"-o{temp_dir}", str(chm_path)],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning("CHM extraction timed out for {}", chm_path.name)
        return False
    except (
        subprocess.SubprocessError, FileNotFoundError, OSError, UnicodeDecodeError, ValueError
    ) as e:
        logger.warning("CHM extraction failed for {}: {}", chm_path.name, e)
        return False
    else:
        return result.returncode == 0


def _extract_title_from_html(html_content: str) -> str | None:
    """Extract title from HTML content.

    Args:
        html_content: HTML content string.

    Returns:
        Title if found, None otherwise.
    """
    # Try <title> tag
    match = re.search(r"<title[^>]*>([^<]+)</title>", html_content, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        if title and len(title) > MIN_TITLE_LENGTH:
            return title

    # Try <h1> tag
    match = re.search(r"<h1[^>]*>([^<]+)</h1>", html_content, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        if title and len(title) > MIN_TITLE_LENGTH:
            return title

    return None


def _scan_html_files_for_isbns(temp_dir: Path, max_files: int = 20) -> list[str]:
    """Scan HTML files for ISBNs.

    Args:
        temp_dir: Directory containing extracted HTML files.
        max_files: Maximum number of files to scan.

    Returns:
        List of unique ISBNs found.
    """
    all_isbns: list[str] = []
    seen: set[str] = set()

    # Find HTML files
    html_files = list(temp_dir.rglob("*.htm")) + list(temp_dir.rglob("*.html"))

    # Sort by size (smaller files like copyright pages often have ISBN)
    html_files.sort(key=lambda f: f.stat().st_size)

    for html_file in html_files[:max_files]:
        try:
            content = html_file.read_text(errors="ignore")
            isbns = extract_all_isbns(content)
            for isbn in isbns:
                if isbn not in seen:
                    seen.add(isbn)
                    all_isbns.append(isbn)
        except (OSError, UnicodeDecodeError, ValueError):
            continue

    return all_isbns


def _extract_title_from_files(temp_dir: Path) -> str | None:
    """Extract title from HTML files in temp directory.

    Args:
        temp_dir: Directory containing extracted files.

    Returns:
        Title if found, None otherwise.
    """
    # Look for common title page files
    title_files = [
        "index.html",
        "index.htm",
        "default.html",
        "default.htm",
        "title.html",
        "title.htm",
        "cover.html",
        "cover.htm",
    ]

    for filename in title_files:
        for html_file in temp_dir.rglob(filename):
            try:
                content = html_file.read_text(errors="ignore")
                title = _extract_title_from_html(content)
                if title:
                    return title
            except (OSError, UnicodeDecodeError, ValueError):
                continue

    # Try any HTML file
    for html_file in list(temp_dir.rglob("*.htm"))[:5]:
        try:
            content = html_file.read_text(errors="ignore")
            title = _extract_title_from_html(content)
            if title:
                return title
        except (OSError, UnicodeDecodeError, ValueError):
            continue

    return None


def extract_chm_metadata(path: Path) -> ChmMetadata | None:
    """Extract metadata from a CHM file.

    Uses 7z to extract HTML content and scans for ISBNs.

    Args:
        path: Path to the CHM file.

    Returns:
        ChmMetadata object or None if extraction fails.
    """
    if not path.exists() or path.suffix.lower() != ".chm":
        return None

    # Check filename for ISBN first
    filename_isbns = extract_all_isbns(path.stem)
    if filename_isbns:
        logger.debug("Found ISBN(s) {} in filename of {}", filename_isbns, path.name)

    # Calculate file size
    file_size_mb = path.stat().st_size / (1024 * 1024)

    # Extract CHM to temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        if not _extract_chm_to_temp(path, temp_path):
            # Return partial metadata if we found ISBN in filename
            if filename_isbns:
                return ChmMetadata(
                    title=None,
                    isbn=filename_isbns[0],
                    isbns=filename_isbns,
                    file_size_mb=file_size_mb,
                )
            return None

        # Collect ISBNs: start with filename, then content
        all_isbns = list(filename_isbns)
        seen_isbns = set(filename_isbns)

        content_isbns = _scan_html_files_for_isbns(temp_path)
        for isbn in content_isbns:
            if isbn not in seen_isbns:
                seen_isbns.add(isbn)
                all_isbns.append(isbn)

        # Extract title
        title = _extract_title_from_files(temp_path)

        if all_isbns:
            logger.debug("Found {} ISBN(s) in {}", len(all_isbns), path.name)

        return ChmMetadata(
            title=title,
            isbn=all_isbns[0] if all_isbns else None,
            isbns=all_isbns,
            file_size_mb=file_size_mb,
        )
