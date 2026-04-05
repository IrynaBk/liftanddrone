"""Peak acceleration magnitude from IMU samples."""

import math
from typing import Dict, List


def compute_max_acceleration_ms2(imu_data: List[Dict]) -> float:
    """Maximum L2 norm of (AccX, AccY, AccZ) in m/s²."""
    if not imu_data:
        return 0.0
    max_accel = 0.0
    for msg in imu_data:
        ax = msg.get('AccX', 0)
        ay = msg.get('AccY', 0)
        az = msg.get('AccZ', 0)
        accel_mag = math.sqrt(ax ** 2 + ay ** 2 + az ** 2)
        max_accel = max(max_accel, accel_mag)
    return float(max_accel)
