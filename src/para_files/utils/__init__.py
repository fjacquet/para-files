"""Utility functions for para-files."""

from para_files.utils.cleanup import (
    JUNK_DIRECTORIES,
    JUNK_PATTERNS,
    cleanup_empty_dirs,
    cleanup_junk,
    delete_junk_directory,
    delete_junk_file,
    is_junk_directory,
    is_junk_file,
    scan_for_junk,
)
from para_files.utils.cleanup_log import (
    CleanupLogEntry,
    CleanupLogger,
    get_default_log_path,
)
from para_files.utils.exiftool import (
    EXIF_EXTENSIONS,
    ExifData,
    GPSCoordinates,
    extract_exif,
    is_exiftool_available,
)
from para_files.utils.file_utils import extract_file_metadata, read_content_preview
from para_files.utils.geolocation import (
    LocationInfo,
    get_location_folder,
    reverse_geocode,
)
from para_files.utils.isbn_lookup import (
    BookInfo,
    infer_technology_from_subjects,
    isbn_to_isbn13,
    lookup_isbn,
    normalize_isbn,
    validate_isbn,
)
from para_files.utils.nfo_parser import (
    NfoHints,
    find_associated_nfo,
    get_nfo_hints_for_file,
    parse_nfo,
)
from para_files.utils.ocr import (
    OCR_EXTENSIONS,
    OCRResult,
    is_vision_available,
)
from para_files.utils.ocr import (
    extract_text as extract_ocr_text,
)
from para_files.utils.ocr import (
    extract_text_with_regions as extract_ocr_regions,
)
from para_files.utils.pandoc import (
    PANDOC_EXTENSIONS,
    PANDOC_FORMATS,
    PandocResult,
    get_pandoc_format,
    is_pandoc_available,
)
from para_files.utils.pandoc import (
    extract_metadata as extract_pandoc_metadata,
)
from para_files.utils.pandoc import (
    extract_text as extract_pandoc_text,
)
from para_files.utils.pdf_metadata import (
    PdfMetadata,
    contains_book_keywords,
    extract_isbn,
    extract_pdf_metadata,
    is_book_creator,
)
from para_files.utils.validation import (
    validate_directory_exists,
    validate_file_exists,
)


__all__ = [
    # Original exports
    "EXIF_EXTENSIONS",
    # Cleanup
    "JUNK_DIRECTORIES",
    "JUNK_PATTERNS",
    "OCR_EXTENSIONS",
    "PANDOC_EXTENSIONS",
    "PANDOC_FORMATS",
    "BookInfo",
    "CleanupLogEntry",
    "CleanupLogger",
    "ExifData",
    "GPSCoordinates",
    "LocationInfo",
    # NFO Parser
    "NfoHints",
    "OCRResult",
    "PandocResult",
    "PdfMetadata",
    "cleanup_empty_dirs",
    "cleanup_junk",
    "contains_book_keywords",
    "delete_junk_directory",
    "delete_junk_file",
    "extract_exif",
    "extract_file_metadata",
    "extract_isbn",
    "extract_ocr_regions",
    "extract_ocr_text",
    "extract_pandoc_metadata",
    "extract_pandoc_text",
    "extract_pdf_metadata",
    "find_associated_nfo",
    "get_default_log_path",
    "get_location_folder",
    "get_nfo_hints_for_file",
    "get_pandoc_format",
    "infer_technology_from_subjects",
    "is_book_creator",
    "is_exiftool_available",
    "is_junk_directory",
    "is_junk_file",
    "is_pandoc_available",
    "is_vision_available",
    "isbn_to_isbn13",
    "lookup_isbn",
    "normalize_isbn",
    "parse_nfo",
    "read_content_preview",
    "reverse_geocode",
    "scan_for_junk",
    "validate_directory_exists",
    "validate_file_exists",
    "validate_isbn",
]
