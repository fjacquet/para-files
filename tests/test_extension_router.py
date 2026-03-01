"""Tests for ExtensionRouterClassifier — full behaviour coverage.

TDD test suite verifying all 6 ROUTE-* requirements:
- ROUTE-01: Video extensions route to media_video_folder
- ROUTE-02: Audio extensions route to media_audio_folder
- ROUTE-03: Image extensions route to media_images_folder
- ROUTE-04: Security extensions route to security_folder
- ROUTE-05: Script extensions route to scripts_folder
- ROUTE-06: Unknown extensions route to catchall_folder; no extension returns None

Each test constructs FileMetadata directly (no mocking — pure logic tests).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from para_files.classifiers.extension_router import EXTENSION_GROUPS, ExtensionRouterClassifier
from para_files.config import ExtensionRoutingConfig
from para_files.types import ClassificationSource, FileMetadata


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def default_config() -> ExtensionRoutingConfig:
    """Return an ExtensionRoutingConfig with default folder paths."""
    return ExtensionRoutingConfig()


@pytest.fixture
def classifier(default_config: ExtensionRoutingConfig) -> ExtensionRouterClassifier:
    """Return an ExtensionRouterClassifier with default config."""
    return ExtensionRouterClassifier(default_config)


def _make_metadata(extension: str) -> FileMetadata:
    """Create minimal FileMetadata for testing with the given extension."""
    filename = f"test{extension}"
    return FileMetadata(
        path=Path(f"/tmp/{filename}"),
        filename=filename,
        extension=extension,
        size_bytes=1024,
    )


# ---------------------------------------------------------------------------
# ROUTE-01: Video extensions → media_video_folder
# ---------------------------------------------------------------------------


class TestVideoRouting:
    """ROUTE-01: Video files must route to media_video_folder with confidence >= 0.95."""

    @pytest.mark.parametrize("ext", [".mp4", ".3gp", ".m4v", ".mov"])
    def test_video_extension_routes_to_video_folder(
        self,
        classifier: ExtensionRouterClassifier,
        default_config: ExtensionRoutingConfig,
        ext: str,
    ) -> None:
        """Video extensions must route to media_video_folder."""
        metadata = _make_metadata(ext)
        result = classifier.classify("", metadata=metadata)

        assert result is not None
        assert result.category == default_config.media_video_folder
        assert result.confidence.value >= 0.95
        assert result.confidence.source == ClassificationSource.EXTENSION_ROUTER

    @pytest.mark.parametrize("ext", [".MP4", ".MOV"])  # uppercase
    def test_video_extension_case_insensitive(
        self,
        classifier: ExtensionRouterClassifier,
        default_config: ExtensionRoutingConfig,
        ext: str,
    ) -> None:
        """Video extension matching must be case-insensitive."""
        metadata = _make_metadata(ext)
        result = classifier.classify("", metadata=metadata)

        assert result is not None
        assert result.category == default_config.media_video_folder


# ---------------------------------------------------------------------------
# ROUTE-02: Audio extensions → media_audio_folder
# ---------------------------------------------------------------------------


class TestAudioRouting:
    """ROUTE-02: Audio files must route to media_audio_folder."""

    @pytest.mark.parametrize("ext", [".mp3", ".m4a"])
    def test_audio_extension_routes_to_audio_folder(
        self,
        classifier: ExtensionRouterClassifier,
        default_config: ExtensionRoutingConfig,
        ext: str,
    ) -> None:
        """Audio extensions must route to media_audio_folder."""
        metadata = _make_metadata(ext)
        result = classifier.classify("", metadata=metadata)

        assert result is not None
        assert result.category == default_config.media_audio_folder
        assert result.confidence.value >= 0.95
        assert result.confidence.source == ClassificationSource.EXTENSION_ROUTER


# ---------------------------------------------------------------------------
# ROUTE-03: Image extensions → media_images_folder
# ---------------------------------------------------------------------------


class TestImageRouting:
    """ROUTE-03: Raster image files must route to media_images_folder."""

    @pytest.mark.parametrize("ext", [".tif", ".tiff", ".gif", ".psd"])
    def test_image_extension_routes_to_images_folder(
        self,
        classifier: ExtensionRouterClassifier,
        default_config: ExtensionRoutingConfig,
        ext: str,
    ) -> None:
        """Image extensions must route to media_images_folder."""
        metadata = _make_metadata(ext)
        result = classifier.classify("", metadata=metadata)

        assert result is not None
        assert result.category == default_config.media_images_folder
        assert result.confidence.value >= 0.95
        assert result.confidence.source == ClassificationSource.EXTENSION_ROUTER


# ---------------------------------------------------------------------------
# ROUTE-04: Security extensions → security_folder
# ---------------------------------------------------------------------------


class TestSecurityRouting:
    """ROUTE-04: Security files must route to security_folder with confidence >= 0.97."""

    @pytest.mark.parametrize("ext", [".kdbx", ".p7b", ".asc"])
    def test_security_extension_routes_to_security_folder(
        self,
        classifier: ExtensionRouterClassifier,
        default_config: ExtensionRoutingConfig,
        ext: str,
    ) -> None:
        """Security extensions must route to security_folder."""
        metadata = _make_metadata(ext)
        result = classifier.classify("", metadata=metadata)

        assert result is not None
        assert result.category == default_config.security_folder
        assert result.confidence.value >= 0.97
        assert result.confidence.source == ClassificationSource.EXTENSION_ROUTER


# ---------------------------------------------------------------------------
# ROUTE-05: Script extensions → scripts_folder
# ---------------------------------------------------------------------------


class TestScriptRouting:
    """ROUTE-05: Script and web files must route to scripts_folder."""

    @pytest.mark.parametrize("ext", [".sh", ".ps1", ".css", ".js"])
    def test_script_extension_routes_to_scripts_folder(
        self,
        classifier: ExtensionRouterClassifier,
        default_config: ExtensionRoutingConfig,
        ext: str,
    ) -> None:
        """Script/web extensions must route to scripts_folder."""
        metadata = _make_metadata(ext)
        result = classifier.classify("", metadata=metadata)

        assert result is not None
        assert result.category == default_config.scripts_folder
        assert result.confidence.value >= 0.95
        assert result.confidence.source == ClassificationSource.EXTENSION_ROUTER


# ---------------------------------------------------------------------------
# ROUTE-06: Edge cases — unknown extension, no extension, no metadata
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """ROUTE-06: Edge cases for catch-all and no-extension behaviour."""

    def test_unknown_extension_routes_to_catchall(
        self,
        classifier: ExtensionRouterClassifier,
        default_config: ExtensionRoutingConfig,
    ) -> None:
        """An unknown extension (.xyz) must route to catchall_folder with confidence 0.80."""
        metadata = _make_metadata(".xyz")
        result = classifier.classify("", metadata=metadata)

        assert result is not None
        assert result.category == default_config.catchall_folder
        assert result.confidence.value == 0.80
        assert result.confidence.source == ClassificationSource.EXTENSION_ROUTER

    def test_no_extension_returns_none(
        self,
        classifier: ExtensionRouterClassifier,
    ) -> None:
        """A file with no extension must return None so the pipeline can continue."""
        metadata = _make_metadata("")
        result = classifier.classify("", metadata=metadata)

        assert result is None

    def test_none_metadata_returns_none(
        self,
        classifier: ExtensionRouterClassifier,
    ) -> None:
        """Passing metadata=None must return None gracefully."""
        result = classifier.classify("", metadata=None)

        assert result is None

    def test_content_argument_ignored(
        self,
        classifier: ExtensionRouterClassifier,
        default_config: ExtensionRoutingConfig,
    ) -> None:
        """Content argument is ignored — classification is extension-only."""
        metadata = _make_metadata(".mp4")
        # Even with non-empty, misleading content, result should be based on extension
        result = classifier.classify("this is audio content", metadata=metadata)

        assert result is not None
        assert result.category == default_config.media_video_folder


# ---------------------------------------------------------------------------
# Full EXTENSION_GROUPS coverage
# ---------------------------------------------------------------------------


class TestFullExtensionGroupsCoverage:
    """Verify every key in EXTENSION_GROUPS routes to a non-catchall category."""

    @pytest.mark.parametrize("ext", list(EXTENSION_GROUPS.keys()))
    def test_all_known_extensions_route_to_known_category(
        self,
        classifier: ExtensionRouterClassifier,
        default_config: ExtensionRoutingConfig,
        ext: str,
    ) -> None:
        """Every extension in EXTENSION_GROUPS must return a non-None result not in catchall."""
        metadata = _make_metadata(ext)
        result = classifier.classify("", metadata=metadata)

        assert result is not None, f"Expected classification for {ext}, got None"
        assert result.category != default_config.catchall_folder, (
            f"Extension {ext} unexpectedly routed to catchall"
        )
        assert result.confidence.value >= 0.95, (
            f"Expected confidence >= 0.95 for {ext}, got {result.confidence.value}"
        )
        assert result.confidence.source == ClassificationSource.EXTENSION_ROUTER


# ---------------------------------------------------------------------------
# Config override test
# ---------------------------------------------------------------------------


class TestConfigOverride:
    """Verify that custom ExtensionRoutingConfig values are respected."""

    def test_custom_video_folder_overrides_default(self) -> None:
        """ExtensionRoutingConfig(media_video_folder='custom/video') must route .mp4 there."""
        custom_config = ExtensionRoutingConfig(media_video_folder="custom/video")
        classifier = ExtensionRouterClassifier(custom_config)
        metadata = _make_metadata(".mp4")

        result = classifier.classify("", metadata=metadata)

        assert result is not None
        assert result.category == "custom/video"

    def test_custom_catchall_folder_overrides_default(self) -> None:
        """ExtensionRoutingConfig(catchall_folder='custom/misc') must be used for .xyz."""
        custom_config = ExtensionRoutingConfig(catchall_folder="custom/misc")
        classifier = ExtensionRouterClassifier(custom_config)
        metadata = _make_metadata(".xyz")

        result = classifier.classify("", metadata=metadata)

        assert result is not None
        assert result.category == "custom/misc"

    def test_custom_security_folder_overrides_default(self) -> None:
        """ExtensionRoutingConfig(security_folder='private/vault') must route .kdbx there."""
        custom_config = ExtensionRoutingConfig(security_folder="private/vault")
        classifier = ExtensionRouterClassifier(custom_config)
        metadata = _make_metadata(".kdbx")

        result = classifier.classify("", metadata=metadata)

        assert result is not None
        assert result.category == "private/vault"


# ---------------------------------------------------------------------------
# Classifier properties
# ---------------------------------------------------------------------------


class TestClassifierProperties:
    """Verify classifier metadata properties."""

    def test_classifier_name(self, classifier: ExtensionRouterClassifier) -> None:
        """Classifier name must be 'extension_router'."""
        assert classifier.name == "extension_router"

    def test_classifier_source(self, classifier: ExtensionRouterClassifier) -> None:
        """Classifier source must be EXTENSION_ROUTER."""
        assert classifier.source == ClassificationSource.EXTENSION_ROUTER

    def test_default_confidence(self, classifier: ExtensionRouterClassifier) -> None:
        """Default confidence must be 0.97."""
        assert classifier.default_confidence == 0.97
