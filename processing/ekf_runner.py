"""EKF execution pipeline over parsed ArduPilot telemetry messages."""

from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from processing.ekf_core import (
    calculate_kalman_gain,
    f_state_transition,
    get_jacobian_F,
    predict_covariance,
    update_covariance,
    update_state,
)
from processing.geodesy import normalize_gps_measurement
from processing.integration import calculate_magnitude


GRAVITY_MS2 = 9.80665
INIT_IMU_SAMPLES = 50
INIT_LEVEL_G_TOL = 1.5
INIT_LEVEL_TIMEOUT_S = 2.0
ADAPTIVE_MIN_SAMPLES = 10
ADAPTIVE_WINDOW = 5
ADAPTIVE_DELTA_MS2 = 0.5
ADAPTIVE_IN_FLIGHT_MAG_MS2 = 10.3


def _safe_time(msg: dict) -> float:
    return float(msg.get("TimeS", 0.0))


def _gps_has_3d_fix(msg: dict) -> bool:
    """Return True when GPS record is considered a valid 3D fix."""
    lat = float(msg.get("Lat", 0.0))
    lon = float(msg.get("Lng", 0.0))
    if not np.isfinite(lat) or not np.isfinite(lon):
        return False

    status_raw = msg.get("Status", None)
    if status_raw is not None:
        try:
            return int(status_raw) >= 3
        except (TypeError, ValueError):
            pass

    # Fallback for logs without Status field.
    return not (lat == 0.0 and lon == 0.0)


def _first_valid_gps(gps_records: List[dict]) -> Optional[dict]:
    for g in gps_records:
        if _gps_has_3d_fix(g):
            return g
    return None


