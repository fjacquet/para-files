"""Bookstore command for para-files CLI.

This module provides the 'bookstore' command which scans a directory
for books (PDF, CHM, EPUB) with ISBN and moves them to the appropriate
Thema-classified location in the PARA structure.

Only books with confirmed ISBN are moved (100% confidence).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from loguru import logger

from para_files.cli.app import app
from para_files.cli.shared import (
    load_config_or_exit,
    setup_logging,
    validate_directory_or_exit,
)
from para_files.mover import FileMover
from para_files.utils.chm_metadata import extract_chm_metadata
from para_files.utils.epub_metadata import extract_epub_metadata
from para_files.utils.isbn_lookup import BookInfo, find_matching_book_info
from para_files.utils.pdf_metadata import extract_pdf_metadata
from para_files.utils.thema_lookup import get_thema_lookup


# Supported book file extensions
BOOK_EXTENSIONS = {".pdf", ".chm", ".epub"}


# Constants
MAX_AUTHOR_LENGTH = 30
MAX_TITLE_LENGTH = 60


def _sanitize_book_title(title: str, max_length: int = 80) -> str:
    """Convert a book title to a valid filename.

    Args:
        title: Original title from PDF or ISBN lookup.
        max_length: Maximum filename length.

    Returns:
        Sanitized filename-safe string.
    """
    # Replace invalid filesystem characters
    invalid_chars = '<>:"/\\|?*'
    result = title
    for char in invalid_chars:
        result = result.replace(char, "_")

    # Collapse multiple underscores/spaces
    while "__" in result:
        result = result.replace("__", "_")
    while "  " in result:
        result = result.replace("  ", " ")

    # Trim and limit length
    result = result.strip("_ ")
    if len(result) > max_length:
        result = result[:max_length].rsplit(" ", 1)[0]

    return result


def _build_book_filename(book_info: BookInfo, original_name: str, extension: str) -> str:
    """Build a clean filename for a book.

    Format: "Author - Title (Year).ext"

    Args:
        book_info: Book information from ISBN lookup.
        original_name: Original filename as fallback.
        extension: File extension to use (e.g., ".pdf", ".epub").

    Returns:
        Clean filename for the book.
    """
    if not book_info.title:
        return original_name

    parts = []

    # Add author if available
    if book_info.authors:
        author = book_info.authors[0]
        # Shorten long author names
        if len(author) > MAX_AUTHOR_LENGTH:
            author = author.split(",")[0]
        parts.append(_sanitize_book_title(author, MAX_AUTHOR_LENGTH))

    # Add title
    title = _sanitize_book_title(book_info.title, MAX_TITLE_LENGTH)
    parts.append(title)

    # Build filename: "Author - Title" or just "Title"
    if len(parts) > 1:
        filename = f"{parts[0]} - {parts[1]}"
    elif parts:
        filename = parts[0]
    else:
        # Remove extension from original name for base filename
        filename = Path(original_name).stem

    # Add year if available
    if book_info.publish_date:
        year = book_info.publish_date[:4]
        if year.isdigit():
            filename = f"{filename} ({year})"

    # Ensure extension starts with dot
    if not extension.startswith("."):
        extension = f".{extension}"

    return f"{filename}{extension}"


def _extract_isbns_from_file(file_path: Path) -> list[str] | None:
    """Extract ISBNs from a book file based on its type.

    Args:
        file_path: Path to the book file (PDF, CHM, or EPUB).

    Returns:
        List of ISBNs found, or None if extraction fails.
    """
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        pdf_meta = extract_pdf_metadata(file_path)
        return pdf_meta.isbns if pdf_meta else None

    if ext == ".chm":
        chm_meta = extract_chm_metadata(file_path)
        return chm_meta.isbns if chm_meta else None

    if ext == ".epub":
        epub_meta = extract_epub_metadata(file_path)
        return epub_meta.isbns if epub_meta else None

    return None


def _detect_book(
    file_path: Path,
    para_root: Path,
    *,
    rename: bool = True,
) -> dict[str, str | Path] | None:
    """Detect book metadata from a book file (PDF, CHM, or EPUB).

    Args:
        file_path: Path to the book file.
        para_root: PARA root directory.
        rename: If True, build new filename using book title.

    Returns:
        Dict with book info and destination paths, or None if not a book.
    """
    # Check supported extension
    ext = file_path.suffix.lower()
    if ext not in BOOK_EXTENSIONS:
        return None

    # Extract ISBNs based on file type
    isbns = _extract_isbns_from_file(file_path)
    if not isbns:
        return None

    # Find matching book info with ISBN coherence validation
    book_info, matched_isbn = find_matching_book_info(
        isbns,
        file_path.name,
        require_coherence=True,
    )
    if book_info is None or matched_isbn is None:
        logger.debug("No matching ISBN found for {}", file_path.name)
        return None

    # Get Thema classification
    thema_lookup = get_thema_lookup()
    thema_code: str | None = None

    # Try to detect Thema from subjects
    if book_info.subjects:
        thema_code = thema_lookup.lookup_subjects(book_info.subjects)

    # Try description
    if not thema_code and book_info.description:
        thema_code = thema_lookup.lookup_from_text(book_info.description)

    # Try title
    if not thema_code and book_info.title:
        thema_code = thema_lookup.lookup_from_text(book_info.title)

    # Default to Computing/IT
    if not thema_code:
        thema_code = "U"

    # Build destination path
    category = thema_lookup.build_para_path(thema_code)
    dest_dir = para_root / category

    # Build filename (preserve original extension)
    if rename and book_info.title:
        new_filename = _build_book_filename(book_info, file_path.name, ext)
    else:
        new_filename = file_path.name

    # Return detection info (no move yet)
    return {
        "source": file_path,
        "isbn": matched_isbn,
        "title": book_info.title or "Unknown",
        "authors": ", ".join(book_info.authors) if book_info.authors else "Unknown",
        "thema": thema_code,
        "category": category,
        "dest_dir": dest_dir,
        "new_filename": new_filename,
    }


def _display_book_info(
    result: dict[str, str | Path],
    original_name: str,
    destination: Path,
    *,
    dry_run: bool,
    rename: bool,
) -> None:
    """Display book information to the user."""
    action = "Would move" if dry_run else "Moved"
    typer.echo(f"📖 {result['title']}")
    typer.echo(f"   ISBN: {result['isbn']}")
    typer.echo(f"   Authors: {result['authors']}")
    typer.echo(f"   Thema: {result['thema']} → {result['category']}")
    new_filename = str(result["new_filename"])
    if rename and new_filename != original_name:
        typer.echo(f"   Renamed: {new_filename}")
    typer.echo(f"   {action}: {destination}")
    typer.echo()


def _display_summary(
    total_files: int,
    books_found: int,
    books_moved: int,
    duplicates_skipped: int,
    content_duplicates: int,
    *,
    dry_run: bool,
) -> None:
    """Display summary of bookstore operation."""
    typer.echo("─" * 60)
    typer.echo(f"📚 Found {books_found} unique books with ISBN out of {total_files} files")
    if duplicates_skipped > 0:
        typer.echo(f"⏭️  Skipped {duplicates_skipped} ISBN duplicate(s)")
    if content_duplicates > 0:
        typer.echo(f"🔄 Removed {content_duplicates} content duplicate(s)")
    if not dry_run:
        typer.echo(f"✅ Moved {books_moved} books to PARA structure")
    else:
        typer.echo("(i) Run without --dry-run to move files")


def _find_book_files(path: Path, *, recursive: bool) -> list[Path]:
    """Find all book files (PDF, CHM, EPUB) in a directory.

    Args:
        path: Directory to search.
        recursive: Whether to search subdirectories.

    Returns:
        List of paths to book files.
    """
    book_files: list[Path] = []
    for ext in BOOK_EXTENSIONS:
        pattern = f"*{ext}"
        if recursive:
            book_files.extend(path.rglob(pattern))
            # Also handle uppercase extensions
            book_files.extend(path.rglob(pattern.upper()))
        else:
            book_files.extend(path.glob(pattern))
            book_files.extend(path.glob(pattern.upper()))
    return book_files


@app.command()
def bookstore(
    path: Annotated[
        Path,
        typer.Argument(
            help="Directory to scan for books",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-n",
            help="Preview changes without moving files",
        ),
    ] = False,
    no_rename: Annotated[
        bool,
        typer.Option(
            "--no-rename",
            help="Keep original filenames instead of renaming",
        ),
    ] = False,
    recursive: Annotated[
        bool,
        typer.Option(
            "--recursive",
            "-R",
            help="Scan subdirectories recursively",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed output",
        ),
    ] = False,
) -> None:
    """Scan directory for books with ISBN and organize by Thema classification.

    Supports PDF, CHM (Microsoft Help), and EPUB files. Only moves files that
    have a confirmed ISBN. Uses Google Books API to lookup book metadata and
    Thema codes for classification.

    Examples:
        # Preview books in Downloads folder
        para-files bookstore ~/Downloads --dry-run

        # Move books from a folder
        para-files bookstore /path/to/books

        # Recursive scan without renaming
        para-files bookstore /path/to/books -R --no-rename
    """
    setup_logging(verbose=verbose)
    validate_directory_or_exit(path)
    config = load_config_or_exit()

    para_root = Path(config.para_root).expanduser()

    # Find book files (PDF, CHM, EPUB)
    book_files = _find_book_files(path, recursive=recursive)

    if not book_files:
        exts = ", ".join(BOOK_EXTENSIONS)
        typer.echo(f"No book files ({exts}) found in {path}")
        raise typer.Exit(0)

    typer.echo(f"📚 Scanning {len(book_files)} book files for ISBN...")
    if dry_run:
        typer.echo("   (dry-run mode - no files will be moved)")
    typer.echo()

    # Create FileMover for deduplication and conflict handling
    mover = FileMover(dry_run=dry_run, deduplicate=True)

    # Process files with ISBN deduplication
    books_found = 0
    books_moved = 0
    duplicates_skipped = 0
    content_duplicates = 0
    processed_isbns: dict[str, Path] = {}  # ISBN -> first file path

    for book_file in book_files:
        # Detect book metadata
        result = _detect_book(
            book_file,
            para_root,
            rename=not no_rename,
        )

        if result:
            isbn = str(result["isbn"])

            # Check for duplicate ISBN (same book, different file)
            if isbn in processed_isbns:
                duplicates_skipped += 1
                if verbose:
                    typer.echo(f"⏭️  Skipping duplicate: {book_file.name}")
                    first_file = processed_isbns[isbn].name
                    typer.echo(f"   ISBN {isbn} already processed from: {first_file}")
                    typer.echo()
                continue

            # Track this ISBN
            processed_isbns[isbn] = book_file
            books_found += 1

            # Build destination path
            dest_dir = result["dest_dir"]
            new_filename = str(result["new_filename"])
            dest_path = Path(dest_dir) / new_filename

            # Move file using FileMover (handles content deduplication)
            move_result = mover.move(book_file, dest_path)

            # Check if it was a content duplicate
            if move_result.action and "duplicate" in move_result.action:
                content_duplicates += 1
                if verbose:
                    typer.echo(f"🔄 Content duplicate: {book_file.name}")
                    typer.echo(f"   Identical to: {dest_path}")
                    typer.echo()
                continue

            _display_book_info(
                result,
                book_file.name,
                move_result.destination or dest_path,
                dry_run=dry_run,
                rename=not no_rename,
            )

            if not dry_run and move_result.success:
                books_moved += 1

    # Summary
    _display_summary(
        len(book_files),
        books_found,
        books_moved,
        duplicates_skipped,
        content_duplicates,
        dry_run=dry_run,
    )
