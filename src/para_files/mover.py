"""File mover for classified files.

Handles moving/copying files to their PARA destinations with conflict resolution.
"""

from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


# Maximum number of rename attempts before failing
_MAX_RENAME_ATTEMPTS = 1000


logger = logging.getLogger(__name__)


class ConflictStrategy(str, Enum):
    """Strategy for handling filename conflicts."""

    SKIP = "skip"  # Skip if file exists
    OVERWRITE = "overwrite"  # Overwrite existing file
    RENAME = "rename"  # Add counter suffix (file_1.txt, file_2.txt)
    RENAME_WITH_DATE = "rename_with_date"  # Add date prefix (2025-01-15_file.txt)


class MoveResult(BaseModel):
    """Result of a file move operation."""

    source: Path = Field(description="Original file path")
    destination: Path = Field(description="Target file path")
    success: bool = Field(description="Whether the operation succeeded")
    action: str = Field(description="Action taken: moved, copied, skipped, error")
    message: str = Field(default="", description="Additional details or error message")

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


class FileMover:
    """Moves or copies files to PARA destinations.

    Features:
    - Dry-run mode for previewing changes
    - Multiple conflict resolution strategies
    - Optional date-based renaming
    - Copy mode (preserve original)
    """

    def __init__(
        self,
        *,
        dry_run: bool = False,
        copy_mode: bool = False,
        conflict_strategy: ConflictStrategy = ConflictStrategy.RENAME,
        add_date_prefix: bool = False,
    ) -> None:
        """Initialize the file mover.

        Args:
            dry_run: If True, don't actually move files, just report what would happen.
            copy_mode: If True, copy files instead of moving them.
            conflict_strategy: How to handle existing files at destination.
            add_date_prefix: If True, add date prefix to filename (YYYY-MM-DD_).
        """
        self.dry_run = dry_run
        self.copy_mode = copy_mode
        self.conflict_strategy = conflict_strategy
        self.add_date_prefix = add_date_prefix

    def move(self, source: Path, destination_dir: Path) -> MoveResult:
        """Move or copy a file to the destination directory.

        Args:
            source: Source file path.
            destination_dir: Target directory (will be created if needed).

        Returns:
            MoveResult with operation details.
        """
        if not source.exists():
            return MoveResult(
                source=source,
                destination=destination_dir / source.name,
                success=False,
                action="error",
                message=f"Source file does not exist: {source}",
            )

        if not source.is_file():
            return MoveResult(
                source=source,
                destination=destination_dir / source.name,
                success=False,
                action="error",
                message=f"Source is not a file: {source}",
            )

        # Build destination filename
        filename = self._build_filename(source)
        initial_destination = destination_dir / filename

        # Handle conflicts
        resolved_destination = self._resolve_conflict(initial_destination)
        if resolved_destination is None:
            return MoveResult(
                source=source,
                destination=initial_destination,
                success=True,
                action="skipped",
                message="File already exists, skipped per conflict strategy",
            )

        # Create target directory
        if not self.dry_run:
            resolved_destination.parent.mkdir(parents=True, exist_ok=True)

        # Perform the operation
        return self._execute_move(source, resolved_destination)

    def _build_filename(self, source: Path) -> str:
        """Build the destination filename, optionally with date prefix.

        Args:
            source: Source file path.

        Returns:
            Filename string.
        """
        if not self.add_date_prefix:
            return source.name

        # Use file modification date for prefix
        mtime = datetime.fromtimestamp(source.stat().st_mtime, tz=UTC)
        date_prefix = mtime.strftime("%Y-%m-%d")
        return f"{date_prefix}_{source.name}"

    def _resolve_conflict(self, destination: Path) -> Path | None:
        """Resolve filename conflict based on strategy.

        Args:
            destination: Initial destination path.

        Returns:
            Resolved path, or None if file should be skipped.
        """
        if not destination.exists():
            return destination

        if self.conflict_strategy == ConflictStrategy.SKIP:
            return None

        if self.conflict_strategy == ConflictStrategy.OVERWRITE:
            return destination

        if self.conflict_strategy == ConflictStrategy.RENAME:
            return self._find_unique_name(destination)

        # RENAME_WITH_DATE: Add current timestamp to make unique
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        stem = destination.stem
        suffix = destination.suffix
        return destination.with_name(f"{stem}_{timestamp}{suffix}")

    def _find_unique_name(self, destination: Path) -> Path:
        """Find a unique filename by adding a counter suffix.

        Args:
            destination: Original destination path.

        Returns:
            Unique path with counter suffix.
        """
        stem = destination.stem
        suffix = destination.suffix
        parent = destination.parent

        counter = 1
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
            if counter > _MAX_RENAME_ATTEMPTS:
                # Safety limit
                msg = f"Too many conflicts for {destination}"
                raise RuntimeError(msg)

    def _execute_move(self, source: Path, destination: Path) -> MoveResult:
        """Execute the actual move or copy operation.

        Args:
            source: Source file path.
            destination: Destination file path.

        Returns:
            MoveResult with operation details.
        """
        action = "copied" if self.copy_mode else "moved"

        if self.dry_run:
            return MoveResult(
                source=source,
                destination=destination,
                success=True,
                action=f"would be {action}",
                message=f"Dry run: {source} -> {destination}",
            )

        try:
            if self.copy_mode:
                shutil.copy2(source, destination)
            else:
                shutil.move(source, destination)

            logger.info("%s: %s -> %s", action.capitalize(), source, destination)

            return MoveResult(
                source=source,
                destination=destination,
                success=True,
                action=action,
                message="",
            )

        except OSError as e:
            logger.exception("Failed to %s file: %s", action.rstrip("d"), source)
            return MoveResult(
                source=source,
                destination=destination,
                success=False,
                action="error",
                message=str(e),
            )


def move_classified_file(
    source: Path,
    target_dir: Path,
    *,
    dry_run: bool = False,
    copy_mode: bool = False,
    conflict_strategy: ConflictStrategy = ConflictStrategy.RENAME,
    add_date_prefix: bool = False,
) -> MoveResult:
    """Convenience function to move a single classified file.

    Args:
        source: Source file path.
        target_dir: Target directory from classification result.
        dry_run: Preview mode without actual changes.
        copy_mode: Copy instead of move.
        conflict_strategy: How to handle existing files.
        add_date_prefix: Add date prefix to filename.

    Returns:
        MoveResult with operation details.
    """
    mover = FileMover(
        dry_run=dry_run,
        copy_mode=copy_mode,
        conflict_strategy=conflict_strategy,
        add_date_prefix=add_date_prefix,
    )
    return mover.move(source, target_dir)
