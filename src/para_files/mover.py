"""File mover for classified files.

Handles moving/copying files to their PARA destinations with conflict resolution.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from pydantic import BaseModel, Field


if TYPE_CHECKING:
    from para_files.types import ClassificationResult


# Maximum number of rename attempts before failing
_MAX_RENAME_ATTEMPTS = 1000

# Buffer size for file hashing (64KB)
_HASH_BUFFER_SIZE = 65536


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Hexadecimal hash string.
    """
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(_HASH_BUFFER_SIZE):
            sha256.update(chunk)
    return sha256.hexdigest()


def files_are_identical(file1: Path, file2: Path) -> bool:
    """Check if two files are identical by comparing size then hash.

    Args:
        file1: First file path.
        file2: Second file path.

    Returns:
        True if files have identical content.
    """
    # Quick check: different sizes means different files
    if file1.stat().st_size != file2.stat().st_size:
        return False

    # Same size: compare hashes
    return _compute_file_hash(file1) == _compute_file_hash(file2)


class ConflictStrategy(StrEnum):
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
    - Smart rename (use suggested name from classification)
    """

    def __init__(
        self,
        *,
        dry_run: bool = False,
        copy_mode: bool = False,
        conflict_strategy: ConflictStrategy = ConflictStrategy.RENAME,
        add_date_prefix: bool = False,
        smart_rename: bool = False,
        deduplicate: bool = True,
    ) -> None:
        """Initialize the file mover.

        Args:
            dry_run: If True, don't actually move files, just report what would happen.
            copy_mode: If True, copy files instead of moving them.
            conflict_strategy: How to handle existing files at destination.
            add_date_prefix: If True, add date prefix to filename (YYYY-MM-DD_).
            smart_rename: If True, use suggested name from classification (e.g., book title).
            deduplicate: If True, delete source when destination has identical content.
        """
        self.dry_run = dry_run
        self.copy_mode = copy_mode
        self.conflict_strategy = conflict_strategy
        self.add_date_prefix = add_date_prefix
        self.smart_rename = smart_rename
        self.deduplicate = deduplicate

    def move(
        self,
        source: Path,
        destination_dir: Path,
        classification: ClassificationResult | None = None,
    ) -> MoveResult:
        """Move or copy a file to the destination directory.

        Args:
            source: Source file path.
            destination_dir: Target directory (will be created if needed).
            classification: Optional classification result for smart renaming.

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
        filename = self._build_filename(source, classification)
        initial_destination = destination_dir / filename

        # CRITICAL: Never delete if source and destination are the same file
        # This can happen when re-classifying files already in their correct location
        try:
            if source.resolve() == initial_destination.resolve():
                logger.debug("Source and destination are the same file, skipping: {}", source)
                return MoveResult(
                    source=source,
                    destination=initial_destination,
                    success=True,
                    action="skipped",
                    message="File already in correct location",
                )
        except OSError:
            # If we can't resolve paths, check string equality as fallback
            if str(source.absolute()) == str(initial_destination.absolute()):
                return MoveResult(
                    source=source,
                    destination=initial_destination,
                    success=True,
                    action="skipped",
                    message="File already in correct location",
                )

        # Check for duplicate before applying conflict strategy
        if (
            initial_destination.exists()
            and self.deduplicate
            and files_are_identical(source, initial_destination)
        ):
            return self._handle_duplicate(source, initial_destination)

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

    def _build_filename(
        self,
        source: Path,
        classification: ClassificationResult | None = None,
    ) -> str:
        """Build the destination filename, optionally with smart rename or date prefix.

        Args:
            source: Source file path.
            classification: Optional classification result for smart renaming.

        Returns:
            Filename string.
        """
        # Use suggested name from classification if smart_rename is enabled
        if self.smart_rename and classification:
            suggested_name = classification.extracted_params.get("suggested_name")
            if suggested_name:
                # Preserve original extension
                base_name = f"{suggested_name}{source.suffix}"
                logger.debug("Smart rename: {} → {}", source.name, base_name)

                if self.add_date_prefix:
                    mtime = datetime.fromtimestamp(source.stat().st_mtime, tz=UTC)
                    date_prefix = mtime.strftime("%Y-%m-%d")
                    return f"{date_prefix}_{base_name}"
                return base_name

        # Default behavior: use original filename
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

    def _handle_duplicate(self, source: Path, destination: Path) -> MoveResult:
        """Handle duplicate file by deleting source.

        Args:
            source: Source file path (duplicate to delete).
            destination: Destination file path (existing file to keep).

        Returns:
            MoveResult indicating duplicate was removed.
        """
        # CRITICAL SAFETY: Never delete if source and destination are the same file
        try:
            if source.resolve() == destination.resolve():
                logger.warning("SAFETY: Prevented deletion of source=destination: {}", source)
                return MoveResult(
                    source=source,
                    destination=destination,
                    success=True,
                    action="skipped",
                    message="File already in correct location (same file)",
                )
        except OSError:
            pass  # If resolve fails, proceed with caution below

        if self.dry_run:
            return MoveResult(
                source=source,
                destination=destination,
                success=True,
                action="would delete duplicate",
                message=f"Dry run: {source} is identical to {destination}, would delete source",
            )

        try:
            source.unlink()
            logger.info("Deleted duplicate: {} (identical to {})", source, destination)
            return MoveResult(
                source=source,
                destination=destination,
                success=True,
                action="deleted duplicate",
                message=f"Identical file already exists at {destination}",
            )
        except OSError as e:
            logger.exception("Failed to delete duplicate: {}", source)
            return MoveResult(
                source=source,
                destination=destination,
                success=False,
                action="error",
                message=f"Failed to delete duplicate: {e}",
            )

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

            logger.info("{}: {} -> {}", action.capitalize(), source, destination)

            return MoveResult(
                source=source,
                destination=destination,
                success=True,
                action=action,
                message="",
            )

        except OSError as e:
            logger.exception("Failed to {} file: {}", action.rstrip("d"), source)
            return MoveResult(
                source=source,
                destination=destination,
                success=False,
                action="error",
                message=str(e),
            )


