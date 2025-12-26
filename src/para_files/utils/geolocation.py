"""Geolocation utilities for GPS coordinate lookup.

Uses geopy to reverse geocode GPS coordinates into location names.
Falls back gracefully when geocoding fails or times out.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)

# Default timeout for geocoding requests
_GEOCODE_TIMEOUT = 5


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
        """Return a filesystem-safe folder name for the location."""
        name = self.display_name
        # Replace forbidden characters and normalize
        safe = re.sub(r'[<>:"/\\|?*]', "_", name)
        safe = re.sub(r"\s+", "_", safe)
        safe = safe.strip("_")
        return safe or "Unknown"


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
def _cached_reverse_geocode(lat: float, lon: float) -> dict[str, str] | None:
    """Cached reverse geocode lookup.

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
                logger.debug("No location found for coordinates: %s, %s", lat, lon)
    except GeocoderTimedOut:
        logger.debug("Geocoding timed out for: %s, %s", lat, lon)
    except GeocoderUnavailable:
        logger.debug("Geocoder service unavailable")
    except Exception:  # noqa: BLE001
        logger.debug("Geocoding failed for: %s, %s", lat, lon, exc_info=True)

    return result


def reverse_geocode(latitude: float, longitude: float) -> LocationInfo | None:
    """Reverse geocode GPS coordinates to get location information.

    Uses Nominatim (OpenStreetMap) for reverse geocoding with caching
    to avoid repeated API calls for the same coordinates.

    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.

    Returns:
        LocationInfo with city/region/country, or None if lookup fails.
    """
    # Round coordinates for cache efficiency (about 100m precision)
    lat_rounded = round(latitude, 3)
    lon_rounded = round(longitude, 3)

    address = _cached_reverse_geocode(lat_rounded, lon_rounded)
    if address is None:
        return None

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
