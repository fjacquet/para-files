"""EPUB metadata extraction utilities.

EPUB files are ZIP archives containing XHTML content and OPF metadata.
ISBN is typically stored in <dc:identifier> tags in the OPF file.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from loguru import logger

from para_files.utils.pdf_metadata import extract_all_isbns


# ISBN regex patterns
ISBN_PATTERN = re.compile(r"\b(?:97[89])?\d{9}[\dXx]\b")
# Pattern for ISBNs with dashes/spaces (common in copyright pages)
ISBN_CONTENT_PATTERN = re.compile(r"97[89][-\s]?\d[-\s]?\d{3,4}[-\s]?\d{3,5}[-\s]?\d{1,2}[-\s]?\d")

# OPF namespaces
DC_NS = "{http://purl.org/dc/elements/1.1/}"
OPF_NS = "{http://www.idpf.org/2007/opf}"

# ISBN length constants
ISBN_13_LENGTH = 13


@dataclass
class EpubMetadata:
    """Metadata extracted from an EPUB file."""

    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    isbns: list[str] = field(default_factory=list)
    language: str | None = None
    publisher: str | None = None
    file_size_mb: float = 0.0


def _find_opf_path(zf: zipfile.ZipFile) -> str | None:
    """Find the OPF file path from container.xml.

    Args:
        zf: Open ZipFile object.

    Returns:
        Path to OPF file within the archive, or None if not found.
    """
    try:
        container_xml = zf.read("META-INF/container.xml")
        root = ET.fromstring(container_xml)  # noqa: S314

        # Find rootfile element with media-type application/oebps-package+xml
        for rootfile in root.iter():
            if rootfile.tag.endswith("rootfile"):
                media_type = rootfile.get("media-type", "")
                if "oebps-package+xml" in media_type:
                    return rootfile.get("full-path")
    except (KeyError, ET.ParseError) as e:
        logger.debug("Failed to parse container.xml: {}", e)

    # Fallback: look for common OPF filenames
    for name in zf.namelist():
        if name.endswith(".opf"):
            return name

    return None


def _extract_isbns_from_opf(opf_content: bytes) -> list[str]:
    """Extract ISBNs from OPF metadata.

    Args:
        opf_content: Raw OPF XML content.

    Returns:
        List of ISBNs found.
    """
    isbns: list[str] = []

    try:
        root = ET.fromstring(opf_content)  # noqa: S314

        # Look for dc:identifier elements
        for elem in root.iter():
            if elem.tag == f"{DC_NS}identifier" or elem.tag.endswith("}identifier"):
                text = elem.text or ""
                # Check if it's explicitly marked as ISBN
                scheme = elem.get(f"{OPF_NS}scheme", "") or elem.get("scheme", "")
                id_type = elem.get("id", "")

                if "isbn" in scheme.lower() or "isbn" in id_type.lower():
                    # Extract ISBN from text
                    matches = ISBN_PATTERN.findall(text)
                    isbns.extend(matches)
                elif text:
                    # Check if the text looks like an ISBN
                    clean = re.sub(r"[^\dXx]", "", text)
                    if len(clean) in (10, 13) and ISBN_PATTERN.match(clean):
                        isbns.append(clean)

        # Also search in the raw content for any missed ISBNs
        text_content = opf_content.decode("utf-8", errors="ignore")
        for match in ISBN_PATTERN.finditer(text_content):
            isbn = match.group()
            if isbn not in isbns:
                isbns.append(isbn)

    except ET.ParseError as e:
        logger.debug("Failed to parse OPF: {}", e)

    return isbns


def _extract_metadata_from_opf(opf_content: bytes) -> dict[str, str | None]:
    """Extract metadata fields from OPF.

    Args:
        opf_content: Raw OPF XML content.

    Returns:
        Dict with title, author, language, publisher.
    """
    metadata: dict[str, str | None] = {
        "title": None,
        "author": None,
        "language": None,
        "publisher": None,
    }

    try:
        root = ET.fromstring(opf_content)  # noqa: S314

        for elem in root.iter():
            tag_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            if tag_name == "title" and elem.text and not metadata["title"]:
                metadata["title"] = elem.text.strip()
            elif tag_name == "creator" and elem.text and not metadata["author"]:
                metadata["author"] = elem.text.strip()
            elif tag_name == "language" and elem.text and not metadata["language"]:
                metadata["language"] = elem.text.strip()
            elif tag_name == "publisher" and elem.text and not metadata["publisher"]:
                metadata["publisher"] = elem.text.strip()

    except ET.ParseError as e:
        logger.debug("Failed to parse OPF metadata: {}", e)

    return metadata


def _extract_isbns_from_content(zf: zipfile.ZipFile, max_files: int = 5) -> list[str]:
    """Extract ISBNs from XHTML content files (copyright pages, etc.).

    Args:
        zf: Open ZipFile object.
        max_files: Maximum number of content files to scan.

    Returns:
        List of ISBNs found in content.
    """
    isbns: list[str] = []
    files_scanned = 0

    for name in zf.namelist():
        if files_scanned >= max_files:
            break
        if not name.endswith((".html", ".xhtml", ".htm")):
            continue

        try:
            content = zf.read(name).decode("utf-8", errors="ignore")
            # Search for ISBN patterns with dashes/spaces
            for match in ISBN_CONTENT_PATTERN.finditer(content):
                isbn_raw = match.group()
                # Normalize: remove dashes and spaces
                isbn_clean = re.sub(r"[-\s]", "", isbn_raw)
                if isbn_clean not in isbns and len(isbn_clean) == ISBN_13_LENGTH:
                    isbns.append(isbn_clean)
            files_scanned += 1
        except Exception as e:  # noqa: BLE001
            logger.debug("Failed to read content file {}: {}", name, e)
            continue

    return isbns


def _is_valid_isbn(isbn: str) -> bool:
    """Check if ISBN is valid (not a placeholder like 0000000000000)."""
    if not isbn:
        return False
    clean = re.sub(r"[^\dXx]", "", isbn)
    # Reject all-zeros or mostly zeros
    if clean.count("0") > len(clean) - 2:
        return False
    return len(clean) in (10, 13)


def _create_partial_metadata(filename_isbns: list[str], file_size_mb: float) -> EpubMetadata | None:
    """Create partial metadata from filename ISBNs only."""
    if filename_isbns:
        return EpubMetadata(
            isbn=filename_isbns[0],
            isbns=filename_isbns,
            file_size_mb=file_size_mb,
        )
    return None


def extract_epub_metadata(path: Path) -> EpubMetadata | None:
    """Extract metadata from an EPUB file.

    Args:
        path: Path to the EPUB file.

    Returns:
        EpubMetadata object, or None if extraction fails.
    """
    if not path.exists() or path.suffix.lower() != ".epub":
        return None

    # Check filename for ISBN FIRST (common pattern: "9781234567890_Title.epub")
    filename_isbns = extract_all_isbns(path.stem)
    if filename_isbns:
        logger.debug("Found ISBN(s) {} in filename of {}", filename_isbns, path.name)

    # Calculate file size
    file_size_mb = path.stat().st_size / (1024 * 1024)

    try:
        with zipfile.ZipFile(path, "r") as zf:
            # Find OPF file
            opf_path = _find_opf_path(zf)
            if not opf_path:
                logger.debug("No OPF file found in EPUB: {}", path)
                return _create_partial_metadata(filename_isbns, file_size_mb)

            # Read and parse OPF
            opf_content = zf.read(opf_path)

            # Extract ISBNs from OPF
            opf_isbns = _extract_isbns_from_opf(opf_content)
            # Filter out invalid/placeholder ISBNs
            opf_isbns = [isbn for isbn in opf_isbns if _is_valid_isbn(isbn)]

            # If no valid OPF ISBNs, scan content files (copyright pages)
            content_isbns: list[str] = []
            if not opf_isbns and not filename_isbns:
                content_isbns = _extract_isbns_from_content(zf)
                if content_isbns:
                    logger.debug("Found ISBN(s) {} in content of {}", content_isbns, path.name)

            # Combine: filename ISBNs first, then content, then OPF
            all_isbns = list(filename_isbns)
            seen_isbns = set(filename_isbns)
            for isbn in content_isbns + opf_isbns:
                if isbn not in seen_isbns:
                    seen_isbns.add(isbn)
                    all_isbns.append(isbn)

            # Extract other metadata
            meta = _extract_metadata_from_opf(opf_content)

            return EpubMetadata(
                title=meta["title"],
                author=meta["author"],
                isbn=all_isbns[0] if all_isbns else None,
                isbns=all_isbns,
                language=meta["language"],
                publisher=meta["publisher"],
                file_size_mb=file_size_mb,
            )

    except zipfile.BadZipFile:
        logger.debug("Invalid EPUB (bad ZIP): {}", path)
    except Exception as e:  # noqa: BLE001
        logger.debug("Failed to extract EPUB metadata from {}: {}", path, e)

    return _create_partial_metadata(filename_isbns, file_size_mb)
