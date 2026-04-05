"""Data loading, parsing, and geocoding functions."""

import streamlit as st
import tempfile
import os
from typing import Dict, Tuple, Optional
from geopy.geocoders import Nominatim
from service.orchestrator import process_log_file, get_firmware_version as _get_firmware_version


@st.cache_data
def load_data_from_bytes(file_bytes: bytes) -> Tuple[Dict, Dict]:
    """
    Parse log from uploaded bytes and run full telemetry processing orchestrator.
    Cached to avoid re-parsing on re-renders.

    Args:
        file_bytes: Raw bytes from uploaded file

    Returns:
        Tuple of (data dict, metrics dict) returned by processing orchestrator.
    """
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        return process_log_file(tmp_path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except (PermissionError, OSError):
            pass


def extract_firmware_version(data: Dict) -> Optional[str]:
    """Extract firmware version from MSG records. Delegates to orchestrator."""
    return _get_firmware_version(data)


@st.cache_data
def reverse_geocode(latitude: float, longitude: float) -> Dict[str, str]:
    """
    Get country, city, and address from coordinates using reverse geocoding.
    Returns gracefully with "Not available" if geocoding fails.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        Dictionary with 'country', 'city', and 'address' keys
    """
    try:
        geolocator = Nominatim(user_agent="droneviz_analyzer")
        location = geolocator.reverse(f"{latitude}, {longitude}", language='en', timeout=5)
        
        address_parts = location.address.split(',')
        
        country = None
        city = None
        address = None
        
        # Try to extract meaningful parts from the address
        if len(address_parts) >= 1:
            address = address_parts[0].strip()
        if len(address_parts) >= 2:
            city = address_parts[-2].strip()
        if len(address_parts) >= 1:
            country = address_parts[-1].strip()
        
        return {
            'country': country or 'Not available',
            'city': city or 'Not available',
            'address': address or 'Not available'
        }
    except Exception:
        return {
            'country': 'Not available',
            'city': 'Not available',
            'address': 'Not available'
        }
