"""Telemetry calculation services (metrics, map layout, mission bounds)."""

from services.acceleration_service import compute_max_acceleration_ms2
from services.battery_metrics_service import compute_battery_metrics
from services.constants import (
    EARTH_RADIUS_M,
    LOW_VOLTAGE_THRESHOLD,
    MAP_TRAJECTORY_PADDING_FRAC,
    MAX_HDOP,
    MESSAGE_TYPES,
    MIN_SATS,
    MOTOR_MAX_PWM,
    MOTOR_MIN_PWM,
    MOTOR_SATURATION_MARGIN,
    VIBE_CRITICAL_THRESHOLD,
    VIBE_WARNING_THRESHOLD,
)
from services.flight_duration_service import compute_flight_duration
from services.geo import haversine, integrate_velocity, median_filter, wgs84_to_enu
from services.gps_quality import filter_gps_by_quality
from services.gps_track_metrics_service import compute_gps_track_metrics
from services.horizontal_speed_service import compute_max_horizontal_speed_ms
from services.map_view_service import compute_map_view_from_trajectory
from services.metrics import compute_metrics
from services.mission_bounds_service import MissionBoundsStats, compute_mission_bounds_stats
from services.vertical_speed_service import compute_max_vertical_speed_ms

__all__ = [
    'EARTH_RADIUS_M',
    'LOW_VOLTAGE_THRESHOLD',
    'MAP_TRAJECTORY_PADDING_FRAC',
    'MAX_HDOP',
    'MESSAGE_TYPES',
    'MIN_SATS',
    'MOTOR_MAX_PWM',
    'MOTOR_MIN_PWM',
    'MOTOR_SATURATION_MARGIN',
    'MissionBoundsStats',
    'VIBE_CRITICAL_THRESHOLD',
    'VIBE_WARNING_THRESHOLD',
    'compute_battery_metrics',
    'compute_flight_duration',
    'compute_gps_track_metrics',
    'compute_map_view_from_trajectory',
    'compute_max_acceleration_ms2',
    'compute_max_horizontal_speed_ms',
    'compute_max_vertical_speed_ms',
    'compute_metrics',
    'compute_mission_bounds_stats',
    'filter_gps_by_quality',
    'haversine',
    'integrate_velocity',
    'median_filter',
    'wgs84_to_enu',
]
