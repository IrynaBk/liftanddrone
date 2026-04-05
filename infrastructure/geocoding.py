"""Reverse geocoding via Nominatim."""

from typing import Dict

import streamlit as st
from geopy.geocoders import Nominatim


@st.cache_data
def reverse_geocode(latitude: float, longitude: float) -> Dict[str, str]:
    """Get country, city, and address from coordinates.

    Returns gracefully with "Not available" if geocoding fails.

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.

    Returns:
        Dictionary with 'country', 'city', and 'address' keys.
    """
    try:
        geolocator = Nominatim(user_agent="droneviz_analyzer")
        location = geolocator.reverse(f"{latitude}, {longitude}", language='en', timeout=5)

        address_parts = location.address.split(',')

        country = None
        city = None
        address = None

        if len(address_parts) >= 1:
            address = address_parts[0].strip()
        if len(address_parts) >= 2:
            city = address_parts[-2].strip()
        if len(address_parts) >= 1:
            country = address_parts[-1].strip()

        return {
            'country': country or 'Not available',
            'city': city or 'Not available',
            'address': address or 'Not available',
        }
    except Exception:
        return {
            'country': 'Not available',
            'city': 'Not available',
            'address': 'Not available',
        }
