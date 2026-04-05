"""Extended Kalman Filter core math blocks for telemetry fusion."""

from __future__ import annotations

import math
import numpy as np

from core.fusion.orientation import euler_to_rotation_matrix
from core.constants import GRAVITY_MS2


def f_state_transition(X: np.ndarray, acc_body: np.ndarray, gyro: np.ndarray, dt: float) -> np.ndarray:
    """Predict next nonlinear state from IMU over dt.

    State layout:
    - 6D: [pn, pe, pd, vn, ve, vd]
    - 9D: [pn, pe, pd, vn, ve, vd, roll, pitch, yaw]
    """
    x = X.astype(float).copy()
    if dt <= 0:
        return x

    if x.shape[0] >= 9:
        roll, pitch, yaw = x[6], x[7], x[8]

        p, q, r = float(gyro[0]), float(gyro[1]), float(gyro[2])
        sr, cr = math.sin(roll), math.cos(roll)
        tp = math.tan(pitch)
        cp = math.cos(pitch)

        if abs(cp) > 1e-6:
            roll += (p + q * sr * tp + r * cr * tp) * dt
            pitch += (q * cr - r * sr) * dt
            yaw += (q * sr / cp + r * cr / cp) * dt
        else:
            roll += p * dt
            pitch += q * dt
            yaw += r * dt

        x[6], x[7], x[8] = roll, pitch, yaw
    else:
        roll = pitch = yaw = 0.0

    r_bn = euler_to_rotation_matrix(roll, pitch, yaw)
    acc_nav = r_bn @ np.asarray(acc_body, dtype=float)

    acc_nav_dyn = acc_nav.copy()
    acc_nav_dyn[2] += GRAVITY_MS2

    x[0] += x[3] * dt + 0.5 * acc_nav_dyn[0] * dt * dt
    x[1] += x[4] * dt + 0.5 * acc_nav_dyn[1] * dt * dt
    x[2] += x[5] * dt + 0.5 * acc_nav_dyn[2] * dt * dt

    x[3] += acc_nav_dyn[0] * dt
    x[4] += acc_nav_dyn[1] * dt
    x[5] += acc_nav_dyn[2] * dt

    return x


def get_jacobian_F(X: np.ndarray, acc_body: np.ndarray, dt: float) -> np.ndarray:
    """Linearized state transition Jacobian around current state."""
    n = X.shape[0]
    f = np.eye(n, dtype=float)
    if dt <= 0:
        return f

    f[0, 3] = dt
    f[1, 4] = dt
    f[2, 5] = dt

    if n >= 9:
        roll, pitch, yaw = X[6], X[7], X[8]
        sr, cr = math.sin(roll), math.cos(roll)
        sp, cp = math.sin(pitch), math.cos(pitch)
        sy, cy = math.sin(yaw), math.cos(yaw)
        ax, ay, az = float(acc_body[0]), float(acc_body[1]), float(acc_body[2])

        f[3, 6] = dt * (ay * (cy*sp*cr + sy*sr) + az * (-cy*sp*sr + sy*cr))
        f[4, 6] = dt * (ay * (sy*sp*cr - cy*sr) + az * (-sy*sp*sr - cy*cr))
        f[5, 6] = dt * (ay * (cp*cr)            + az * (-cp*sr))

        f[3, 7] = dt * (ax * (-cy*sp) + ay * (cy*cp*sr) + az * (cy*cp*cr))
        f[4, 7] = dt * (ax * (-sy*sp) + ay * (sy*cp*sr) + az * (sy*cp*cr))
        f[5, 7] = dt * (ax * (-cp)    + ay * (-sp*sr)   + az * (-sp*cr))

        f[3, 8] = dt * (ax * (-sy*cp) + ay * (-sy*sp*sr - cy*cr) + az * (-sy*sp*cr + cy*sr))
        f[4, 8] = dt * (ax * (cy*cp)  + ay * (cy*sp*sr - sy*cr)  + az * (cy*sp*cr + sy*sr))
        f[5, 8] = 0.0

    return f


def predict_covariance(P: np.ndarray, F: np.ndarray, Q: np.ndarray) -> np.ndarray:
    """Predict covariance with process noise."""
    return F @ P @ F.T + Q


def calculate_kalman_gain(P: np.ndarray, H: np.ndarray, R: np.ndarray) -> np.ndarray:
    """Compute Kalman gain matrix."""
    s = H @ P @ H.T + R
    s_inv = np.linalg.pinv(s)
    return P @ H.T @ s_inv


def update_state(X: np.ndarray, K: np.ndarray, z: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Correct predicted state with measurement innovation."""
    innovation = z - H @ X
    return X + K @ innovation


def update_covariance(P: np.ndarray, K: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Correct covariance after measurement update."""
    i = np.eye(P.shape[0], dtype=float)
    p_new = (i - K @ H) @ P
    return 0.5 * (p_new + p_new.T)
