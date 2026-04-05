"""Geodesy and coordinate transforms for telemetry processing."""

from __future__ import annotations

import math
from typing import Tuple

from service.common.constants import EARTH_RADIUS_M


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 coordinates in meters."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_M * c


def llh_to_ned(
    lat: float,
    lon: float,
    alt: float,
    ref_lat: float,
    ref_lon: float,
    ref_alt: float,
) -> Tuple[float, float, float]:
    """Convert WGS84 LLH to local NED coordinates (meters)."""
    ref_lat_rad = math.radians(ref_lat)

    north = (lat - ref_lat) * EARTH_RADIUS_M * math.pi / 180.0
    east = (lon - ref_lon) * math.cos(ref_lat_rad) * EARTH_RADIUS_M * math.pi / 180.0
    down = ref_alt - alt

    return north, east, down


def wgs84_to_enu(
    lat: float,
    lon: float,
    alt: float,
    lat0: float,
    lon0: float,
    alt0: float,
) -> Tuple[float, float, float]:
    """Convert WGS84 geodetic point to local ENU frame in meters."""
    lat0_rad = math.radians(lat0)
    east = (lon - lon0) * math.cos(lat0_rad) * EARTH_RADIUS_M * math.pi / 180.0
    north = (lat - lat0) * EARTH_RADIUS_M * math.pi / 180.0
    up = alt - alt0
    return east, north, up


def normalize_gps_measurement(
    gps_record: dict,
    ref_lat: float,
    ref_lon: float,
    ref_alt: float,
) -> Tuple[float, float, float]:
    """
    Normalize GPS position measurement to NED frame with sign consistency.

    CRITICAL: ArduPilot logs record altitude (Alt) in Up system. 
    This function aligns it to the canonical NED Down coordinate 
    before EKF fusion. Only position is extracted and normalized.

    Args:
        gps_record: Dict with 'Lat', 'Lng', 'Alt' fields
        ref_lat, ref_lon, ref_alt: Reference point for NED origin

    Returns:
        (north, east, down) position in NED meters
    """
    lat = float(gps_record.get("Lat", 0.0))
    lon = float(gps_record.get("Lng", 0.0))
    alt = float(gps_record.get("Alt", 0.0))

    return llh_to_ned(lat, lon, alt, ref_lat, ref_lon, ref_alt)
