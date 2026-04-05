"""Mission geographic bounds and GPS quality summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from services.gps_quality import filter_gps_by_quality


@dataclass(frozen=True)
class MissionBoundsStats:
    takeoff_loc: str
    landing_loc: str
    bounds_box: str
    num_valid: int
    num_total: int
    avg_hdop: float
    avg_sats: float


def compute_mission_bounds_stats(gps_data: List[Dict]) -> Optional[MissionBoundsStats]:
    """Aggregate stats for quality-filtered GPS; None if no valid points."""
    filtered_gps = filter_gps_by_quality(gps_data)
    if not filtered_gps:
        return None

    lats = [msg.get('Lat', 0) for msg in filtered_gps]
    lons = [msg.get('Lng', 0) for msg in filtered_gps]
    hdops = [msg.get('HDop', 0) for msg in filtered_gps]
    nsats = [msg.get('NSats', 0) for msg in filtered_gps]

    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)

    takeoff_loc = f"{lats[0]:.4f}° N, {lons[0]:.4f}° E"
    landing_loc = f"{lats[-1]:.4f}° N, {lons[-1]:.4f}° E"
    bounds_box = f"NE: {lat_max:.4f}°, {lon_max:.4f}° | SW: {lat_min:.4f}°, {lon_min:.4f}°"

    return MissionBoundsStats(
        takeoff_loc=takeoff_loc,
        landing_loc=landing_loc,
        bounds_box=bounds_box,
        num_valid=len(filtered_gps),
        num_total=len(gps_data),
        avg_hdop=float(np.mean(hdops)),
        avg_sats=float(np.mean(nsats)),
    )
