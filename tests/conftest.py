"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import importlib.util
import os
import platform
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

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


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


FIXTURE_TREE = Path(__file__).parent / "fixtures" / "test_reference_tree.yaml"


@pytest.fixture(autouse=True)
def _sanitized_reference_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every test on the sanitized fixture tree, never the owner's personal tree."""
    monkeypatch.setenv("PARA_FILES_REFERENCE_TREE_PATH", str(FIXTURE_TREE))


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


@pytest.fixture
def load_script() -> Callable[[str], ModuleType]:
    """Import a module from scripts/ by name (scripts/ is not a package)."""

    def _load(name: str) -> ModuleType:
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    return _load


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
