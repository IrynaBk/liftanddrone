"""Map layout: center and zoom to fit a lat/lon trajectory."""

from __future__ import annotations

import math
from typing import List, Tuple

from services.constants import MAP_TRAJECTORY_PADDING_FRAC


def compute_map_view_from_trajectory(
    lats: List[float],
    lons: List[float],
    width_px: float = 960.0,
    height_px: float = 600.0,
    padding_frac: float = MAP_TRAJECTORY_PADDING_FRAC,
) -> Tuple[float, float, float]:
    """
    Center lat/lon and zoom level for Plotly map layout so the path fits
    with ``padding_frac`` × span margin on each side (N/S and E/W).
    """
    if len(lats) < 2 or len(lons) < 2:
        return (float(lats[0]), float(lons[0]), 16.0)

    lat_to, lon_to = lats[0], lons[0]
    lat_ld, lon_ld = lats[-1], lons[-1]

    lat_min_raw, lat_max_raw = min(lats), max(lats)
    lon_min_raw, lon_max_raw = min(lons), max(lons)

    lat_span = lat_max_raw - lat_min_raw
    lon_span = lon_max_raw - lon_min_raw

    if lat_span < 1e-9 and lon_span < 1e-9:
        return ((lat_to + lat_ld) / 2.0, (lon_to + lon_ld) / 2.0, 17.0)

    if lat_span < 0.0001:
        lat_span = 0.01
    if lon_span < 0.0001:
        lon_span = 0.01

    dlat = padding_frac * lat_span
    dlon = padding_frac * lon_span

    lat_min = lat_min_raw - dlat
    lat_max = lat_max_raw + dlat
    lon_min = lon_min_raw - dlon
    lon_max = lon_max_raw + dlon

    lat_range = lat_max - lat_min
    lon_range = lon_max - lon_min

    lat_center = (lat_min + lat_max) / 2.0
    lon_center = (lon_min + lon_max) / 2.0
    cos_lat = max(math.cos(math.radians(lat_center)), 0.2)

    zoom_lon = math.log2(360.0 * width_px * cos_lat / (256.0 * lon_range))
    zoom_lat = math.log2(180.0 * height_px / (256.0 * lat_range))
    zoom = min(zoom_lon, zoom_lat)

    zoom = max(8.0, min(20.0, zoom))
    return (lat_center, lon_center, zoom)
