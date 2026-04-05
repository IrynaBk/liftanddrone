"""Horizontal path length and altitude statistics from GPS."""

import logging
from typing import Any, Dict, List

from services.constants import _ALT_MEDIAN_K, _MAX_PLAUSIBLE_H_SPEED
from services.geo import haversine, median_filter

logger = logging.getLogger(__name__)

# Heuristic bounds for warning logs only (not validation).
_MAX_PLAUSIBLE_ALT_GAIN_WARN_M = 1200.0
# Raw Alt between consecutive GPS samples; larger jumps suggest GPS alt noise, not real motion.
_MAX_PLAUSIBLE_ALT_DELTA_PER_SAMPLE_M = 10.0


def compute_gps_track_metrics(gps_data: List[Dict]) -> Dict[str, Any]:
    """
    Horizontal distance (plausible segments only), smoothed altitude extrema, and gain.

    Keys: distance_m, max_alt_m, min_alt_m, alt_gain_m; optional alt_gain_warning
    (includes implausible gain, max alt, and inter-sample altitude jumps),
    distance_warning (user-facing strings for the UI).
    """
    out: Dict[str, Any] = {
        'distance_m': 0.0,
        'max_alt_m': 0.0,
        'min_alt_m': 0.0,
        'alt_gain_m': 0.0,
        'alt_gain_warning': None,
        'distance_warning': None,
    }
    if not gps_data:
        return out

    gps_records = gps_data
    altitudes = [r.get('Alt', 0) for r in gps_records]
    k_alt = max(3, min(_ALT_MEDIAN_K, len(altitudes)) | 1)
    alt_smooth = median_filter(altitudes, k=k_alt) if len(altitudes) >= 3 else altitudes

    seg_h_dists: List[float] = []
    for i in range(1, len(gps_records)):
        prev, curr = gps_records[i - 1], gps_records[i]
        prev_us = prev.get('TimeUS')
        curr_us = curr.get('TimeUS')
        if prev_us is not None and curr_us is not None:
            dt = (curr_us - prev_us) / 1_000_000.0
        else:
            dt = curr['TimeS'] - prev['TimeS']
        if dt <= 0:
            continue
        lat1 = prev.get('Lat', 0)
        lon1 = prev.get('Lng', 0)
        lat2 = curr.get('Lat', 0)
        lon2 = curr.get('Lng', 0)
        if lat1 != 0 and lon1 != 0 and lat2 != 0 and lon2 != 0:
            h_dist = haversine(lat1, lon1, lat2, lon2)
            if h_dist / dt <= _MAX_PLAUSIBLE_H_SPEED:
                seg_h_dists.append(h_dist)

    out['distance_m'] = float(sum(seg_h_dists))
    out['max_alt_m'] = float(max(alt_smooth)) if alt_smooth else 0.0
    out['min_alt_m'] = float(min(alt_smooth)) if alt_smooth else 0.0
    out['alt_gain_m'] = out['max_alt_m'] - out['min_alt_m']

    max_abs_alt_delta_m = 0.0
    if len(altitudes) > 1:
        for i in range(1, len(altitudes)):
            a0, a1 = altitudes[i - 1], altitudes[i]
            if a0 == 0 or a1 == 0:
                continue
            max_abs_alt_delta_m = max(max_abs_alt_delta_m, abs(a1 - a0))

    n = len(gps_records)
    alt_msgs: List[str] = []

    if n > 1 and not seg_h_dists:
        logger.warning(
            "GPS track: no horizontal segments passed speed plausibility filter "
            "(%d points); distance may be unreliable.",
            n,
        )
        out['distance_warning'] = (
            "No GPS horizontal segments passed the speed plausibility check. "
            "Reported distance may be too low."
        )

    if out['alt_gain_m'] > _MAX_PLAUSIBLE_ALT_GAIN_WARN_M:
        logger.warning(
            "GPS track: altitude gain %.1f m exceeds typical range; check GPS altitude noise.",
            out['alt_gain_m'],
        )
        alt_msgs.append(
            f"Altitude gain ({out['alt_gain_m']:.0f} m) looks unusually high for a typical flight. "
            "Check GPS or barometer noise."
        )
    if out['max_alt_m'] > 9000.0:
        logger.warning(
            "GPS track: max smoothed altitude %.1f m is implausible; GPS alt may be bad.",
            out['max_alt_m'],
        )
        alt_msgs.append(
            f"Max altitude ({out['max_alt_m']:.0f} m) looks implausible; GPS altitude may be unreliable."
        )

    if max_abs_alt_delta_m > _MAX_PLAUSIBLE_ALT_DELTA_PER_SAMPLE_M:
        logger.warning(
            "GPS track: consecutive Alt delta %.1f m exceeds ±%.1f m per sample; likely GPS alt noise.",
            max_abs_alt_delta_m,
            _MAX_PLAUSIBLE_ALT_DELTA_PER_SAMPLE_M,
        )
        alt_msgs.append(
            f"Altitude jumps: largest step between consecutive GPS samples is {max_abs_alt_delta_m:.1f} m "
            f"(limit ±{_MAX_PLAUSIBLE_ALT_DELTA_PER_SAMPLE_M:.0f} m). Likely GPS altitude noise, not real vertical motion."
        )

    if alt_msgs:
        out['alt_gain_warning'] = " ".join(alt_msgs)

    return out
