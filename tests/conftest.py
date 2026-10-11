"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import platform
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


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


FIXTURE_TREE = Path(__file__).parent / "fixtures" / "test_reference_tree.yaml"


@pytest.fixture(autouse=True)
def _sanitized_reference_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every test on the sanitized fixture tree, never the owner's personal tree."""
    monkeypatch.setenv("PARA_FILES_REFERENCE_TREE_PATH", str(FIXTURE_TREE))
