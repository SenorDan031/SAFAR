"""Safe TTC helper: unknown inputs never become fabricated values."""
import math
def calculate_ttc_s(distance_m, closing_speed_kmh):
    if distance_m is None or closing_speed_kmh is None: return None
    if not all(math.isfinite(v) for v in (distance_m, closing_speed_kmh)) or distance_m < 0 or closing_speed_kmh <= 0: return None
    return distance_m / (closing_speed_kmh / 3.6)
