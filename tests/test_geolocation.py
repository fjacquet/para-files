"""Tests for the geolocation module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from para_files.utils.geolocation import (
    LocationInfo,
    _cached_reverse_geocode,
    _get_nominatim_geolocator,
    get_location_folder,
    reverse_geocode,
)


class TestLocationInfo:
    """Tests for LocationInfo model."""

    def test_all_fields(self):
        """Test LocationInfo with all fields populated."""
        info = LocationInfo(
            city="Geneva",
            region="Geneva",
            country="Switzerland",
            country_code="CH",
        )
        assert info.city == "Geneva"
        assert info.region == "Geneva"
        assert info.country == "Switzerland"
        assert info.country_code == "CH"

    def test_default_values(self):
        """Test LocationInfo with default values."""
        info = LocationInfo()
        assert info.city is None
        assert info.region is None
        assert info.country is None
        assert info.country_code is None

    def test_display_name_city(self):
        """Test display_name prefers city."""
        info = LocationInfo(city="Geneva", region="Canton", country="Switzerland")
        assert info.display_name == "Geneva"

    def test_display_name_region(self):
        """Test display_name falls back to region."""
        info = LocationInfo(region="Canton", country="Switzerland")
        assert info.display_name == "Canton"

    def test_display_name_country(self):
        """Test display_name falls back to country."""
        info = LocationInfo(country="Switzerland")
        assert info.display_name == "Switzerland"

    def test_display_name_unknown(self):
        """Test display_name returns Unknown when empty."""
        info = LocationInfo()
        assert info.display_name == "Unknown"

    def test_folder_name_simple(self):
        """Test folder_name for simple city name."""
        info = LocationInfo(city="Geneva")
        assert info.folder_name == "Geneva"

    def test_folder_name_with_spaces(self):
        """Test folder_name replaces spaces with underscores."""
        info = LocationInfo(city="New York")
        assert info.folder_name == "New_York"

    def test_folder_name_with_forbidden_chars(self):
        """Test folder_name removes forbidden filesystem characters."""
        info = LocationInfo(city='City: "Test" <name>')
        assert "<" not in info.folder_name
        assert ">" not in info.folder_name
        assert ":" not in info.folder_name
        assert '"' not in info.folder_name

    def test_folder_name_strips_underscores(self):
        """Test folder_name strips leading/trailing underscores."""
        info = LocationInfo(city="  Test City  ")
        assert not info.folder_name.startswith("_")
        assert not info.folder_name.endswith("_")

    def test_folder_name_unknown_fallback(self):
        """Test folder_name returns Unknown for empty location."""
        info = LocationInfo()
        assert info.folder_name == "Unknown"


class TestGetNominatimGeolocator:
    """Tests for _get_nominatim_geolocator function."""

    @patch("geopy.geocoders.Nominatim")
    def test_returns_geolocator(self, mock_nominatim: MagicMock):
        """Test that geolocator is returned when geopy available."""
        mock_instance = MagicMock()
        mock_nominatim.return_value = mock_instance

        result = _get_nominatim_geolocator()

        assert result is mock_instance
        mock_nominatim.assert_called_once_with(user_agent="para-files/1.0")

    def test_returns_none_when_geopy_unavailable(self):
        """Test that None is returned when geopy is not installed."""
        # Since geopy is imported inside the function, we need to make import fail
        import builtins
        import sys

        # Save original modules
        geopy_backup = sys.modules.get("geopy")
        geopy_geocoders_backup = sys.modules.get("geopy.geocoders")
        original_import = builtins.__import__

        try:
            # Remove geopy from modules to simulate it being unavailable
            if "geopy" in sys.modules:
                del sys.modules["geopy"]
            if "geopy.geocoders" in sys.modules:
                del sys.modules["geopy.geocoders"]

            def mock_import(name, *args, **kwargs):
                if name == "geopy.geocoders" or name.startswith("geopy"):
                    raise ImportError(name)
                return original_import(name, *args, **kwargs)

            builtins.__import__ = mock_import
            result = _get_nominatim_geolocator()
            assert result is None
        finally:
            # Restore modules and import
            builtins.__import__ = original_import
            if geopy_backup:
                sys.modules["geopy"] = geopy_backup
            if geopy_geocoders_backup:
                sys.modules["geopy.geocoders"] = geopy_geocoders_backup


class TestCachedReverseGeocode:
    """Tests for _cached_reverse_geocode function."""

    def setup_method(self):
        """Clear cache before each test."""
        _cached_reverse_geocode.cache_clear()

    @patch("para_files.utils.geolocation._get_nominatim_geolocator")
    def test_returns_none_when_geolocator_unavailable(self, mock_get_geo: MagicMock):
        """Test returns None when geolocator is not available."""
        mock_get_geo.return_value = None

        result = _cached_reverse_geocode(46.2, 6.1)

        assert result is None

    @patch("para_files.utils.geolocation._get_nominatim_geolocator")
    def test_successful_lookup(self, mock_get_geo: MagicMock):
        """Test successful reverse geocode lookup."""
        mock_location = MagicMock()
        mock_location.raw = {"address": {"city": "Geneva", "country": "Switzerland"}}

        mock_geolocator = MagicMock()
        mock_geolocator.reverse.return_value = mock_location
        mock_get_geo.return_value = mock_geolocator

        result = _cached_reverse_geocode(46.2, 6.1)

        assert result == {"city": "Geneva", "country": "Switzerland"}

    @patch("para_files.utils.geolocation._get_nominatim_geolocator")
    def test_no_location_found(self, mock_get_geo: MagicMock):
        """Test when no location is found for coordinates."""
        mock_geolocator = MagicMock()
        mock_geolocator.reverse.return_value = None
        mock_get_geo.return_value = mock_geolocator

        result = _cached_reverse_geocode(0.0, 0.0)

        assert result is None

    @patch("para_files.utils.geolocation._get_nominatim_geolocator")
    def test_handles_timeout(self, mock_get_geo: MagicMock):
        """Test handling of geocoder timeout."""
        from geopy.exc import GeocoderTimedOut

        mock_geolocator = MagicMock()
        mock_geolocator.reverse.side_effect = GeocoderTimedOut("Timeout")
        mock_get_geo.return_value = mock_geolocator

        result = _cached_reverse_geocode(46.2, 6.1)

        assert result is None

    @patch("para_files.utils.geolocation._get_nominatim_geolocator")
    def test_handles_unavailable(self, mock_get_geo: MagicMock):
        """Test handling of geocoder unavailable."""
        from geopy.exc import GeocoderUnavailable

        mock_geolocator = MagicMock()
        mock_geolocator.reverse.side_effect = GeocoderUnavailable("Service down")
        mock_get_geo.return_value = mock_geolocator

        result = _cached_reverse_geocode(46.2, 6.1)

        assert result is None

    @patch("para_files.utils.geolocation._get_nominatim_geolocator")
    def test_handles_generic_exception(self, mock_get_geo: MagicMock):
        """Test handling of generic exceptions."""
        mock_geolocator = MagicMock()
        mock_geolocator.reverse.side_effect = Exception("Unknown error")
        mock_get_geo.return_value = mock_geolocator

        result = _cached_reverse_geocode(46.2, 6.1)

        assert result is None

    @patch("para_files.utils.geolocation._get_nominatim_geolocator")
    def test_caching_works(self, mock_get_geo: MagicMock):
        """Test that results are cached."""
        mock_location = MagicMock()
        mock_location.raw = {"address": {"city": "Geneva"}}

        mock_geolocator = MagicMock()
        mock_geolocator.reverse.return_value = mock_location
        mock_get_geo.return_value = mock_geolocator

        # Call twice with same coordinates
        result1 = _cached_reverse_geocode(46.2, 6.1)
        result2 = _cached_reverse_geocode(46.2, 6.1)

        # Should only call reverse once due to caching
        assert mock_geolocator.reverse.call_count == 1
        assert result1 == result2


class TestReverseGeocode:
    """Tests for reverse_geocode function."""

    def setup_method(self):
        """Clear cache before each test."""
        _cached_reverse_geocode.cache_clear()

    @patch("para_files.utils.geolocation._cached_reverse_geocode")
    def test_returns_none_when_cache_returns_none(self, mock_cache: MagicMock):
        """Test returns None when cached lookup fails."""
        mock_cache.return_value = None

        result = reverse_geocode(46.2, 6.1)

        assert result is None

    @patch("para_files.utils.geolocation._cached_reverse_geocode")
    def test_extracts_city_fields(self, mock_cache: MagicMock):
        """Test extraction of various city field types."""
        # Test with 'city' field
        mock_cache.return_value = {"city": "Geneva", "country": "Switzerland"}
        result = reverse_geocode(46.2, 6.1)
        assert result is not None
        assert result.city == "Geneva"

    @patch("para_files.utils.geolocation._cached_reverse_geocode")
    def test_extracts_town_field(self, mock_cache: MagicMock):
        """Test extraction with 'town' field."""
        mock_cache.return_value = {"town": "Nyon", "country": "Switzerland"}
        result = reverse_geocode(46.38, 6.24)
        assert result is not None
        assert result.city == "Nyon"

    @patch("para_files.utils.geolocation._cached_reverse_geocode")
    def test_extracts_village_field(self, mock_cache: MagicMock):
        """Test extraction with 'village' field."""
        mock_cache.return_value = {"village": "Tannay", "country": "Switzerland"}
        result = reverse_geocode(46.31, 6.19)
        assert result is not None
        assert result.city == "Tannay"

    @patch("para_files.utils.geolocation._cached_reverse_geocode")
    def test_extracts_region_fields(self, mock_cache: MagicMock):
        """Test extraction of region field types."""
        mock_cache.return_value = {"state": "Vaud", "country": "Switzerland"}
        result = reverse_geocode(46.5, 6.6)
        assert result is not None
        assert result.region == "Vaud"

    @patch("para_files.utils.geolocation._cached_reverse_geocode")
    def test_extracts_country_code(self, mock_cache: MagicMock):
        """Test extraction of country code."""
        mock_cache.return_value = {"country": "Switzerland", "country_code": "ch"}
        result = reverse_geocode(46.2, 6.1)
        assert result is not None
        assert result.country_code == "CH"  # Should be uppercase

    @patch("para_files.utils.geolocation._cached_reverse_geocode")
    def test_rounds_coordinates(self, mock_cache: MagicMock):
        """Test that coordinates are rounded for cache efficiency."""
        mock_cache.return_value = {"city": "Test"}

        reverse_geocode(46.12345, 6.12345)

        # Should be called with rounded coordinates (3 decimal places)
        mock_cache.assert_called_once_with(46.123, 6.123)

    @patch("para_files.utils.geolocation._cached_reverse_geocode")
    def test_full_location_info(self, mock_cache: MagicMock):
        """Test extraction of complete location info."""
        mock_cache.return_value = {
            "city": "Geneva",
            "state": "Geneva",
            "country": "Switzerland",
            "country_code": "ch",
        }

        result = reverse_geocode(46.2, 6.1)

        assert result is not None
        assert result.city == "Geneva"
        assert result.region == "Geneva"
        assert result.country == "Switzerland"
        assert result.country_code == "CH"


class TestGetLocationFolder:
    """Tests for get_location_folder function."""

    def setup_method(self):
        """Clear cache before each test."""
        _cached_reverse_geocode.cache_clear()

    @patch("para_files.utils.geolocation.reverse_geocode")
    def test_returns_folder_name(self, mock_reverse: MagicMock):
        """Test returns folder name for valid location."""
        mock_reverse.return_value = LocationInfo(city="Geneva")

        result = get_location_folder(46.2, 6.1)

        assert result == "Geneva"

    @patch("para_files.utils.geolocation.reverse_geocode")
    def test_returns_none_when_no_location(self, mock_reverse: MagicMock):
        """Test returns None when reverse geocode fails."""
        mock_reverse.return_value = None

        result = get_location_folder(0.0, 0.0)

        assert result is None

    @patch("para_files.utils.geolocation.reverse_geocode")
    def test_returns_sanitized_folder_name(self, mock_reverse: MagicMock):
        """Test returns sanitized folder name."""
        mock_reverse.return_value = LocationInfo(city="New York City")

        result = get_location_folder(40.7, -74.0)

        assert result == "New_York_City"
