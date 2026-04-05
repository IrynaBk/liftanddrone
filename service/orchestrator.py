"""Single orchestration entry point for telemetry processing.

All pipeline stages and query helpers are accessed exclusively through this
module. Views and the data loader must not import from individual service
sub-packages directly.

Pipeline:
  parse_log → run_ekf_on_log → compute_metrics

Query helpers (stateless, for use by views):
  get_filtered_gps, get_mission_bounds, get_map_view, get_firmware_version
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from service.common.parser import parse_log
from service.fusion.ekf_runner import run_ekf_on_log
from service.metrics.metrics import compute_metrics
from service.geo.gps_quality import filter_gps_by_quality
from service.geo.mission_bounds import compute_mission_bounds_stats
from service.geo.map_view import compute_map_view_from_trajectory


# ---------------------------------------------------------------------------
# Pipeline entry points
# ---------------------------------------------------------------------------

def process_data(data: Dict[str, List[Dict]]) -> Tuple[Dict[str, List[Dict]], Dict]:
    """Run EKF fusion + metric computation over already-parsed telemetry."""
    data["EKF"] = run_ekf_on_log(data)
    metrics = compute_metrics(data)
    return data, metrics


def process_log_file(filepath: str) -> Tuple[Dict[str, List[Dict]], Dict]:
    """Parse a binary .bin log file and run the full processing pipeline."""
    parsed = parse_log(filepath)
    return process_data(parsed)


# ---------------------------------------------------------------------------
# Query helpers — views call these instead of importing sub-packages
# ---------------------------------------------------------------------------

def get_filtered_gps(data: Dict) -> List[Dict]:
    """Return quality-filtered GPS records (HDop / NSats thresholds)."""
    return filter_gps_by_quality(data.get("GPS", []))


def get_mission_bounds(data: Dict):
    """Return MissionBoundsStats dataclass or None if no valid GPS."""
    return compute_mission_bounds_stats(data.get("GPS", []))


def get_map_view(
    lats: List[float],
    lons: List[float],
    width_px: float = 960.0,
    height_px: float = 600.0,
) -> Tuple[float, float, float]:
    """Return (center_lat, center_lon, zoom) for a Plotly/Mapbox map."""
    return compute_map_view_from_trajectory(lats, lons, width_px, height_px)


def get_firmware_version(data: Dict) -> Optional[str]:
    """Extract firmware version string from MSG records, or None."""
    for msg in data.get("MSG", []):
        message = msg.get("Message", "")
        if "ArduCopter" in message or "ArduPlane" in message or "Rover" in message:
            return message
    return None
