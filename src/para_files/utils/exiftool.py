"""Exiftool integration for extracting file metadata.

Uses exiftool CLI for extracting EXIF data from images and videos.
Falls back gracefully when exiftool is not installed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field


# Supported extensions for EXIF extraction
EXIF_EXTENSIONS = frozenset(
    {
        # Images
        ".jpg",
        ".jpeg",
        ".png",
        ".heic",
        ".heif",
        ".tiff",
        ".tif",
        ".gif",
        ".bmp",
        ".webp",
        ".raw",
        ".cr2",
        ".nef",
        ".arw",
        ".dng",
        # Videos
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".m4v",
        ".3gp",
        ".wmv",
        # Audio
        ".mp3",
        ".m4a",
        ".wav",
        ".flac",
        ".aac",
    }
)

# Duration format constants
_DURATION_PARTS_HMS = 3  # H:MM:SS format
_DURATION_PARTS_MS = 2  # MM:SS format


class GPSCoordinates(BaseModel):
    """GPS coordinates from EXIF data."""

    latitude: float = Field(description="Latitude in decimal degrees")
    longitude: float = Field(description="Longitude in decimal degrees")
    altitude: float | None = Field(default=None, description="Altitude in meters")


class ExifData(BaseModel):
    """EXIF metadata extracted from a file."""

    # Dates
    date_taken: datetime | None = Field(
        default=None,
        description="Original capture date (DateTimeOriginal or CreateDate)",
    )
    date_created: datetime | None = Field(
        default=None,
        description="File creation date from EXIF",
    )

    # Camera info
    make: str | None = Field(default=None, description="Camera manufacturer")
    model: str | None = Field(default=None, description="Camera model")
    lens: str | None = Field(default=None, description="Lens model")

    # Location
    gps: GPSCoordinates | None = Field(default=None, description="GPS coordinates")

    # Image properties
    width: int | None = Field(default=None, description="Image width in pixels")
    height: int | None = Field(default=None, description="Image height in pixels")
    orientation: int | None = Field(default=None, description="EXIF orientation (1-8)")

    # Video properties
    duration: float | None = Field(default=None, description="Video duration in seconds")

    # Author
    author: str | None = Field(default=None, description="Author/Artist from metadata")
    copyright: str | None = Field(default=None, description="Copyright information")

    @property
    def best_date(self) -> datetime | None:
        """Return the best available date (prefer date_taken over date_created)."""
        return self.date_taken or self.date_created


def is_exiftool_available() -> bool:
    """Check if exiftool is installed and accessible."""
    return shutil.which("exiftool") is not None


def _normalize_date_string(date_str: str) -> str:
    """Normalize EXIF date string for parsing.

    Removes timezone suffixes and handles various formats.
    """
    # Remove timezone suffix like +00:00 or -05:00
    if "+" in date_str:
        date_str = date_str.split("+")[0]
    # Handle ISO format with T separator
    date_str = date_str.replace("T", " ")
    return date_str.strip()


def _parse_exif_date(date_str: str | None) -> datetime | None:
    """Parse EXIF date string to datetime.

    EXIF dates are typically in format: "2025:01:15 14:30:00"
    Returns timezone-aware datetime in UTC.
    """
    if not date_str:
        return None

    normalized = _normalize_date_string(date_str)

    # Common EXIF date formats (without timezone - we add UTC)
    formats = [
        "%Y:%m:%d %H:%M:%S",  # Standard EXIF
        "%Y-%m-%d %H:%M:%S",  # Alternative
        "%Y:%m:%d",  # Date only
        "%Y-%m-%d",  # Date only alternative
    ]

    for fmt in formats:
        try:
            naive_dt = datetime.strptime(normalized, fmt)  # noqa: DTZ007
            return naive_dt.replace(tzinfo=UTC)
        except ValueError:
            continue

    # Try parsing with just first 10 chars as date
    try:
        date_only = normalized[:10].replace(":", "-")
        naive_dt = datetime.strptime(date_only, "%Y-%m-%d")  # noqa: DTZ007
        return naive_dt.replace(tzinfo=UTC)
    except ValueError:
        logger.debug("Could not parse EXIF date: %s", date_str)
        return None


def _parse_gps(data: dict[str, object]) -> GPSCoordinates | None:
    """Parse GPS coordinates from exiftool output."""
    lat = data.get("GPSLatitude")
    lon = data.get("GPSLongitude")

    if lat is None or lon is None:
        return None

    try:
        # exiftool returns decimal degrees when using -n flag
        lat_val = float(lat) if isinstance(lat, (int, float, str)) else None
        lon_val = float(lon) if isinstance(lon, (int, float, str)) else None

        if lat_val is None or lon_val is None:
            return None

        alt = data.get("GPSAltitude")
        alt_val = float(alt) if alt and isinstance(alt, (int, float, str)) else None

        return GPSCoordinates(
            latitude=lat_val,
            longitude=lon_val,
            altitude=alt_val,
        )
    except (ValueError, TypeError):
        logger.debug("Could not parse GPS coordinates")
        return None


def _parse_duration(duration: object) -> float | None:
    """Parse duration from exiftool output.

    Duration can be a float (seconds) or a string like "0:05:23".
    """
    if duration is None:
        return None

    if isinstance(duration, (int, float)):
        return float(duration)

    if isinstance(duration, str):
        # Handle "H:MM:SS" or "MM:SS" format
        parts = duration.split(":")
        try:
            if len(parts) == _DURATION_PARTS_HMS:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            if len(parts) == _DURATION_PARTS_MS:
                return float(parts[0]) * 60 + float(parts[1])
            return float(duration)
        except ValueError:
            pass

    return None


def _get_string_field(data: dict[str, object], *keys: str) -> str | None:
    """Get first non-None string value from data for given keys."""
    for key in keys:
        value = data.get(key)
        if value is not None:
            return str(value)
    return None


def _get_int_field(data: dict[str, object], key: str) -> int | None:
    """Get integer value from data, or None if not present."""
    value = data.get(key)
    if value is not None:
        try:
            return int(str(value))
        except (ValueError, TypeError):
            pass
    return None


def _run_exiftool(file_path: Path) -> dict[str, object] | None:
    """Run exiftool and return parsed JSON data."""
    exiftool_args = [
        "exiftool",
        "-json",
        "-n",  # Numeric output for GPS
        "-DateTimeOriginal",
        "-CreateDate",
        "-Make",
        "-Model",
        "-LensModel",
        "-GPSLatitude",
        "-GPSLongitude",
        "-GPSAltitude",
        "-ImageWidth",
        "-ImageHeight",
        "-Orientation",
        "-Duration",
        "-Artist",
        "-Author",
        "-Copyright",
        str(file_path),
    ]
    try:
        result = subprocess.run(  # noqa: S603
            exiftool_args,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode != 0:
            logger.debug("exiftool failed: %s", result.stderr)
            return None

        data_list: list[dict[str, object]] = json.loads(result.stdout)
        if not data_list:
            return None

        return data_list[0]

    except subprocess.TimeoutExpired:
        logger.warning("exiftool timed out for: %s", file_path)
    except json.JSONDecodeError:
        logger.warning("exiftool returned invalid JSON for: %s", file_path)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to extract EXIF from: %s", file_path)

    return None


def extract_exif(file_path: Path) -> ExifData | None:
    """Extract EXIF data from a file using exiftool.

    Args:
        file_path: Path to the file to extract EXIF from.

    Returns:
        ExifData if extraction succeeds, None if exiftool unavailable
        or file has no EXIF data.
    """
    if not is_exiftool_available():
        logger.debug("exiftool not available")
        return None

    # Check if file extension is supported
    ext = file_path.suffix.lower()
    if ext not in EXIF_EXTENSIONS:
        logger.debug("Unsupported extension for EXIF: %s", ext)
        return None

    if not file_path.exists():
        logger.debug("File does not exist: %s", file_path)
        return None

    data = _run_exiftool(file_path)
    if data is None:
        return None

    # Parse dates
    date_str = _get_string_field(data, "DateTimeOriginal", "CreateDate")
    date_taken = _parse_exif_date(date_str)
    date_created = _parse_exif_date(_get_string_field(data, "CreateDate"))

    return ExifData(
        date_taken=date_taken,
        date_created=date_created,
        make=_get_string_field(data, "Make"),
        model=_get_string_field(data, "Model"),
        lens=_get_string_field(data, "LensModel"),
        gps=_parse_gps(data),
        width=_get_int_field(data, "ImageWidth"),
        height=_get_int_field(data, "ImageHeight"),
        orientation=_get_int_field(data, "Orientation"),
        duration=_parse_duration(data.get("Duration")),
        author=_get_string_field(data, "Artist", "Author"),
        copyright=_get_string_field(data, "Copyright"),
    )
