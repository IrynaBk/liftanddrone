"""Mission metric computation service."""

from __future__ import annotations

import math
from typing import Dict, List

import numpy as np

from service.geo.gps_quality import filter_gps_by_quality
from service.geo.gps_track_metrics import compute_gps_track_metrics
from service.common.integration import integrate_velocity
from service.metrics.warnings import compute_gyro_extremes_warning
from service.common.constants import GRAVITY_MS2


def compute_metrics(data: Dict[str, List[Dict]]) -> Dict:
    """Compute mission metrics from parsed telemetry and fused outputs."""
    metrics: Dict = {}

    gps_data = data.get("GPS", [])
    imu_data = data.get("IMU", [])
    bat_data = data.get("BAT", [])

    filtered_gps = filter_gps_by_quality(gps_data)

    if gps_data:
        duration_s = gps_data[-1]["TimeS"] - gps_data[0]["TimeS"]
        metrics["duration_s"] = duration_s
        minutes, seconds = divmod(int(duration_s), 60)
        metrics["duration_str"] = f"{minutes}:{seconds:02d}"
    else:
        metrics["duration_s"] = 0
        metrics["duration_str"] = "N/A"

    track = compute_gps_track_metrics(filtered_gps if filtered_gps else gps_data)
    metrics["distance_m"] = track.get("distance_m", 0.0)
    metrics["distance_km"] = metrics["distance_m"] / 1000.0
    metrics["max_alt_m"] = track.get("max_alt_m", 0.0)
    metrics["min_alt_m"] = track.get("min_alt_m", 0.0)
    metrics["alt_gain_m"] = track.get("alt_gain_m", 0.0)
    metrics["distance_warning"] = track.get("distance_warning")
    metrics["alt_gain_warning"] = track.get("alt_gain_warning")

    if filtered_gps:
        h_speeds = [msg.get("Spd", 0) for msg in filtered_gps]
        max_h_speed = max(h_speeds)
        metrics["max_h_speed_ms"] = max_h_speed
        metrics["max_h_speed_kmh"] = max_h_speed * 3.6

        vz_values = [abs(msg.get("VZ", 0)) for msg in filtered_gps]
        max_v_speed = max(vz_values) if vz_values else 0.0
        metrics["max_v_speed_ms"] = max_v_speed
        metrics["max_v_speed_kmh"] = max_v_speed * 3.6

        max_total_speed = 0.0
        for msg in filtered_gps:
            h_speed = msg.get("Spd", 0)
            v_speed = abs(msg.get("VZ", 0))
            total_speed = math.sqrt(h_speed**2 + v_speed**2)
            max_total_speed = max(max_total_speed, total_speed)
        metrics["max_total_speed_ms"] = max_total_speed
        metrics["max_total_speed_kmh"] = max_total_speed * 3.6

        sats = [msg.get("NSats", 0) for msg in filtered_gps]
        metrics["avg_sats"] = float(np.mean(sats)) if sats else 0.0
    else:
        metrics["max_h_speed_ms"] = 0.0
        metrics["max_h_speed_kmh"] = 0.0
        metrics["max_v_speed_ms"] = 0.0
        metrics["max_v_speed_kmh"] = 0.0
        metrics["max_total_speed_ms"] = 0.0
        metrics["max_total_speed_kmh"] = 0.0
        metrics["avg_sats"] = 0.0

    if imu_data:
        max_accel = 0.0
        for msg in imu_data:
            ax = msg.get("AccX", 0)
            ay = msg.get("AccY", 0)
            az = msg.get("AccZ", 0)
            accel_mag = math.sqrt(ax**2 + ay**2 + az**2)
            dynamic_accel = abs(accel_mag - GRAVITY_MS2)
            max_accel = max(max_accel, dynamic_accel)
        metrics["max_accel_ms2"] = max_accel
    else:
        metrics["max_accel_ms2"] = 0.0

    if len(imu_data) > 1:
        imu_times = np.array([msg["TimeS"] for msg in imu_data])
        acc_x = np.array([msg.get("AccX", 0) for msg in imu_data])
        acc_y = np.array([msg.get("AccY", 0) for msg in imu_data])
        acc_z = np.array([msg.get("AccZ", 0) for msg in imu_data]) + GRAVITY_MS2

        vel_x = integrate_velocity(acc_x, imu_times)
        vel_y = integrate_velocity(acc_y, imu_times)
        vel_z = integrate_velocity(acc_z, imu_times)

        imu_speed = np.sqrt(vel_x**2 + vel_y**2 + vel_z**2)
        metrics["max_imu_speed_ms"] = float(np.max(imu_speed))
    else:
        metrics["max_imu_speed_ms"] = 0.0

    if bat_data:
        currents = [msg.get("Curr", 0) for msg in bat_data]
        metrics["avg_current_a"] = float(np.mean(currents)) if currents else 0.0

        curr_tots = [msg.get("CurrTot", 0) for msg in bat_data]
        metrics["energy_used_mah"] = curr_tots[-1] if curr_tots else 0.0
    else:
        metrics["avg_current_a"] = 0.0
        metrics["energy_used_mah"] = 0.0

    ekf = data.get("EKF")
    if ekf and ekf.get("speed"):
        metrics["ekf_max_speed_ms"] = max(ekf["speed"])
        metrics["ekf_max_speed_kmh"] = metrics["ekf_max_speed_ms"] * 3.6
        metrics["ekf_max_h_speed_ms"] = max(ekf["h_speed"])
        metrics["ekf_max_h_speed_kmh"] = metrics["ekf_max_h_speed_ms"] * 3.6
        metrics["ekf_max_v_speed_ms"] = max(ekf["v_speed"])
        metrics["ekf_max_v_speed_kmh"] = metrics["ekf_max_v_speed_ms"] * 3.6
        metrics["ekf_available"] = True
        metrics["ekf_board_rotation"] = ekf.get("board_rotation_applied", False)
    else:
        metrics["ekf_available"] = False

    metrics["battery_warning"] = (
        "No battery telemetry (BAT) in this log; energy and current are unavailable."
        if not bat_data
        else None
    )
    metrics["gyro_extremes_warning"] = compute_gyro_extremes_warning(imu_data)
    metrics["speed_warning"] = None

    return metrics
