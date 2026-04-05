"""Flight duration from GPS time span."""

from typing import Dict, List, Tuple


def compute_flight_duration(gps_data: List[Dict]) -> Tuple[float, str]:
    """
    Duration between first and last GPS sample.

    Returns:
        (duration_s, human-readable "M:SS" or "N/A" when no data)
    """
    if not gps_data:
        return 0.0, "N/A"
    duration_s = gps_data[-1]['TimeS'] - gps_data[0]['TimeS']
    minutes, seconds = divmod(int(duration_s), 60)
    return duration_s, f"{minutes}:{seconds:02d}"
