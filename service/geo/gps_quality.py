"""GPS quality filtering service."""

from typing import Dict, List

from service.common.constants import MAX_HDOP, MIN_SATS


def filter_gps_by_quality(gps_records: List[Dict]) -> List[Dict]:
    """Keep points with sufficient satellites and acceptable HDOP."""
    return [
        msg
        for msg in gps_records
        if msg.get("HDop", 999) < MAX_HDOP and msg.get("NSats", 0) >= MIN_SATS
    ]
