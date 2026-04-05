"""Maximum vertical speed from GPS altitude differences."""

from typing import Dict, List


def compute_max_vertical_speed_ms(gps_data: List[Dict]) -> float:
    """Peak |dAlt/dt| between consecutive GPS samples."""
    if len(gps_data) <= 1:
        return 0.0
    alts = [msg.get('Alt', 0) for msg in gps_data]
    times = [msg['TimeS'] for msg in gps_data]
    max_v_speed = 0.0
    for i in range(1, len(alts)):
        dt = times[i] - times[i - 1]
        if dt > 0:
            v_speed = abs(alts[i] - alts[i - 1]) / dt
            max_v_speed = max(max_v_speed, v_speed)
    return float(max_v_speed)
