"""Cleanup utilities for Apple/Windows temp files and junk."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from loguru import logger


# Patterns for junk files that should be deleted automatically
JUNK_PATTERNS: list[str] = [
    # macOS
    ".DS_Store",
    "._*",  # AppleDouble shadow files
    ".AppleDouble",
    ".AppleDB",
    ".AppleDesktop",
    ".Spotlight-V100",
    ".Trashes",
    ".TemporaryItems",
    ".fseventsd",
    ".metadata_never_index",
    ".metadata_never_index_unless_rootfs",
    ".NetworkTrashFolder",
    "Network Trash Folder",
    "Temporary Items",
    ".apdisk",
    ".VolumeIcon.icns",
    # Windows
    "desktop.ini",
    "Thumbs.db",
    "ehthumbs.db",
    "ehthumbs_vista.db",
    "$RECYCLE.BIN",
    "*.lnk",
    # Linux
    ".directory",
    "*~",  # Backup files
    ".Trash-*",
]

# Directories that are entirely junk (should be deleted with contents)
JUNK_DIRECTORIES: list[str] = [
    ".Spotlight-V100",
    ".Trashes",
    ".TemporaryItems",
    ".fseventsd",
    ".AppleDouble",
    ".AppleDB",
    ".AppleDesktop",
    "$RECYCLE.BIN",
    ".Trash-*",
]


def is_junk_file(path: Path) -> bool:
    """Check if a file matches known junk/temp file patterns.

    Args:
        path: Path to check

    Returns:
        True if the file is a known junk file that should be deleted
    """
    name = path.name
    return any(fnmatch.fnmatch(name, pattern) for pattern in JUNK_PATTERNS)


def is_junk_directory(path: Path) -> bool:
    """Check if a directory matches known junk directory patterns.

    Args:
        path: Path to check

    Returns:
        True if the directory is a known junk directory
    """
    if not path.is_dir():
        return False

    name = path.name
    return any(fnmatch.fnmatch(name, pattern) for pattern in JUNK_DIRECTORIES)


def delete_junk_file(path: Path, *, dry_run: bool = True) -> bool:
    """Delete a junk file with dry-run support.

    Args:
        path: Path to the file to delete
        dry_run: If True, only log what would be deleted

    Returns:
        True if file was deleted (or would be in dry-run mode)
    """
    if not path.exists():
        return False

    if not is_junk_file(path):
        logger.warning("Refusing to delete non-junk file: %s", path)
        return False

    if dry_run:
        logger.info("[DRY-RUN] Would delete junk file: %s", path)
    else:
        try:
            path.unlink()
            logger.info("Deleted junk file: %s", path)
        except OSError:
            logger.exception("Failed to delete %s", path)
            return False

    return True


def delete_junk_directory(path: Path, *, dry_run: bool = True) -> bool:
    """Delete a junk directory and its contents.

    Args:
        path: Path to the directory to delete
        dry_run: If True, only log what would be deleted

    Returns:
        True if directory was deleted (or would be in dry-run mode)
    """
    if not path.exists():
        return False

    if not is_junk_directory(path):
        logger.warning("Refusing to delete non-junk directory: %s", path)
        return False

    if dry_run:
        logger.info("[DRY-RUN] Would delete junk directory: %s", path)
    else:
        try:
            import shutil

            shutil.rmtree(path)
            logger.info("Deleted junk directory: %s", path)
        except OSError:
            logger.exception("Failed to delete directory %s", path)
            return False

    return True


def cleanup_empty_dirs(root: Path, *, dry_run: bool = True) -> list[Path]:
    """Remove empty directories recursively (bottom-up).

    Args:
        root: Root directory to scan
        dry_run: If True, only report what would be deleted

    Returns:
        List of deleted (or would-be-deleted) directories
    """
    deleted: list[Path] = []

    if not root.is_dir():
        return deleted

    # Process bottom-up by sorting paths in reverse order (deepest first)
    all_dirs = sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True)

    for dirpath in all_dirs:
        if not dirpath.is_dir():
            continue

        # Check if directory is empty (no files or subdirs)
        try:
            if not any(dirpath.iterdir()):
                if dry_run:
                    logger.info("[DRY-RUN] Would delete empty directory: %s", dirpath)
                else:
                    try:
                        dirpath.rmdir()
                        logger.info("Deleted empty directory: %s", dirpath)
                    except OSError:
                        logger.exception("Failed to delete empty dir %s", dirpath)
                        continue
                deleted.append(dirpath)
        except PermissionError:
            logger.warning("Permission denied accessing: %s", dirpath)

    return deleted


def scan_for_junk(
    root: Path,
    *,
    recursive: bool = True,
) -> tuple[list[Path], list[Path]]:
    """Scan directory for junk files and directories.

    Args:
        root: Directory to scan
        recursive: Whether to scan subdirectories

    Returns:
        Tuple of (junk_files, junk_directories)
    """
    junk_files: list[Path] = []
    junk_dirs: list[Path] = []

    if not root.is_dir():
        return junk_files, junk_dirs

    items = list(root.rglob("*")) if recursive else list(root.iterdir())

    for item in items:
        if item.is_file() and is_junk_file(item):
            junk_files.append(item)
        elif item.is_dir() and is_junk_directory(item):
            junk_dirs.append(item)

    return junk_files, junk_dirs


def cleanup_junk(
    root: Path,
    *,
    recursive: bool = True,
    dry_run: bool = True,
) -> tuple[list[Path], list[Path]]:
    """Clean up all junk files and directories in a path.

    Args:
        root: Directory to clean
        recursive: Whether to scan subdirectories
        dry_run: If True, only report what would be deleted

    Returns:
        Tuple of (deleted_files, deleted_directories)
    """
    junk_files, junk_dirs = scan_for_junk(root, recursive=recursive)

    # Delete files first
    deleted_files = [f for f in junk_files if delete_junk_file(f, dry_run=dry_run)]

    # Then delete directories (children might be inside junk dirs)
    deleted_dirs = [d for d in junk_dirs if delete_junk_directory(d, dry_run=dry_run)]

    return deleted_files, deleted_dirs
