"""Data loading, parsing, and geocoding functions."""

import streamlit as st
import tempfile
import os
from typing import Dict, Tuple, Optional
from geopy.geocoders import Nominatim
from drone_dashboard import parse_log, compute_metrics


@st.cache_data
def load_data_from_bytes(file_bytes: bytes) -> Tuple[Dict, Dict]:
    """
    Parse log from uploaded bytes and compute metrics.
    Cached to avoid re-parsing on re-renders.

    Args:
        file_bytes: Raw bytes from uploaded file

    Returns:
        Tuple of (data dict, metrics dict)
    """
    # Write bytes to temporary file (parse_log expects a filepath)
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        data = parse_log(tmp_path)
        metrics = compute_metrics(data)
        return data, metrics
    finally:
        # Clean up temp file - handle Windows file locking
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except (PermissionError, OSError):
            # File may still be locked on Windows; OS will clean it up eventually
            pass


def extract_firmware_version(data: Dict) -> Optional[str]:
    """
    Extract firmware version from MSG records if available.

    Args:
        data: Parsed log data

    Returns:
        Firmware version string or None
    """
    msg_data = data.get('MSG', [])
    for msg in msg_data:
        message = msg.get('Message', '')
        if 'ArduCopter' in message or 'ArduPlane' in message or 'Rover' in message:
            return message
    return None


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