def move_classified_file(  # noqa: PLR0913
    source: Path,
    target_dir: Path,
    *,
    dry_run: bool = False,
    copy_mode: bool = False,
    conflict_strategy: ConflictStrategy = ConflictStrategy.RENAME,
    add_date_prefix: bool = False,
    smart_rename: bool = False,
    deduplicate: bool = True,
    classification: ClassificationResult | None = None,
) -> MoveResult:
    """Convenience function to move a single classified file.

    Args:
        source: Source file path.
        target_dir: Target directory from classification result.
        dry_run: Preview mode without actual changes.
        copy_mode: Copy instead of move.
        conflict_strategy: How to handle existing files.
        add_date_prefix: Add date prefix to filename.
        smart_rename: Use suggested name from classification (e.g., book title).
        deduplicate: Delete source if destination has identical content.
        classification: Optional classification result for smart renaming.

    Returns:
        MoveResult with operation details.
    """
    mover = FileMover(
        dry_run=dry_run,
        copy_mode=copy_mode,
        conflict_strategy=conflict_strategy,
        add_date_prefix=add_date_prefix,
        smart_rename=smart_rename,
        deduplicate=deduplicate,
    )
    return mover.move(source, target_dir, classification)


def validate_destination_permissions(destinations: set[Path]) -> list[Path]:
    """Pre-flight check: validate write permissions for all unique destination directories.

    For directories that don't exist yet, checks the nearest existing parent.

    Args:
        destinations: Set of destination directory paths to check.

    Returns:
        List of paths that are NOT writable (empty if all OK).
    """
    unwritable: list[Path] = []
    for dest in destinations:
        check_path = dest
        # Walk up to find an existing directory
        while not check_path.exists():
            check_path = check_path.parent
            if check_path == check_path.parent:  # reached filesystem root
                break
        if not os.access(check_path, os.W_OK):
            unwritable.append(dest)
    return unwritable


