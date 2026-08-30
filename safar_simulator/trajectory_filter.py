"""
SAFAR Simulator — Ego-Path Trajectory Relevance Filter
Determines whether a detected road entity is OUTSIDE PATH, NEAR PATH, INTERSECTING, or DIRECTLY AHEAD.
Filters out non-threatening opposite lane and sidewalk traffic to eliminate false emergency braking.
"""
from dataclasses import dataclass
from typing import Tuple, Optional
import math

@dataclass
class TrajectoryRelevance:
    state: str                 # "OUTSIDE_PATH", "NEAR_PATH", "INTERSECTING_PATH", "DIRECTLY_AHEAD"
    threat_score: float        # 0.0 to 1.0
    threat_level: str          # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    decision_action: str       # "CONTINUE", "MONITOR", "WARN", "BRAKE", "EMERGENCY_BRAKE"
    ttc_seconds: float
    reason: str
    is_immediate_hazard: bool


class TrajectoryFilterEngine:
    """Evaluates spatial geometry and trajectory relevance for any entity relative to ego vehicle."""

    @staticmethod
    def evaluate(
        distance_m: float,
        lateral_offset_m: float,
        relative_speed_kmh: float,
        entity_class: str = "car",
        lane_width_m: float = 3.5
    ) -> TrajectoryRelevance:
        half_lane = lane_width_m * 0.5 # ~1.75m

        # Calculate Time-To-Collision (TTC)
        closing_speed_mps = relative_speed_kmh / 3.6
        if closing_speed_mps > 0.5 and distance_m > 0:
            ttc_s = distance_m / closing_speed_mps
        else:
            ttc_s = 999.0

        abs_lat = abs(lateral_offset_m)

        # 1. OUTSIDE PATH (Opposite lane traffic or far sidewalk)
        if abs_lat > (half_lane + 0.8):
            return TrajectoryRelevance(
                state="OUTSIDE_PATH",
                threat_score=0.00,
                threat_level="LOW",
                decision_action="CONTINUE",
                ttc_seconds=ttc_s,
                reason=f"{entity_class.upper()} outside ego driving corridor ({lateral_offset_m:+.1f}m lateral offset). Ignored.",
                is_immediate_hazard=False
            )

        # 2. NEAR PATH (Adjacent lane or curb edge)
        elif abs_lat > (half_lane - 0.4):
            return TrajectoryRelevance(
                state="NEAR_PATH",
                threat_score=0.18,
                threat_level="LOW",
                decision_action="MONITOR",
                ttc_seconds=ttc_s,
                reason=f"{entity_class.upper()} in adjacent corridor ({lateral_offset_m:+.1f}m lateral). Monitored.",
                is_immediate_hazard=False
            )

        # 3. DIRECTLY AHEAD or INTERSECTING PATH (Inside ego lane corridor)
        else:
            # Inside ego driving corridor
            if distance_m <= 15.0 or (ttc_s <= 2.2 and ttc_s > 0.0):
                # Imminent collision risk
                score = min(1.0, 0.85 + (15.0 - max(0.0, distance_m)) * 0.01)
                return TrajectoryRelevance(
                    state="DIRECTLY_AHEAD",
                    threat_score=score,
                    threat_level="CRITICAL",
                    decision_action="EMERGENCY_BRAKE",
                    ttc_seconds=ttc_s,
                    reason=f"Imminent {entity_class.upper()} directly in path (Dist: {distance_m:.1f}m, TTC: {ttc_s:.1f}s). AEB engaged.",
                    is_immediate_hazard=True
                )
            elif distance_m <= 30.0 or (ttc_s <= 4.0 and ttc_s > 0.0):
                # High hazard / closing in
                score = 0.65 + (30.0 - distance_m) * 0.006
                return TrajectoryRelevance(
                    state="INTERSECTING_PATH",
                    threat_score=score,
                    threat_level="HIGH",
                    decision_action="WARN",
                    ttc_seconds=ttc_s,
                    reason=f"{entity_class.upper()} in forward trajectory (Dist: {distance_m:.1f}m, TTC: {ttc_s:.1f}s). Active slowdown.",
                    is_immediate_hazard=True
                )
            else:
                # Moderate distance obstacle
                return TrajectoryRelevance(
                    state="INTERSECTING_PATH",
                    threat_score=0.35,
                    threat_level="MEDIUM",
                    decision_action="MONITOR",
                    ttc_seconds=ttc_s,
                    reason=f"{entity_class.upper()} ahead in lane at {distance_m:.1f}m. Maintaining safe gap.",
                    is_immediate_hazard=False
                )
