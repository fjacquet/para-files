"""SQLite cache (spec §4.2, robustness and caching): ISBN lookups and signal verdicts.

Verdicts are keyed by (content sha256, config fingerprint), so a preview followed by an apply
pays for model calls once, and any edit of tree/rules/issuers or of the model id starts fresh.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


CONFIG_FILES = ("tree.yaml", "rules.yaml", "issuers.yaml")


class Cache:
    """Two key/value tables in one SQLite file; safe to share between threads."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        with self._lock, self._db:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS isbn (isbn TEXT PRIMARY KEY, info TEXT NOT NULL)"
            )
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS verdict (sha256 TEXT NOT NULL, "
                "fingerprint TEXT NOT NULL, verdict TEXT NOT NULL, "
                "PRIMARY KEY (sha256, fingerprint))"
            )

    def _get(self, sql: str, args: tuple[str, ...]) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute(sql, args).fetchone()
        return json.loads(row[0]) if row else None

    def _put(self, sql: str, args: tuple[str, ...]) -> None:
        with self._lock, self._db:
            self._db.execute(sql, args)

    def get_isbn(self, isbn: str) -> dict[str, Any] | None:
        """Stored lookup result, or None."""
        return self._get("SELECT info FROM isbn WHERE isbn = ?", (isbn,))

    def put_isbn(self, isbn: str, info: dict[str, Any]) -> None:
        """Store a lookup result."""
        self._put("INSERT OR REPLACE INTO isbn VALUES (?, ?)", (isbn, json.dumps(info)))

    def get_verdict(self, sha256: str, fingerprint: str) -> dict[str, Any] | None:
        """Stored verdict for this content under this config, or None."""
        return self._get(
            "SELECT verdict FROM verdict WHERE sha256 = ? AND fingerprint = ?",
            (sha256, fingerprint),
        )

    def put_verdict(self, sha256: str, fingerprint: str, verdict: dict[str, Any]) -> None:
        """Store a verdict."""
        self._put(
            "INSERT OR REPLACE INTO verdict VALUES (?, ?, ?)",
            (sha256, fingerprint, json.dumps(verdict)),
        )

    def close(self) -> None:
        """Close the connection."""
        with self._lock:
            self._db.close()


def config_fingerprint(directory: Path, *parts: str) -> str:
    """Hash of tree.yaml, rules.yaml, issuers.yaml (missing = empty) and the given parts
    (models, prompt version, preview size): change any of them and the model is asked again."""
    digest = hashlib.sha256()
    for name in CONFIG_FILES:
        path = directory / name
        digest.update(name.encode() + b"\0")
        digest.update((path.read_bytes() if path.exists() else b"") + b"\0")
    for part in parts:
        digest.update(part.encode() + b"\0")
    return digest.hexdigest()
