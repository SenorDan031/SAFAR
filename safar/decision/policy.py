"""Configurable, continuous prototype policy for hazardous-object decisions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HazardPolicy:
    """Thresholds centralised so tests and later tuning do not scatter numbers."""

    minimum_confidence: float = 0.35
    persistence_frames: int = 2
    deescalation_frames: int = 3
    path_half_width_m: float = 2.2
    image_path_left_ratio: float = 0.30
    image_path_right_ratio: float = 0.70
    emergency_ttc_s: float = 1.5
    critical_first_seen_distance_m: float = 7.0
    critical_first_seen_closing_kmh: float = 18.0

    def awareness_distance_m(self, speed_kmh: float) -> float:
        """Increase awareness smoothly from ~22 m at city speed to highway range."""
        return 22.0 + max(0.0, speed_kmh - 20.0) * 0.85

    def slowdown_distance_m(self, speed_kmh: float) -> float:
        """Increase the gradual-slowdown threshold smoothly with vehicle speed."""
        return 12.0 + max(0.0, speed_kmh - 20.0) * 0.60
