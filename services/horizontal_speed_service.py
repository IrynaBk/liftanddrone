"""Maximum reported horizontal speed from GPS."""

from typing import Dict, List


def compute_max_horizontal_speed_ms(gps_data: List[Dict]) -> float:
    """Max of GPS Spd field (m/s)."""
    if not gps_data:
        return 0.0
    speeds = [msg.get('Spd', 0) for msg in gps_data]
    return float(max(speeds)) if speeds else 0.0
