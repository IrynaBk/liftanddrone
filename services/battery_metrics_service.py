"""Average current and cumulative energy from BAT messages."""

from typing import Dict, List, Tuple

import numpy as np


def compute_battery_metrics(bat_data: List[Dict]) -> Tuple[float, float]:
    """
    Returns:
        (avg_current_a, energy_used_mAh from last CurrTot)
    """
    if not bat_data:
        return 0.0, 0.0
    currents = [msg.get('Curr', 0) for msg in bat_data]
    avg_current_a = float(np.mean(currents)) if currents else 0.0
    curr_tots = [msg.get('CurrTot', 0) for msg in bat_data]
    energy_used_mah = float(curr_tots[-1]) if curr_tots else 0.0
    return avg_current_a, energy_used_mah
