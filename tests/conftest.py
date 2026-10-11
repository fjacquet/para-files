"""Pytest configuration and shared fixtures.

Every test runs hermetically: HOME and the personal config dir point into tmp_path, the working
directory is tmp_path, `.env` loading is disabled on every settings class, and the reference tree
is the sanitized fixture. No test reads the owner's real PARA configuration or volume.
Tests run with cwd = tmp_path; a test that needs the repo root must chdir itself.
"""

from __future__ import annotations

import contextlib
import importlib.util
import os
import platform
import sys
import uuid
from collections.abc import Callable, Iterator
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
def _sanitized_reference_tree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Sandbox configuration: fixture tree, per-test HOME and config dir, no .env, tmp cwd."""
    from para_files.config import (
        Config,
        ExtensionRoutingConfig,
        LLMConfig,
        LoggingConfig,
        MLXConfig,
    )

    for name in [k for k in os.environ if k.startswith("PARA_FILES_")]:
        monkeypatch.delenv(name)  # inherited shell values (e.g. sourced ~/.env) never leak in
    home = tmp_path_factory.mktemp("home")  # outside tmp_path so tests listing it stay exact
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PARA_FILES_CONFIG_DIR", str(home / ".config" / "para-files"))
    monkeypatch.setenv("PARA_FILES_REFERENCE_TREE_PATH", str(FIXTURE_TREE))
    monkeypatch.chdir(tmp_path)  # cwd YAML fallbacks and ./.env resolve to empty tmp_path
    for settings_cls in (Config, MLXConfig, LLMConfig, LoggingConfig, ExtensionRoutingConfig):
        monkeypatch.setitem(settings_cls.model_config, "env_file", None)


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


@pytest.fixture
def load_script() -> Iterator[Callable[[str], ModuleType]]:
    """Import a module from scripts/ by name (scripts/ is not a package).

    Each load gets a unique module name. On teardown the sys.path entry and every module that
    came from scripts/ are removed, so no test sees another test's script.
    """
    added_path = str(SCRIPTS_DIR) not in sys.path
    if added_path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    before = set(sys.modules)

    def _load(name: str) -> ModuleType:
        unique = f"scripts_{name}_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(unique, SCRIPTS_DIR / f"{name}.py")
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[unique] = module
        spec.loader.exec_module(module)
        return module

    yield _load

    for key in set(sys.modules) - before:
        file = getattr(sys.modules[key], "__file__", None) or ""
        if file.startswith(str(SCRIPTS_DIR)):
            del sys.modules[key]
    if added_path:
        with contextlib.suppress(ValueError):
            sys.path.remove(str(SCRIPTS_DIR))


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
