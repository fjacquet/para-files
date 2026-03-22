"""Geolocation utilities for GPS coordinate lookup.

Uses geopy to reverse geocode GPS coordinates into location names.
Features a two-level cache: in-memory LRU + persistent SQLite.
Falls back gracefully when geocoding fails or times out.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from pydantic import BaseModel, Field

from para_files.utils.filename_sanitizer import sanitize_path_component


if TYPE_CHECKING:
    from collections.abc import Mapping


# Default timeout for geocoding requests
_GEOCODE_TIMEOUT = 5

# Cache configuration
_CACHE_DIR = Path.home() / ".cache" / "para-files"
_CACHE_DB = _CACHE_DIR / "geolocation.db"


class LocationInfo(BaseModel):
    """Location information from reverse geocoding."""

    city: str | None = Field(default=None, description="City or town name")
    region: str | None = Field(default=None, description="State/province/region")
    country: str | None = Field(default=None, description="Country name")
    country_code: str | None = Field(default=None, description="ISO country code")

    @property
    def display_name(self) -> str:
        """Return a display name for the location, preferring city > region > country."""
        if self.city:
            return self.city
        if self.region:
            return self.region
        if self.country:
            return self.country
        return "Unknown"

    @property
    def folder_name(self) -> str:
        """Return a filesystem-safe folder path for the location.

        Returns country/location format when both are available.
        E.g., "Switzerland/Geneva" or "United_States/New_York".
        """

        def sanitize(name: str) -> str:
            """Make a name filesystem-safe using centralized sanitizer."""
            result = sanitize_path_component(name, replacement="_", replace_spaces=True)
            return result or "Unknown"

        # Get the most specific location
        location = self.city or self.region
        country = self.country

        if country and location:
            # Return country/location format
            return f"{sanitize(country)}/{sanitize(location)}"
        if country:
            return sanitize(country)
        if location:
            return sanitize(location)
        return "Unknown"


class GeolocationCache:
    """SQLite-backed persistent cache for geolocation lookups."""

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize the cache.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.cache/para-files/geolocation.db
        """
        self.db_path = db_path or _CACHE_DB
        self._connection: sqlite3.Connection | None = None
        self._lock = threading.RLock()  # Thread-safe access to SQLite
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = self._get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS geolocation_cache (
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    address_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (lat, lon)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_geolocation_coords
                ON geolocation_cache (lat, lon)
            """)
            conn.commit()
            logger.debug("Geolocation cache initialized at {}", self.db_path)
        except sqlite3.Error as e:
            logger.warning("Failed to initialize geolocation cache: {}", e)

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
        return self._connection

    def get(self, lat: float, lon: float) -> dict[str, str] | None:
        """Get cached address for coordinates (thread-safe).

        Args:
            lat: Latitude (already rounded).
            lon: Longitude (already rounded).

        Returns:
            Cached address dictionary, or None if not found.
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.execute(
                    "SELECT address_json FROM geolocation_cache WHERE lat = ? AND lon = ?",
                    (lat, lon),
                )
                row = cursor.fetchone()
                if row:
                    result: dict[str, str] = json.loads(row[0])
                    logger.debug("Cache hit for coordinates: {}, {}", lat, lon)
                    return result
            except (sqlite3.Error, json.JSONDecodeError) as e:
                logger.debug("Cache lookup failed: {}", e)
            return None

    def set(self, lat: float, lon: float, address: Mapping[str, str]) -> None:
        """Store address in cache (thread-safe).

        Args:
            lat: Latitude (already rounded).
            lon: Longitude (already rounded).
            address: Address dictionary from geocoder.
        """
        with self._lock:
            try:
                conn = self._get_connection()
                conn.execute(
                    """
                    INSERT OR REPLACE INTO geolocation_cache (lat, lon, address_json)
                    VALUES (?, ?, ?)
                    """,
                    (lat, lon, json.dumps(dict(address))),
                )
                conn.commit()
                logger.debug("Cached location for coordinates: {}, {}", lat, lon)
            except sqlite3.Error as e:
                logger.debug("Cache write failed: {}", e)

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics (thread-safe).

        Returns:
            Dictionary with cache statistics.
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.execute("SELECT COUNT(*) FROM geolocation_cache")
                row = cursor.fetchone()
                count = row[0] if row else 0
            except sqlite3.Error:
                return {"entries": 0}
            else:
                return {"entries": count}

    def clear(self) -> None:
        """Clear all cached entries (thread-safe)."""
        with self._lock:
            try:
                conn = self._get_connection()
                conn.execute("DELETE FROM geolocation_cache")
                conn.commit()
                logger.info("Geolocation cache cleared")
            except sqlite3.Error as e:
                logger.warning("Failed to clear cache: {}", e)

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


# Global cache instance (lazy initialized with thread-safe access)
_cache: GeolocationCache | None = None
_cache_lock = threading.Lock()


def _get_cache() -> GeolocationCache:
    """Get or create the global cache instance (thread-safe with double-check)."""
    global _cache  # noqa: PLW0603
    if _cache is None:
        with _cache_lock:
            if _cache is None:  # Double-check after acquiring lock
                _cache = GeolocationCache()
    return _cache


def _get_nominatim_geolocator() -> object | None:
    """Get the Nominatim geolocator with proper user agent.

    Returns:
        Nominatim geolocator instance, or None if geopy unavailable.
    """
    try:
        from geopy.geocoders import Nominatim  # type: ignore[import-untyped]

        geolocator: object = Nominatim(user_agent="para-files/1.0")
    except ImportError:
        logger.warning("geopy not available for location lookup")
        return None
    else:
        return geolocator


@lru_cache(maxsize=256)
def _memory_cached_lookup(lat: float, lon: float) -> str | None:
    """In-memory LRU cache layer.

    Returns JSON string of address dict, or None.
    We return string because lru_cache needs hashable values.
    """
    # Check SQLite cache first
    cache = _get_cache()
    cached = cache.get(lat, lon)
    if cached is not None:
        return json.dumps(cached)

    # Not in cache, call Nominatim
    address = _fetch_from_nominatim(lat, lon)
    if address is not None:
        # Store in SQLite cache
        cache.set(lat, lon, address)
        return json.dumps(address)

    return None


def _fetch_from_nominatim(lat: float, lon: float) -> dict[str, str] | None:
    """Fetch location from Nominatim API.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        Raw address dictionary from geocoder, or None if lookup fails.
    """
    geolocator = _get_nominatim_geolocator()
    if geolocator is None:
        return None

    result: dict[str, str] | None = None
    try:
        from geopy.exc import (  # type: ignore[import-untyped]
            GeocoderTimedOut,
            GeocoderUnavailable,
        )

        # Use getattr to call reverse method on untyped geolocator
        reverse_func = getattr(geolocator, "reverse", None)
        if reverse_func is not None:
            location = reverse_func(
                (lat, lon),
                exactly_one=True,
                language="en",
                timeout=_GEOCODE_TIMEOUT,
            )

            if location is not None:
                raw = getattr(location, "raw", None)
                if raw is not None:
                    result = raw.get("address", {})
            else:
                logger.debug("No location found for coordinates: {}, {}", lat, lon)
    except GeocoderTimedOut:
        logger.debug("Geocoding timed out for: {}, {}", lat, lon)
    except GeocoderUnavailable:
        logger.debug("Geocoder service unavailable")
    except (ConnectionError, TimeoutError, OSError, ValueError) as e:
        logger.debug("Geocoding failed for: {}, {} ({})", lat, lon, e)

    return result


def reverse_geocode(latitude: float, longitude: float) -> LocationInfo | None:
    """Reverse geocode GPS coordinates to get location information.

    Uses Nominatim (OpenStreetMap) for reverse geocoding with two-level caching:
    1. In-memory LRU cache for fast repeated lookups
    2. SQLite persistent cache to avoid API calls across sessions

    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.

    Returns:
        LocationInfo with city/region/country, or None if lookup fails.
    """
    # Round coordinates for cache efficiency (about 100m precision)
    lat_rounded = round(latitude, 3)
    lon_rounded = round(longitude, 3)

    # Two-level cache lookup
    address_json = _memory_cached_lookup(lat_rounded, lon_rounded)
    if address_json is None:
        return None

    address: dict[str, str] = json.loads(address_json)

    # Extract location components
    # Nominatim returns different fields depending on location type
    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("hamlet")
    )

    region = address.get("state") or address.get("county") or address.get("province")

    country = address.get("country")
    country_code = address.get("country_code", "").upper() or None

    return LocationInfo(
        city=city,
        region=region,
        country=country,
        country_code=country_code,
    )


def get_location_folder(latitude: float, longitude: float) -> str | None:
    """Get a folder name for a GPS location.

    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.

    Returns:
        Filesystem-safe location folder name, or None if lookup fails.
    """
    location = reverse_geocode(latitude, longitude)
    if location is None:
        return None

    return location.folder_name


def get_cache_stats() -> dict[str, int]:
    """Get geolocation cache statistics.

    Returns:
        Dictionary with cache statistics including entry count.
    """
    return _get_cache().get_stats()


def clear_cache() -> None:
    """Clear the geolocation cache."""
    _get_cache().clear()
    _memory_cached_lookup.cache_clear()
