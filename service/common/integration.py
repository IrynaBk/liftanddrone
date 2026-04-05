"""Numerical integration helpers for IMU velocity estimation."""

from __future__ import annotations

import numpy as np


def trapz_step(val_prev: float, val_curr: float, dt: float) -> float:
    """One trapezoidal integration step over dt."""
    if dt <= 0:
        return 0.0
    return 0.5 * (val_prev + val_curr) * dt


def integrate_velocity(accel_array: np.ndarray, time_array: np.ndarray) -> np.ndarray:
    """Integrate acceleration over time with trapezoidal rule."""
    if len(accel_array) < 2:
        return np.asarray(accel_array, dtype=float)

    velocity = np.zeros_like(accel_array, dtype=float)
    for i in range(1, len(accel_array)):
        dt = float(time_array[i] - time_array[i - 1])
        if dt > 0:
            velocity[i] = velocity[i - 1] + trapz_step(float(accel_array[i - 1]), float(accel_array[i]), dt)
    return velocity
