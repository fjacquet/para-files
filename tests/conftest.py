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
