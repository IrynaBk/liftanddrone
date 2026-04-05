"""Orientation helpers for body-to-navigation vector transforms."""

from __future__ import annotations

import math
import numpy as np


def euler_to_rotation_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """Build body-to-NED rotation matrix from ZYX Euler angles in radians."""
    sr, cr = math.sin(roll), math.cos(roll)
    sp, cp = math.sin(pitch), math.cos(pitch)
    sy, cy = math.sin(yaw), math.cos(yaw)

    # Standard body-to-nav (NED) rotation matrix R_b^n
    return np.array(
        [
            [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp,     cp * sr,                cp * cr               ],
        ],
        dtype=float,
    )


def rotate_vector(vector: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Rotate a 3D vector by a rotation matrix."""
    return matrix @ vector