def _should_finalize_leveling(samples: List[np.ndarray], elapsed_s: float) -> tuple[bool, bool]:
    """Return (ready, flight_detected) for accelerometer leveling phase.

    Adaptive logic:
    - finalize early when acceleration trend suggests the vehicle already started moving,
    - otherwise keep legacy exits (enough samples or timeout).
    """
    count = len(samples)
    if count >= ADAPTIVE_MIN_SAMPLES:
        mags = [float(np.linalg.norm(v)) for v in samples]
        win = min(ADAPTIVE_WINDOW, count // 2)
        if win >= 2:
            baseline = float(np.mean(mags[:win]))
            recent = float(np.mean(mags[-win:]))
            delta = abs(recent - baseline)

            # Early stop when startup motion is detected.
            if recent >= ADAPTIVE_IN_FLIGHT_MAG_MS2 or delta >= ADAPTIVE_DELTA_MS2:
                return True, True

    if count >= INIT_IMU_SAMPLES or elapsed_s >= INIT_LEVEL_TIMEOUT_S:
        return True, False

    return False, False


def _leveling_mean_acc(samples: List[np.ndarray], flight_detected: bool) -> np.ndarray:
    """Compute mean acceleration for leveling, favoring pre-motion samples."""
    if not samples:
        return np.zeros(3, dtype=float)

    use_samples = samples
    if flight_detected and len(samples) > ADAPTIVE_WINDOW + 2:
        use_samples = samples[:-ADAPTIVE_WINDOW]

    return np.mean(np.vstack(use_samples), axis=0)


def run_ekf_on_log(data: Dict[str, List[dict]]) -> Optional[Dict[str, List[float]]]:
    """Run EKF fusion over ArduPilot telemetry and return NED trajectory using an Event-Driven Single Queue.

    Corrections Applied:
    1. Accelerometer Leveling: Init Roll/Pitch from initial IMU vector, not zeros.
    2. 6D Update: GPS Update step now uses [pN, pE, pD, vN, vE, vD] to correct accelerometer drift.
    3. Seed VZ: VZ from GPS is captured during startup to avoid 'In-Air Start' drops.
    """
    # 1. Build a single chronological event queue
    events = []
    for m in data.get("IMU", []):
        m_copy = m.copy()
        m_copy['event_type'] = 'IMU'
        events.append(m_copy)

    for g in data.get("GPS", []):
        g_copy = g.copy()
        g_copy['event_type'] = 'GPS'
        events.append(g_copy)

    for a in data.get("ATT", []):
        a_copy = a.copy()
        a_copy['event_type'] = 'ATT'
        events.append(a_copy)

    if not events:
        return None

    # Sort strictly by timestamp
    events.sort(key=_safe_time)

    # EKF State matrices
    x = np.zeros(9, dtype=float)
    # Initial P: large for pos/vel, small for angles (since we do init leveling)
    p = np.diag([10.0, 10.0, 10.0, 2.0, 2.0, 2.0, 0.1, 0.1, 0.1])
    q = np.diag([0.02, 0.02, 0.02, 0.6, 0.6, 0.6, 0.01, 0.01, 0.01])
    
    # 6D Measurement Noise (Position and Velocity)
    r = np.diag([4.0, 4.0, 6.0, 1.0, 1.0, 1.5])

    # 6x9 Observation Matrix (Map State [pn..yaw] to Measurement [pn, pe, pd, vn, ve, vd])
    h = np.zeros((6, 9), dtype=float)
    h[0, 0] = 1.0
    h[1, 1] = 1.0
    h[2, 2] = 1.0
    h[3, 3] = 1.0
    h[4, 4] = 1.0
    h[5, 5] = 1.0

    # 3x9 Observation Matrix for ATT Update
    h_att = np.zeros((3, 9), dtype=float)
    h_att[0, 6] = 1.0
    h_att[1, 7] = 1.0
    h_att[2, 8] = 1.0
    r_att = np.diag([0.01, 0.01, 0.05])  # Trust ATT roll/pitch heavily, yaw slightly less

    # Pipeline State
    gps_ref = _first_valid_gps(data.get("GPS", []))
    if not gps_ref:
        return None

    ref_lat = float(gps_ref.get("Lat", 0.0))
    ref_lon = float(gps_ref.get("Lng", 0.0))
    ref_alt = float(gps_ref.get("Alt", 0.0))

    spd = float(gps_ref.get("Spd", 0.0))
    gcrs = float(gps_ref.get("GCrs", 0.0))
    v_n_init = spd * math.cos(math.radians(gcrs))
    v_e_init = spd * math.sin(math.radians(gcrs))
    v_d_init = float(gps_ref.get("VZ", 0.0))
    first_gps_time = _safe_time(gps_ref)

    is_fully_initialized = False
    prev_t = None
    init_start_t = None
    init_acc_samples: List[np.ndarray] = []

    east, north, up = [], [], []
    speed, h_speed, v_speed, time_s = [], [], [], []

    # Identify first valid ATT for Yaw initialization
    yaw_init = 0.0
    for a in data.get("ATT", []):
        if "Yaw" in a:
            yaw_init = math.radians(float(a["Yaw"]))
            break

    # 2. Main Event Loop
    for e in events:
        t = _safe_time(e)

        # Skip all events until we hit the time of the first valid GPS
        if t < first_gps_time:
            continue

        # -- PHASE 1: Wait for first IMU after GPS to perform Accelerometer Leveling --
        if not is_fully_initialized:
            if e['event_type'] == 'IMU':
                ax = float(e.get("AccX", 0.0))
                ay = float(e.get("AccY", 0.0))
                az = float(e.get("AccZ", 0.0))

                if init_start_t is None:
                    init_start_t = t

                init_acc_samples.append(np.array([ax, ay, az], dtype=float))
                elapsed = t - init_start_t

                ready, flight_detected = _should_finalize_leveling(init_acc_samples, elapsed)
                if not ready:
                    continue

                acc_mean = _leveling_mean_acc(init_acc_samples, flight_detected)
                ax_m, ay_m, az_m = float(acc_mean[0]), float(acc_mean[1]), float(acc_mean[2])
                acc_mag = float(np.linalg.norm(acc_mean))

                # If gravity estimate is implausible, keep waiting a bit longer.
                if (
                    not flight_detected
                    and abs(acc_mag - GRAVITY_MS2) > INIT_LEVEL_G_TOL
                    and elapsed < INIT_LEVEL_TIMEOUT_S
                ):
                    continue

                # Accelerometer leveling (Pitch and Roll from averaged gravity vector)
                # ArduPilot convention: AccZ is ~ -9.81 when level.
                roll_init = math.atan2(-ay_m, -az_m)
                pitch_init = math.atan2(ax_m, math.sqrt(ay_m**2 + az_m**2))

                # Seed state vector
                x[3], x[4], x[5] = v_n_init, v_e_init, v_d_init
                x[6], x[7], x[8] = roll_init, pitch_init, yaw_init

                is_fully_initialized = True
                prev_t = t
            continue

        dt = t - prev_t
        if dt <= 0:
            continue

        # -- PHASE 3: Normal Filter Operation --
        if e['event_type'] == 'IMU':
            acc_body = np.array([float(e.get("AccX", 0.0)), float(e.get("AccY", 0.0)), float(e.get("AccZ", 0.0))], dtype=float)
            gyro_body = np.array([float(e.get("GyrX", 0.0)), float(e.get("GyrY", 0.0)), float(e.get("GyrZ", 0.0))], dtype=float)
            
            x = f_state_transition(x, acc_body, gyro_body, dt)
            f = get_jacobian_F(x, acc_body, dt)
            p = predict_covariance(p, f, q * dt)
            prev_t = t
            
            # Record trajectory
            vn, ve, vd = x[3], x[4], x[5]
            time_s.append(t)
            north.append(x[0])
            east.append(x[1])
            up.append(-x[2])  # Convert Down to Up metric
            speed.append(calculate_magnitude(vn, ve, vd))
            h_speed.append(math.sqrt(vn**2 + ve**2))
            v_speed.append(abs(vd))
            
        elif e['event_type'] == 'GPS':
            if not _gps_has_3d_fix(e):
                continue
                
            gn, ge, gd = normalize_gps_measurement(e, ref_lat, ref_lon, ref_alt)
            
            spd = float(e.get("Spd", 0.0))
            gcrs = float(e.get("GCrs", 0.0))
            vn_meas = spd * math.cos(math.radians(gcrs))
            ve_meas = spd * math.sin(math.radians(gcrs))
            vd_meas = float(e.get("VZ", 0.0))
            
            # 6D Measurement Update
            z = np.array([gn, ge, gd, vn_meas, ve_meas, vd_meas], dtype=float)
            
            k = calculate_kalman_gain(p, h, r)
            x = update_state(x, k, z, h)
            p = update_covariance(p, k, h)
            
        elif e['event_type'] == 'ATT':
            # Properly treat ATT as a pseudo-measurement to update angles via EKF (preventing gyro drift)
            # This maintains covariance consistency and properly integrates with the 9D EKF architecture.
            z_att = np.array([
                math.radians(float(e.get("Roll", 0.0))),
                math.radians(float(e.get("Pitch", 0.0))),
                math.radians(float(e.get("Yaw", 0.0)))
            ], dtype=float)
            
            k = calculate_kalman_gain(p, h_att, r_att)
            
            # Subtraction for angles needs to handle +-Pi wrap-around
            innovation = z_att - (h_att @ x)
            innovation = (innovation + np.pi) % (2 * np.pi) - np.pi
            
            x = x + k @ innovation
            p = update_covariance(p, k, h_att)

    if not time_s:
        return None

    return {
        "time_s": time_s,
        "east": east,
        "north": north,
        "up": up,
        "speed": speed,
        "h_speed": h_speed,
        "v_speed": v_speed,
        "board_rotation_applied": False,
        "coord_frame": "NED",
    }
