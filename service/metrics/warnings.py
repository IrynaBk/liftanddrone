"""Warning generation services for mission metrics."""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

from service.common.constants import GYRO_EXTREME_WARN_DEG_S

logger = logging.getLogger(__name__)

_GYR_KEYS: Tuple[Tuple[str, str], ...] = (
    ("GyrX", "X"),
    ("GyrY", "Y"),
    ("GyrZ", "Z"),
)


def compute_gyro_extremes_warning(imu_data: List[Dict]) -> Optional[str]:
    """Warn when gyro rates exceed typical non-aerobatic flight range."""
    if not imu_data:
        return None

    lim_rad = math.radians(GYRO_EXTREME_WARN_DEG_S)
    max_abs = 0.0
    max_axis = ""
    has_gyro = False

    for msg in imu_data:
        for key, short in _GYR_KEYS:
            v = msg.get(key)
            if v is None:
                continue
            has_gyro = True
            try:
                g = float(v)
            except (TypeError, ValueError):
                continue
            a = abs(g)
            if a > max_abs:
                max_abs = a
                max_axis = short

    if not has_gyro or max_abs <= lim_rad:
        return None

    peak_deg = math.degrees(max_abs)
    logger.warning(
        "Gyro peak |ω| %.2f rad/s (%.0f°/s) on axis %s exceeds %.0f°/s.",
        max_abs,
        peak_deg,
        max_axis or "?",
        GYRO_EXTREME_WARN_DEG_S,
    )

    return (
        f"Gyroscope Extremes: peak |ω| ≈ {peak_deg:.0f}°/s ({max_abs:.2f} rad/s) on Gyr{max_axis} - "
        f"above ±{GYRO_EXTREME_WARN_DEG_S:.0f}°/s. Stable flight is usually well under 100°/s. "
        "Possible aerobatics, crash/tumble, or prop-wash oscillation."
    )
