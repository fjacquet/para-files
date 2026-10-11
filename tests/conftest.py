"""Pytest configuration: every test runs with its own HOME, config dir and cwd.

No test reads the owner's real configuration or PARA volume.
"""

from __future__ import annotations

import os
import platform
from collections.abc import Callable
from pathlib import Path

import pytest


# Platform skip marker for macOS-only tests (Apple Vision Framework, etc.)
macos_only = pytest.mark.skipif(
    platform.system() != "Darwin",
    reason="Requires macOS (Apple Vision Framework)",
)


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(autouse=True)
def _sandbox(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Per-test HOME and config dir, no inherited PARA_FILES_ or API key, cwd = tmp_path."""
    for name in [k for k in os.environ if k.startswith("PARA_FILES_")]:
        monkeypatch.delenv(name)  # inherited shell values (e.g. sourced ~/.env) never leak in
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)  # a real key never reaches a test
    home = tmp_path_factory.mktemp("home")  # outside tmp_path so tests listing it stay exact
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PARA_FILES_CONFIG_DIR", str(home / ".config" / "para-files"))
    monkeypatch.chdir(tmp_path)


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    """Every entry under root with size and mtime_ns; equal snapshots mean nothing changed."""
    entries: dict[str, tuple[int, int]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in [*dirnames, *filenames]:
            path = Path(dirpath) / name
            stat = path.lstat()
            entries[str(path.relative_to(root))] = (stat.st_size, stat.st_mtime_ns)
    return entries


@pytest.fixture
def snapshot() -> Callable[[Path], dict[str, tuple[int, int]]]:
    """Return a function that snapshots a directory tree (read-only checks)."""
    return _snapshot
