"""Bookstore command for para-files CLI.

This module provides the 'bookstore' command which scans a directory
for PDF books with ISBN and moves them to the appropriate Thema-classified
location in the PARA structure.

Only books with confirmed ISBN are moved (100% confidence).
"""

from __future__ import annotations

import shutil
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
from para_files.utils.isbn_lookup import BookInfo, lookup_isbn
from para_files.utils.pdf_metadata import extract_pdf_metadata
from para_files.utils.thema_lookup import get_thema_lookup


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


def _build_book_filename(book_info: BookInfo, original_name: str) -> str:
    """Build a clean filename for a book.

    Format: "Author - Title (Year).pdf"

    Args:
        book_info: Book information from ISBN lookup.
        original_name: Original filename as fallback.

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
        filename = original_name.replace(".pdf", "")

    # Add year if available
    if book_info.publish_date:
        year = book_info.publish_date[:4]
        if year.isdigit():
            filename = f"{filename} ({year})"

    return f"{filename}.pdf"


def _process_book(
    file_path: Path,
    para_root: Path,
    *,
    dry_run: bool = False,
    rename: bool = True,
) -> dict[str, str] | None:
    """Process a single PDF file for book detection.

    Args:
        file_path: Path to the PDF file.
        para_root: PARA root directory.
        dry_run: If True, don't actually move files.
        rename: If True, rename files using book title.

    Returns:
        Dict with book info if ISBN found and processed, None otherwise.
    """
    # Extract PDF metadata
    pdf_meta = extract_pdf_metadata(file_path)
    if pdf_meta is None or not pdf_meta.isbn:
        return None

    # Lookup ISBN
    book_info = lookup_isbn(pdf_meta.isbn)
    if book_info is None:
        logger.debug("ISBN {} lookup failed for {}", pdf_meta.isbn, file_path.name)
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

    # Build filename
    if rename and book_info.title:
        new_filename = _build_book_filename(book_info, file_path.name)
    else:
        new_filename = file_path.name

    dest_path = dest_dir / new_filename

    # Result info
    result = {
        "source": str(file_path),
        "isbn": pdf_meta.isbn,
        "title": book_info.title or "Unknown",
        "authors": ", ".join(book_info.authors) if book_info.authors else "Unknown",
        "thema": thema_code,
        "category": category,
        "destination": str(dest_path),
        "new_filename": new_filename,
    }

    if not dry_run:
        # Create destination directory
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Handle conflicts
        if dest_path.exists():
            # Add ISBN to filename to make unique
            stem = dest_path.stem
            dest_path = dest_dir / f"{stem}_{pdf_meta.isbn}.pdf"
            result["destination"] = str(dest_path)
            result["new_filename"] = dest_path.name

        # Move file
        shutil.move(str(file_path), str(dest_path))
        logger.info("Moved: {} → {}", file_path.name, dest_path)

    return result


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
            "-r",
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

    Only moves PDF files that have a confirmed ISBN. Uses Google Books API
    to lookup book metadata and Thema codes for classification.

    Examples:
        # Preview books in Downloads folder
        para-files bookstore ~/Downloads --dry-run

        # Move books from a folder
        para-files bookstore /path/to/books

        # Recursive scan without renaming
        para-files bookstore /path/to/books -r --no-rename
    """
    setup_logging(verbose=verbose)
    validate_directory_or_exit(path)
    config = load_config_or_exit()

    para_root = Path(config.para_root).expanduser()

    # Find PDF files
    pattern = "*.pdf"
    pdf_files = list(path.rglob(pattern) if recursive else path.glob(pattern))

    if not pdf_files:
        typer.echo(f"No PDF files found in {path}")
        raise typer.Exit(0)

    typer.echo(f"📚 Scanning {len(pdf_files)} PDF files for books with ISBN...")
    if dry_run:
        typer.echo("   (dry-run mode - no files will be moved)")
    typer.echo()

    # Process files
    books_found = 0
    books_moved = 0

    for pdf_file in pdf_files:
        result = _process_book(
            pdf_file,
            para_root,
            dry_run=dry_run,
            rename=not no_rename,
        )

        if result:
            books_found += 1
            action = "Would move" if dry_run else "Moved"

            typer.echo(f"📖 {result['title']}")
            typer.echo(f"   ISBN: {result['isbn']}")
            typer.echo(f"   Authors: {result['authors']}")
            typer.echo(f"   Thema: {result['thema']} → {result['category']}")
            if not no_rename and result["new_filename"] != pdf_file.name:
                typer.echo(f"   Renamed: {result['new_filename']}")
            typer.echo(f"   {action}: {result['destination']}")
            typer.echo()

            if not dry_run:
                books_moved += 1

    # Summary
    typer.echo("─" * 60)
    typer.echo(f"📚 Found {books_found} books with ISBN out of {len(pdf_files)} PDFs")
    if not dry_run:
        typer.echo(f"✅ Moved {books_moved} books to PARA structure")
    else:
        typer.echo("(i) Run without --dry-run to move files")
