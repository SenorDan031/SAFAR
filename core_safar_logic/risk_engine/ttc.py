"""Safe TTC helper: unknown inputs never become fabricated values."""

import math
from typing import Optional


def calculate_ttc_s(distance_m: Optional[float], closing_speed_kmh: Optional[float]) -> Optional[float]:
    """Calculate Time-To-Collision in seconds from distance (m) and closing speed (km/h).
    
    Returns None if inputs are invalid, non-finite, negative distance, or zero/negative closing speed.
    """
    if distance_m is None or closing_speed_kmh is None:
        return None
    if not all(math.isfinite(v) for v in (distance_m, closing_speed_kmh)):
        return None
    if distance_m < 0.0 or closing_speed_kmh <= 0.0:
        return None
    return distance_m / (closing_speed_kmh / 3.6)
