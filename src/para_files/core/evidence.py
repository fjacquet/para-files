"""Evidence: everything the signals may read about one file, extracted once (spec §4.2)."""

from __future__ import annotations

import hashlib
import tarfile
import unicodedata
import zipfile
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

from loguru import logger

from para_files.core.secrets import secret_reason
from para_files.utils.epub_metadata import extract_epub_metadata
from para_files.utils.exiftool import extract_exif, is_exiftool_available
from para_files.utils.file_utils import read_content_preview
from para_files.utils.mobi_metadata import extract_mobi_metadata
from para_files.utils.pdf_metadata import extract_pdf_metadata


MAX_ARCHIVE_ENTRIES = 200
MAX_ISBN_PAGES = 10
MEDIA_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".dng", ".cr2", ".nef", ".arw"}
    | {".mov", ".mp4", ".m4v"}
)
TAR_SUFFIXES = (".tar", ".tgz", ".tar.gz", ".tar.bz2", ".tar.xz")


@dataclass(frozen=True)
class Evidence:
    """One file as the signals see it. A secret file carries only filesystem facts."""

    path: Path
    name: str
    ext: str
    size: int
    mtime: float
    sha256: str
    secret: str | None = None
    text_preview: str = ""
    doc_meta: dict[str, str] = field(default_factory=dict)
    isbns: tuple[str, ...] = ()
    exif_date: datetime | None = None
    archive_listing: tuple[str, ...] = ()


def sha256_of(path: Path) -> str:
    """Content hash (hex)."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _secret_folder(path: Path, root: Path | None) -> str | None:
    """'folder' when a folder between root and the file is secret-named."""
    if root is None:
        return None
    try:
        parts = path.resolve().parent.relative_to(root.resolve()).parts  # /var vs /private/var
    except ValueError:
        return None
    return "folder" if any(secret_reason(part) for part in parts) else None


def _preview(path: Path, max_chars: int) -> str:
    try:
        text = read_content_preview(path, max_chars)
    except Exception as exc:  # noqa: BLE001 - a reader failure leaves the preview empty
        logger.warning("preview failed for {}: {}", path.name, exc)
        return ""
    return "" if text.strip() == f"Filename: {path.name}" else text[:max_chars]


def _book_meta(path: Path, ext: str) -> tuple[dict[str, str], tuple[str, ...]]:
    try:
        if ext == ".pdf":
            pdf = extract_pdf_metadata(path, max_pages_for_isbn=MAX_ISBN_PAGES)
            if pdf is None:
                return {}, ()
            meta = {
                "title": pdf.title or "",
                "author": pdf.author or "",
                "subject": pdf.subject or "",
                "page_count": str(pdf.page_count or 0),
            }
            return meta, tuple(pdf.isbns)
        if ext in {".epub", ".mobi"}:
            book = extract_epub_metadata(path) if ext == ".epub" else extract_mobi_metadata(path)
            if book is None:
                return {}, ()
            return {"title": book.title or "", "author": book.author or ""}, tuple(book.isbns)
    except Exception as exc:  # noqa: BLE001 - metadata is optional evidence
        logger.warning("metadata failed for {}: {}", path.name, exc)
    return {}, ()


def _exif_date(path: Path, ext: str) -> datetime | None:
    if ext not in MEDIA_EXTENSIONS or not is_exiftool_available():
        return None
    try:
        data = extract_exif(path)
    except Exception as exc:  # noqa: BLE001 - EXIF is optional evidence
        logger.warning("EXIF failed for {}: {}", path.name, exc)
        return None
    return (data.date_taken or data.date_created) if data else None


def _archive_listing(path: Path) -> tuple[str, ...]:
    lower = path.name.lower()
    try:
        if lower.endswith(".zip"):
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
        elif lower.endswith(TAR_SUFFIXES):
            with tarfile.open(path) as archive:
                names = archive.getnames()
        else:
            return ()
    except (OSError, zipfile.BadZipFile, tarfile.TarError) as exc:
        logger.warning("archive listing failed for {}: {}", path.name, exc)
        return ()
    return tuple(names)


def extract(path: Path, *, root: Path | None = None, preview_chars: int = 2000) -> Evidence:
    """Read one file once; secret checks run before any content is kept."""
    path = path.absolute()
    stat = path.stat()
    base = Evidence(
        path=path,
        name=unicodedata.normalize("NFC", path.name),
        ext=path.suffix.lower(),
        size=stat.st_size,
        mtime=stat.st_mtime,
        sha256=sha256_of(path),
    )
    secret = _secret_folder(path, root) or secret_reason(base.name)
    if secret:
        return replace(base, secret=secret)
    listing = _archive_listing(path)
    if any(secret_reason(entry) for entry in listing):
        return replace(base, secret="archive")  # noqa: S106 - a reason, not a password
    preview = _preview(path, preview_chars)
    secret = secret_reason(base.name, preview)
    if secret:
        return replace(base, secret=secret)
    meta, isbns = _book_meta(path, base.ext)
    return replace(
        base,
        text_preview=preview,
        doc_meta=meta,
        isbns=isbns,
        exif_date=_exif_date(path, base.ext),
        archive_listing=listing[:MAX_ARCHIVE_ENTRIES],
    )
