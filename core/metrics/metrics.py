"""Mission metric computation."""

from __future__ import annotations

import math
from typing import Dict, List

import numpy as np

from core.geo.gps_quality import filter_gps_by_quality
from core.geo.gps_track_metrics import compute_gps_track_metrics
from core.imu.integration import integrate_velocity
from core.metrics.warnings import compute_gyro_extremes_warning
from core.constants import GRAVITY_MS2


def _compute_duration(gps_data: List[Dict]) -> Dict:
    if gps_data:
        duration_s = gps_data[-1]["TimeS"] - gps_data[0]["TimeS"]
        minutes, seconds = divmod(int(duration_s), 60)
        return {"duration_s": duration_s, "duration_str": f"{minutes}:{seconds:02d}"}
    return {"duration_s": 0, "duration_str": "N/A"}


def _compute_gps_metrics(filtered_gps: List[Dict], gps_data: List[Dict]) -> Dict:
    source_gps = filtered_gps if filtered_gps else gps_data
    track = compute_gps_track_metrics(source_gps)

    out: Dict = {
        "distance_m":       track.get("distance_m", 0.0),
        "distance_km":      track.get("distance_m", 0.0) / 1000.0,
        "max_alt_m":        track.get("max_alt_m", 0.0),
        "min_alt_m":        track.get("min_alt_m", 0.0),
        "alt_gain_m":       track.get("alt_gain_m", 0.0),
        "distance_warning": track.get("distance_warning"),
        "alt_gain_warning": track.get("alt_gain_warning"),
        "takeoff_alt_m":    0.0,
        "max_alt_above_takeoff_m": 0.0,
    }

    if source_gps:
        out["takeoff_alt_m"] = float(source_gps[0].get("Alt", 0.0))
        out["max_alt_above_takeoff_m"] = out["max_alt_m"] - out["takeoff_alt_m"]

    if filtered_gps:
        h_speeds = [msg.get("Spd", 0) for msg in filtered_gps]
        max_h_speed = max(h_speeds)

        vz_values = [abs(msg.get("VZ", 0)) for msg in filtered_gps]
        max_v_speed = max(vz_values) if vz_values else 0.0

        max_total_speed = 0.0
        for msg in filtered_gps:
            h_speed = msg.get("Spd", 0)
            v_speed = abs(msg.get("VZ", 0))
            total_speed = math.sqrt(h_speed**2 + v_speed**2)
            max_total_speed = max(max_total_speed, total_speed)

        sats = [msg.get("NSats", 0) for msg in filtered_gps]

        out.update({
            "max_h_speed_ms":     max_h_speed,
            "max_h_speed_kmh":    max_h_speed * 3.6,
            "max_v_speed_ms":     max_v_speed,
            "max_v_speed_kmh":    max_v_speed * 3.6,
            "max_total_speed_ms": max_total_speed,
            "max_total_speed_kmh": max_total_speed * 3.6,
            "avg_sats":           float(np.mean(sats)) if sats else 0.0,
        })
    else:
        out.update({
            "max_h_speed_ms": 0.0, "max_h_speed_kmh": 0.0,
            "max_v_speed_ms": 0.0, "max_v_speed_kmh": 0.0,
            "max_total_speed_ms": 0.0, "max_total_speed_kmh": 0.0,
            "avg_sats": 0.0,
        })

    return out


def _compute_imu_metrics(imu_data: List[Dict]) -> Dict:
    if not imu_data:
        return {"max_accel_ms2": 0.0, "max_imu_speed_ms": 0.0}

    max_accel = 0.0
    for msg in imu_data:
        ax = msg.get("AccX", 0)
        ay = msg.get("AccY", 0)
        az = msg.get("AccZ", 0)
        accel_mag = math.sqrt(ax**2 + ay**2 + az**2)
        dynamic_accel = abs(accel_mag - GRAVITY_MS2)
        max_accel = max(max_accel, dynamic_accel)

    max_imu_speed = 0.0
    if len(imu_data) > 1:
        imu_times = np.array([msg["TimeS"] for msg in imu_data])
        acc_x = np.array([msg.get("AccX", 0) for msg in imu_data])
        acc_y = np.array([msg.get("AccY", 0) for msg in imu_data])
        acc_z = np.array([msg.get("AccZ", 0) for msg in imu_data]) + GRAVITY_MS2

        vel_x = integrate_velocity(acc_x, imu_times)
        vel_y = integrate_velocity(acc_y, imu_times)
        vel_z = integrate_velocity(acc_z, imu_times)

        max_imu_speed = float(np.max(np.sqrt(vel_x**2 + vel_y**2 + vel_z**2)))

    return {"max_accel_ms2": max_accel, "max_imu_speed_ms": max_imu_speed}


def _compute_battery_metrics(bat_data: List[Dict]) -> Dict:
    if not bat_data:
        return {"avg_current_a": 0.0, "energy_used_mah": 0.0}

    currents = [msg.get("Curr", 0) for msg in bat_data]
    curr_tots = [msg.get("CurrTot", 0) for msg in bat_data]
    return {
        "avg_current_a":   float(np.mean(currents)) if currents else 0.0,
        "energy_used_mah": curr_tots[-1] if curr_tots else 0.0,
    }


def _compute_ekf_metrics(ekf) -> Dict:
    if not (ekf and ekf.get("speed")):
        return {"ekf_available": False}

    return {
        "ekf_available":        True,
        "ekf_max_speed_ms":     max(ekf["speed"]),
        "ekf_max_speed_kmh":    max(ekf["speed"]) * 3.6,
        "ekf_max_h_speed_ms":   max(ekf["h_speed"]),
        "ekf_max_h_speed_kmh":  max(ekf["h_speed"]) * 3.6,
        "ekf_max_v_speed_ms":   max(ekf["v_speed"]),
        "ekf_max_v_speed_kmh":  max(ekf["v_speed"]) * 3.6,
        "ekf_board_rotation":   ekf.get("board_rotation_applied", False),
    }


def _compute_warnings(imu_data: List[Dict], bat_data: List[Dict]) -> Dict:
    return {
        "battery_warning": (
            "No battery telemetry (BAT) in this log; energy and current are unavailable."
            if not bat_data else None
        ),
        "gyro_extremes_warning": compute_gyro_extremes_warning(imu_data),
        "speed_warning": None,
    }


def compute_metrics(data: Dict[str, List[Dict]]) -> Dict:
    """Compute mission metrics from parsed telemetry and fused outputs."""
    gps_data = data.get("GPS", [])
    imu_data = data.get("IMU", [])
    bat_data = data.get("BAT", [])
    filtered_gps = filter_gps_by_quality(gps_data)

    return {
        **_compute_duration(gps_data),
        **_compute_gps_metrics(filtered_gps, gps_data),
        **_compute_imu_metrics(imu_data),
        **_compute_battery_metrics(bat_data),
        **_compute_ekf_metrics(data.get("EKF")),
        **_compute_warnings(imu_data, bat_data),
    }
