"""Audit logging for cleanup operations."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class CleanupLogEntry:
    """A single cleanup operation log entry."""

    timestamp: str
    action: str  # "deleted", "skipped", "error"
    path: str
    file_type: str  # "junk_file", "junk_dir", "empty_dir", "nfo"
    reason: str
    dry_run: bool = False

    @classmethod
    def create(
        cls,
        action: str,
        path: Path,
        file_type: str,
        reason: str,
        *,
        dry_run: bool = False,
    ) -> CleanupLogEntry:
        """Create a new log entry with current timestamp."""
        return cls(
            timestamp=datetime.now(UTC).isoformat(),
            action=action,
            path=str(path),
            file_type=file_type,
            reason=reason,
            dry_run=dry_run,
        )


class CleanupLogger:
    """Logger for cleanup operations with JSON file output."""

    def __init__(self, log_path: Path | None = None) -> None:
        """Initialize cleanup logger.

        Args:
            log_path: Path to the log file. If None, logging to file is disabled.
        """
        self.log_path = log_path
        self.entries: list[CleanupLogEntry] = []
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        """Create log directory if it doesn't exist."""
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_deleted(
        self,
        path: Path,
        file_type: str,
        reason: str,
        *,
        dry_run: bool = False,
    ) -> None:
        """Log a deleted file/directory."""
        action = "would_delete" if dry_run else "deleted"
        entry = CleanupLogEntry.create(action, path, file_type, reason, dry_run=dry_run)
        self.entries.append(entry)
        logger.info("[%s] %s: %s (%s)", action.upper(), file_type, path, reason)

    def log_skipped(
        self,
        path: Path,
        file_type: str,
        reason: str,
    ) -> None:
        """Log a skipped file/directory."""
        entry = CleanupLogEntry.create("skipped", path, file_type, reason)
        self.entries.append(entry)
        logger.debug("[SKIPPED] %s: %s (%s)", file_type, path, reason)

    def log_error(
        self,
        path: Path,
        file_type: str,
        reason: str,
    ) -> None:
        """Log an error during cleanup."""
        entry = CleanupLogEntry.create("error", path, file_type, reason)
        self.entries.append(entry)
        logger.error("[ERROR] %s: %s (%s)", file_type, path, reason)

    def write_log(self) -> None:
        """Write all log entries to the log file."""
        if not self.log_path or not self.entries:
            return

        # Read existing entries if file exists
        existing_entries: list[dict[str, object]] = []
        if self.log_path.exists():
            try:
                with self.log_path.open("r", encoding="utf-8") as f:
                    existing_entries = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Could not read existing log file: %s", e)
                existing_entries = []

        # Append new entries
        all_entries = existing_entries + [asdict(e) for e in self.entries]

        # Write back
        try:
            with self.log_path.open("w", encoding="utf-8") as f:
                json.dump(all_entries, f, indent=2, ensure_ascii=False)
            logger.info("Cleanup log written to: %s", self.log_path)
        except OSError:
            logger.exception("Failed to write cleanup log")

    def get_summary(self) -> dict[str, int]:
        """Get a summary of cleanup actions."""
        summary: dict[str, int] = {
            "deleted": 0,
            "would_delete": 0,
            "skipped": 0,
            "error": 0,
        }

        for entry in self.entries:
            if entry.action in summary:
                summary[entry.action] += 1

        return summary

    def get_deleted_count(self) -> int:
        """Get count of deleted (or would-be-deleted) items."""
        return sum(1 for e in self.entries if e.action in ("deleted", "would_delete"))


def get_default_log_path(para_root: Path) -> Path:
    """Get the default cleanup log path.

    Args:
        para_root: Root of the PARA structure

    Returns:
        Path to cleanup-log.json
    """
    return para_root / "logs" / "cleanup-log.json"
