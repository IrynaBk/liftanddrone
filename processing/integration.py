"""Integration and vector analytics helpers."""

from __future__ import annotations

import math


def trapz_step(val_prev: float, val_curr: float, dt: float) -> float:
    """One trapezoidal integration step over dt."""
    if dt <= 0:
        return 0.0
    return 0.5 * (val_prev + val_curr) * dt


def calculate_magnitude(vx: float, vy: float, vz: float) -> float:
    """3D vector magnitude."""
    return math.sqrt(vx * vx + vy * vy + vz * vz)
