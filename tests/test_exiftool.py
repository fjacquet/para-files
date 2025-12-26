"""Tests for the exiftool extractor module."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from para_files.utils.exiftool import (
    EXIF_EXTENSIONS,
    ExifData,
    GPSCoordinates,
    _get_int_field,
    _get_string_field,
    _normalize_date_string,
    _parse_duration,
    _parse_exif_date,
    _parse_gps,
    extract_exif,
    is_exiftool_available,
)


class TestExifDataModel:
    """Tests for ExifData Pydantic model."""

    def test_exif_data_defaults(self):
        """Test ExifData with default values."""
        exif = ExifData()
        assert exif.date_taken is None
        assert exif.date_created is None
        assert exif.make is None
        assert exif.model is None
        assert exif.gps is None

    def test_exif_data_with_values(self):
        """Test ExifData with actual values."""
        dt = datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC)
        exif = ExifData(
            date_taken=dt,
            make="Apple",
            model="iPhone 15 Pro",
            width=4032,
            height=3024,
        )
        assert exif.date_taken == dt
        assert exif.make == "Apple"
        assert exif.model == "iPhone 15 Pro"
        assert exif.width == 4032
        assert exif.height == 3024

    def test_exif_data_best_date_prefers_date_taken(self):
        """Test best_date property prefers date_taken."""
        dt_taken = datetime(2025, 1, 15, tzinfo=UTC)
        dt_created = datetime(2025, 1, 10, tzinfo=UTC)
        exif = ExifData(date_taken=dt_taken, date_created=dt_created)
        assert exif.best_date == dt_taken

    def test_exif_data_best_date_falls_back_to_created(self):
        """Test best_date falls back to date_created."""
        dt_created = datetime(2025, 1, 10, tzinfo=UTC)
        exif = ExifData(date_created=dt_created)
        assert exif.best_date == dt_created

    def test_exif_data_best_date_none(self):
        """Test best_date returns None when no dates."""
        exif = ExifData()
        assert exif.best_date is None


class TestGPSCoordinates:
    """Tests for GPSCoordinates model."""

    def test_gps_basic(self):
        """Test GPS with lat/lon only."""
        gps = GPSCoordinates(latitude=46.2044, longitude=6.1432)
        assert gps.latitude == 46.2044
        assert gps.longitude == 6.1432
        assert gps.altitude is None

    def test_gps_with_altitude(self):
        """Test GPS with altitude."""
        gps = GPSCoordinates(latitude=46.2044, longitude=6.1432, altitude=375.5)
        assert gps.altitude == 375.5


class TestNormalizeDateString:
    """Tests for date string normalization."""

    def test_standard_exif_format(self):
        """Test standard EXIF format passes through."""
        result = _normalize_date_string("2025:01:15 14:30:00")
        assert result == "2025:01:15 14:30:00"

    def test_removes_timezone_suffix(self):
        """Test timezone suffix is removed."""
        result = _normalize_date_string("2025:01:15 14:30:00+02:00")
        assert result == "2025:01:15 14:30:00"

    def test_converts_iso_format(self):
        """Test ISO format T separator is converted."""
        result = _normalize_date_string("2025-01-15T14:30:00")
        assert result == "2025-01-15 14:30:00"

    def test_strips_whitespace(self):
        """Test whitespace is stripped."""
        result = _normalize_date_string("  2025:01:15 14:30:00  ")
        assert result == "2025:01:15 14:30:00"


class TestParseExifDate:
    """Tests for EXIF date parsing."""

    def test_parse_none(self):
        """Test None input returns None."""
        assert _parse_exif_date(None) is None

    def test_parse_empty_string(self):
        """Test empty string returns None."""
        assert _parse_exif_date("") is None

    def test_parse_standard_exif_format(self):
        """Test standard EXIF date format."""
        result = _parse_exif_date("2025:01:15 14:30:00")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30
        assert result.tzinfo == UTC

    def test_parse_iso_format(self):
        """Test ISO date format."""
        result = _parse_exif_date("2025-01-15 14:30:00")
        assert result is not None
        assert result.year == 2025

    def test_parse_date_only(self):
        """Test date-only format."""
        result = _parse_exif_date("2025:01:15")
        assert result is not None
        assert result.year == 2025
        assert result.hour == 0

    def test_parse_with_timezone(self):
        """Test date with timezone suffix."""
        result = _parse_exif_date("2025:01:15 14:30:00+02:00")
        assert result is not None
        assert result.year == 2025

    def test_parse_invalid_format(self):
        """Test invalid format returns None."""
        result = _parse_exif_date("not a date")
        assert result is None


class TestParseGPS:
    """Tests for GPS coordinate parsing."""

    def test_parse_gps_valid(self):
        """Test parsing valid GPS data."""
        data = {"GPSLatitude": 46.2044, "GPSLongitude": 6.1432}
        result = _parse_gps(data)
        assert result is not None
        assert result.latitude == 46.2044
        assert result.longitude == 6.1432

    def test_parse_gps_with_altitude(self):
        """Test GPS with altitude."""
        data = {"GPSLatitude": 46.2044, "GPSLongitude": 6.1432, "GPSAltitude": 375.5}
        result = _parse_gps(data)
        assert result is not None
        assert result.altitude == 375.5

    def test_parse_gps_missing_lat(self):
        """Test missing latitude returns None."""
        data = {"GPSLongitude": 6.1432}
        assert _parse_gps(data) is None

    def test_parse_gps_missing_lon(self):
        """Test missing longitude returns None."""
        data = {"GPSLatitude": 46.2044}
        assert _parse_gps(data) is None

    def test_parse_gps_string_values(self):
        """Test GPS values as strings."""
        data = {"GPSLatitude": "46.2044", "GPSLongitude": "6.1432"}
        result = _parse_gps(data)
        assert result is not None
        assert result.latitude == 46.2044


class TestParseDuration:
    """Tests for duration parsing."""

    def test_parse_duration_none(self):
        """Test None input returns None."""
        assert _parse_duration(None) is None

    def test_parse_duration_float(self):
        """Test float seconds."""
        assert _parse_duration(123.45) == 123.45

    def test_parse_duration_int(self):
        """Test integer seconds."""
        assert _parse_duration(120) == 120.0

    def test_parse_duration_hms_string(self):
        """Test H:MM:SS format."""
        result = _parse_duration("1:05:23")
        assert result == 3923.0  # 1*3600 + 5*60 + 23

    def test_parse_duration_ms_string(self):
        """Test MM:SS format."""
        result = _parse_duration("5:30")
        assert result == 330.0  # 5*60 + 30

    def test_parse_duration_numeric_string(self):
        """Test numeric string."""
        assert _parse_duration("123.5") == 123.5

    def test_parse_duration_invalid(self):
        """Test invalid duration."""
        assert _parse_duration("invalid") is None


class TestGetStringField:
    """Tests for string field extraction."""

    def test_get_string_single_key(self):
        """Test getting single key."""
        data = {"Make": "Apple"}
        assert _get_string_field(data, "Make") == "Apple"

    def test_get_string_first_match(self):
        """Test first matching key is returned."""
        data = {"Artist": "John", "Author": "Jane"}
        assert _get_string_field(data, "Artist", "Author") == "John"

    def test_get_string_fallback(self):
        """Test fallback to second key."""
        data = {"Author": "Jane"}
        assert _get_string_field(data, "Artist", "Author") == "Jane"

    def test_get_string_missing(self):
        """Test missing key returns None."""
        data = {"Other": "value"}
        assert _get_string_field(data, "Make", "Model") is None

    def test_get_string_converts_int(self):
        """Test integer is converted to string."""
        data = {"Width": 4032}
        assert _get_string_field(data, "Width") == "4032"


class TestGetIntField:
    """Tests for integer field extraction."""

    def test_get_int_valid(self):
        """Test getting valid integer."""
        data = {"ImageWidth": 4032}
        assert _get_int_field(data, "ImageWidth") == 4032

    def test_get_int_from_string(self):
        """Test integer from string."""
        data = {"ImageWidth": "4032"}
        assert _get_int_field(data, "ImageWidth") == 4032

    def test_get_int_missing(self):
        """Test missing key returns None."""
        data = {"Other": 123}
        assert _get_int_field(data, "ImageWidth") is None

    def test_get_int_invalid(self):
        """Test invalid value returns None."""
        data = {"ImageWidth": "not a number"}
        assert _get_int_field(data, "ImageWidth") is None


class TestIsExiftoolAvailable:
    """Tests for exiftool availability check."""

    def test_exiftool_available(self):
        """Test when exiftool is available."""
        with patch("shutil.which", return_value="/usr/local/bin/exiftool"):
            assert is_exiftool_available() is True

    def test_exiftool_not_available(self):
        """Test when exiftool is not available."""
        with patch("shutil.which", return_value=None):
            assert is_exiftool_available() is False


class TestExtractExif:
    """Tests for the main extract_exif function."""

    def test_exiftool_not_available(self, tmp_path: Path):
        """Test when exiftool is not installed."""
        test_file = tmp_path / "test.jpg"
        test_file.touch()
        with patch("para_files.utils.exiftool.is_exiftool_available", return_value=False):
            result = extract_exif(test_file)
            assert result is None

    def test_unsupported_extension(self, tmp_path: Path):
        """Test unsupported file extension."""
        test_file = tmp_path / "test.txt"
        test_file.touch()
        result = extract_exif(test_file)
        assert result is None

    def test_file_not_exists(self):
        """Test non-existent file."""
        result = extract_exif(Path("/nonexistent/file.jpg"))
        assert result is None

    def test_exif_extensions_includes_common_formats(self):
        """Test EXIF_EXTENSIONS contains common formats."""
        assert ".jpg" in EXIF_EXTENSIONS
        assert ".jpeg" in EXIF_EXTENSIONS
        assert ".png" in EXIF_EXTENSIONS
        assert ".heic" in EXIF_EXTENSIONS
        assert ".mp4" in EXIF_EXTENSIONS
        assert ".mov" in EXIF_EXTENSIONS

    @patch("para_files.utils.exiftool._run_exiftool")
    def test_extract_exif_with_data(self, mock_run: MagicMock, tmp_path: Path):
        """Test extracting EXIF data."""
        test_file = tmp_path / "photo.jpg"
        test_file.touch()

        mock_run.return_value = {
            "DateTimeOriginal": "2025:01:15 14:30:00",
            "Make": "Apple",
            "Model": "iPhone 15 Pro",
            "ImageWidth": 4032,
            "ImageHeight": 3024,
            "GPSLatitude": 46.2044,
            "GPSLongitude": 6.1432,
        }

        result = extract_exif(test_file)

        assert result is not None
        assert result.make == "Apple"
        assert result.model == "iPhone 15 Pro"
        assert result.width == 4032
        assert result.height == 3024
        assert result.gps is not None
        assert result.gps.latitude == 46.2044
        assert result.date_taken is not None
        assert result.date_taken.year == 2025

    @patch("para_files.utils.exiftool._run_exiftool")
    def test_extract_exif_no_data(self, mock_run: MagicMock, tmp_path: Path):
        """Test when exiftool returns no data."""
        test_file = tmp_path / "empty.jpg"
        test_file.touch()

        mock_run.return_value = None
        result = extract_exif(test_file)
        assert result is None


class TestExtractExifIntegration:
    """Integration tests that require exiftool to be installed."""

    @pytest.fixture
    def check_exiftool(self):
        """Skip test if exiftool is not installed."""
        if not is_exiftool_available():
            pytest.skip("exiftool not installed")

    @pytest.mark.slow
    def test_extract_from_real_image(self, check_exiftool, tmp_path: Path):
        """Test extracting EXIF from a real image file."""
        # Create a minimal JPEG file (no actual EXIF data)
        jpeg_file = tmp_path / "test.jpg"
        # Minimal valid JPEG (SOI + EOI markers)
        jpeg_file.write_bytes(
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
        )

        result = extract_exif(jpeg_file)
        # May return ExifData with all None fields, or None
        # depending on how exiftool handles minimal JPEG
        if result:
            # If we got data, it should be a valid ExifData object
            assert isinstance(result, ExifData)
