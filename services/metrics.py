"""Aggregate all mission summary metrics from parsed log data."""

from typing import Dict, List

from services.acceleration_service import compute_max_acceleration_ms2
from services.battery_metrics_service import compute_battery_metrics
from services.flight_duration_service import compute_flight_duration
from services.gps_track_metrics_service import compute_gps_track_metrics
from services.horizontal_speed_service import compute_max_horizontal_speed_ms
from services.vertical_speed_service import compute_max_vertical_speed_ms


def compute_metrics(data: Dict[str, List[Dict]]) -> Dict:
    """
    Compute all mission metrics from parsed log data.

    Returns:
        Dictionary with duration, distance, speeds, altitude gain, acceleration, battery.
    """
    gps_data = data.get('GPS', [])
    imu_data = data.get('IMU', [])
    bat_data = data.get('BAT', [])

    metrics: Dict = {}

    if gps_data:
        duration_s, duration_str = compute_flight_duration(gps_data)
        metrics['duration_s'] = duration_s
        metrics['duration_str'] = duration_str
    else:
        metrics['duration_s'] = 0
        metrics['duration_str'] = "N/A"

    track = compute_gps_track_metrics(gps_data)
    metrics['distance_m'] = track['distance_m']
    metrics['max_alt_m'] = track['max_alt_m']
    metrics['min_alt_m'] = track['min_alt_m']
    metrics['alt_gain_m'] = track['alt_gain_m']
    metrics['alt_gain_warning'] = track.get('alt_gain_warning')
    metrics['distance_warning'] = track.get('distance_warning')

    metrics['max_h_speed_ms'] = compute_max_horizontal_speed_ms(gps_data)
    metrics['max_v_speed_ms'] = compute_max_vertical_speed_ms(gps_data)
    metrics['max_accel_ms2'] = compute_max_acceleration_ms2(imu_data)

    avg_current_a, energy_used_mah = compute_battery_metrics(bat_data)
    metrics['avg_current_a'] = avg_current_a
    metrics['energy_used_mah'] = energy_used_mah

    return metrics
