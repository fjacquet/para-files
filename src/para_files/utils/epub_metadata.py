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


# ISBN regex pattern
ISBN_PATTERN = re.compile(r"\b(?:97[89])?\d{9}[\dXx]\b")

# OPF namespaces
DC_NS = "{http://purl.org/dc/elements/1.1/}"
OPF_NS = "{http://www.idpf.org/2007/opf}"


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


def extract_epub_metadata(path: Path) -> EpubMetadata | None:
    """Extract metadata from an EPUB file.

    Args:
        path: Path to the EPUB file.

    Returns:
        EpubMetadata object, or None if extraction fails.
    """
    if not path.exists():
        logger.debug("EPUB file not found: {}", path)
        return None

    if path.suffix.lower() != ".epub":
        logger.debug("Not an EPUB file: {}", path)
        return None

    try:
        file_size_mb = path.stat().st_size / (1024 * 1024)

        with zipfile.ZipFile(path, "r") as zf:
            # Find OPF file
            opf_path = _find_opf_path(zf)
            if not opf_path:
                logger.debug("No OPF file found in EPUB: {}", path)
                return None

            # Read and parse OPF
            opf_content = zf.read(opf_path)

            # Extract ISBNs
            isbns = _extract_isbns_from_opf(opf_content)

            # Extract other metadata
            meta = _extract_metadata_from_opf(opf_content)

            return EpubMetadata(
                title=meta["title"],
                author=meta["author"],
                isbn=isbns[0] if isbns else None,
                isbns=isbns,
                language=meta["language"],
                publisher=meta["publisher"],
                file_size_mb=file_size_mb,
            )

    except zipfile.BadZipFile:
        logger.debug("Invalid EPUB (bad ZIP): {}", path)
    except Exception as e:  # noqa: BLE001
        logger.debug("Failed to extract EPUB metadata from {}: {}", path, e)

    return None