class BatchMoveResult(BaseModel):
    """Result of a batch move operation with rollback capability."""

    results: list[MoveResult] = Field(
        default_factory=list,
        description="Results for each file attempted",
    )
    completed_moves: list[tuple[Path, Path]] = Field(
        default_factory=list,
        description="(source, destination) pairs for successful moves",
    )
    total: int = Field(default=0, description="Total files in batch")
    succeeded: int = Field(default=0, description="Successfully moved")
    failed_at: int | None = Field(
        default=None,
        description="Index where failure occurred (None if all succeeded)",
    )
    failure_message: str = Field(default="", description="Error message from the failed move")

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


class BatchMover:
    """Moves files in batch with stop-on-failure and rollback support.

    Tracks every completed move as a (source, destination) tuple.
    On first failure: stops immediately, offers rollback of completed moves.
    """

    def __init__(
        self,
        *,
        dry_run: bool = False,
        copy_mode: bool = False,
        conflict_strategy: ConflictStrategy = ConflictStrategy.RENAME,
        add_date_prefix: bool = False,
        smart_rename: bool = False,
        deduplicate: bool = True,
    ) -> None:
        """Initialize the batch mover.

        Args:
            dry_run: If True, simulate operations without moving files.
            copy_mode: If True, copy files instead of moving.
            conflict_strategy: How to handle existing files at destination.
            add_date_prefix: If True, add date prefix to filename.
            smart_rename: If True, use suggested name from classification.
            deduplicate: If True, delete source when destination has identical content.
        """
        self._mover = FileMover(
            dry_run=dry_run,
            copy_mode=copy_mode,
            conflict_strategy=conflict_strategy,
            add_date_prefix=add_date_prefix,
            smart_rename=smart_rename,
            deduplicate=deduplicate,
        )
        self._dry_run = dry_run
        self._completed_moves: list[tuple[Path, Path]] = []

    @property
    def completed_moves(self) -> list[tuple[Path, Path]]:
        """Return a copy of (source, destination) pairs for successfully completed moves."""
        return self._completed_moves.copy()

    def move_batch(
        self,
        items: list[tuple[Path, Path, ClassificationResult | None]],
    ) -> BatchMoveResult:
        """Move a batch of files, stopping on first failure.

        Args:
            items: List of (source, destination_dir, classification) tuples.

        Returns:
            BatchMoveResult with results and rollback info.
        """
        self._completed_moves.clear()
        results: list[MoveResult] = []

        for idx, (source, dest_dir, classification) in enumerate(items):
            move_result = self._mover.move(source, dest_dir, classification)
            results.append(move_result)

            if move_result.success and move_result.action not in (
                "skipped",
                "would be moved",
                "would be copied",
            ):
                self._completed_moves.append((source, move_result.destination))

            if not move_result.success:
                return BatchMoveResult(
                    results=results,
                    completed_moves=self._completed_moves.copy(),
                    total=len(items),
                    succeeded=len(self._completed_moves),
                    failed_at=idx,
                    failure_message=move_result.message,
                )

        return BatchMoveResult(
            results=results,
            completed_moves=self._completed_moves.copy(),
            total=len(items),
            succeeded=len(self._completed_moves),
        )

    def rollback(self) -> list[MoveResult]:
        """Roll back all completed moves, returning files to original locations.

        Processes in LIFO order. Rollback failures are logged as warnings, not
        hard errors — callers receive the full list of rollback results.

        Returns:
            List of MoveResult for each rollback operation.
        """
        rollback_results: list[MoveResult] = []

        # Reverse order to undo in LIFO order
        for source, destination in reversed(self._completed_moves):
            if self._dry_run:
                rollback_results.append(
                    MoveResult(
                        source=destination,
                        destination=source,
                        success=True,
                        action="would rollback",
                        message=f"Dry run: would move {destination} back to {source}",
                    )
                )
                continue

            try:
                shutil.move(str(destination), str(source))
                logger.info("Rolled back: {} -> {}", destination, source)
                rollback_results.append(
                    MoveResult(
                        source=destination,
                        destination=source,
                        success=True,
                        action="rolled back",
                    )
                )
            except OSError as e:
                logger.warning("Rollback failed for {} -> {}: {}", destination, source, e)
                rollback_results.append(
                    MoveResult(
                        source=destination,
                        destination=source,
                        success=False,
                        action="rollback failed",
                        message=str(e),
                    )
                )

        self._completed_moves.clear()
        return rollback_results
