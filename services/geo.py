"""Geodesy helpers and numeric utilities used by metric services."""

from __future__ import annotations

import math
from typing import List, Tuple

import numpy as np

from services.constants import EARTH_RADIUS_M


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS-84 coordinates (meters)."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_M * c


def median_filter(values: List[float], k: int) -> List[float]:
    """Sliding-window median with edge padding. k must be odd."""
    pad = k // 2
    arr = np.asarray(values, dtype=float)
    padded = np.pad(arr, pad, mode="edge")
    out = np.empty_like(arr)
    for i in range(len(arr)):
        out[i] = np.median(padded[i: i + k])
    return out.tolist()


def integrate_velocity(accel_array: np.ndarray, time_array: np.ndarray) -> np.ndarray:
    """
    Integrate acceleration over time to produce velocity using trapezoidal rule.
    Returns velocity (m/s) with initial velocity = 0.
    """
    if len(accel_array) < 2:
        return accel_array

    velocity = np.zeros_like(accel_array, dtype=float)
    for i in range(1, len(accel_array)):
        dt = time_array[i] - time_array[i - 1]
        if dt > 0:
            velocity[i] = velocity[i - 1] + (accel_array[i - 1] + accel_array[i]) / 2.0 * dt

    return velocity


def wgs84_to_enu(
    lat: float, lon: float, alt: float,
    lat0: float, lon0: float, alt0: float,
) -> Tuple[float, float, float]:
    """
    WGS-84 geodetic to local ENU (flat-Earth, scales < ~10 km).
    Returns (east, north, up) in meters relative to origin.
    """
    lat0_rad = math.radians(lat0)
    east = (lon - lon0) * math.cos(lat0_rad) * EARTH_RADIUS_M * math.pi / 180.0
    north = (lat - lat0) * EARTH_RADIUS_M * math.pi / 180.0
    up = alt - alt0
    return east, north, up
